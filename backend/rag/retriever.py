# backend/rag/retriever.py
"""
知识库检索：在国标规范中查找相关条款
Embedding走OpenAI兼容接口（.env配置LLM_BASE_URL/LLM_API_KEY/EMBEDDING_MODEL）
"""
import os
from chromadb import PersistentClient
from openai import OpenAI

# 兼容字段名：向量库较旧时字段名可能不同
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class KnowledgeBase:

    def __init__(self, db_path: str, api_key: str = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")

        if not os.path.exists(db_path):
            print(f"知识库目录不存在: {db_path}")
            print("请先运行 rag/build_index.py 构建知识库")
            self.collection = None
            return

        try:
            self.client = PersistentClient(path=db_path)
            self.collection = self.client.get_collection("regulations")
            print(f"知识库加载成功，共 {self.collection.count()} 条")
        except Exception as e:
            print(f"知识库加载失败: {e}")
            self.collection = None

    def search(self, query: str, top_k: int = 3) -> list:
        if not self.collection:
            return []

        # 查询向量化（OpenAI兼容embeddings接口）
        try:
            emb_client = OpenAI(
                api_key=self.api_key,
                base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
            )
            model = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")
            resp = emb_client.embeddings.create(model=model, input=[query])
            query_vector = resp.data[0].embedding
        except Exception as e:
            print(f"Embedding调用失败: {e}")
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )
        except Exception as e:
            print(f"检索失败: {e}")
            return []

        out = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                out.append({
                    "content": doc,
                    "source": meta.get("source", "国标规范"),
                    "page": meta.get("page", 0)
                })

        return out
