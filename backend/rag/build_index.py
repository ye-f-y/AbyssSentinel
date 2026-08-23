# backend/rag/build_index.py
"""
构建国标规范知识库
运行一次即可: python build_index.py
"""
import os
import sys

# 确保能import同目录下的retriever
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import fitz  # pymupdf
from chromadb import PersistentClient
from openai import OpenAI

# 导入预置国标条款（扫描版PDF的补充）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
try:
    from agent import PRESET_REGULATIONS
except ImportError:
    PRESET_REGULATIONS = []


def extract_text_from_pdf(pdf_path: str, chunk_size: int = 500) -> list:
    """从PDF提取文本，按chunk_size切片。检测扫描版PDF（无文本层）"""
    chunks = []
    doc = fitz.open(pdf_path)
    source_name = os.path.basename(pdf_path)
    total_text_len = 0

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if not text.strip():
            continue
        total_text_len += len(text.strip())

        # 按段落切
        paragraphs = text.split("\n\n")
        current = ""
        for p in paragraphs:
            p = p.strip().replace("\n", "")
            if not p:
                continue
            if len(current) + len(p) > chunk_size:
                if current:
                    chunks.append({
                        "text": current,
                        "source": source_name,
                        "page": page_num + 1
                    })
                current = p
            else:
                current += p
        if current:
            chunks.append({
                "text": current,
                "source": source_name,
                "page": page_num + 1
            })

    doc.close()

    # 检测扫描版PDF：总文本过少说明是扫描件，补充预置条款
    if total_text_len < 200:
        print(f"  ⚠️ 检测到扫描版PDF（可提取文本仅{total_text_len}字符），补充预置条款")
        for preset in PRESET_REGULATIONS:
            if preset["source"].startswith("GB51174") and "内涝" in source_name:
                chunks.append({
                    "text": preset["content"],
                    "source": preset["source"],
                    "page": preset["page"]
                })
            elif preset["source"].startswith("GB50330") and "边坡" in source_name:
                chunks.append({
                    "text": preset["content"],
                    "source": preset["source"],
                    "page": preset["page"]
                })

    return chunks


def build_index():
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("错误: 未配置LLM_API_KEY")
        return

    # OpenAI兼容embeddings客户端（.env配置端点与模型）
    emb_client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    )
    emb_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")
    print(f"Embedding模型: {emb_model}")

    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    db_dir = os.path.join(os.path.dirname(__file__), "db")

    pdf_files = [f for f in os.listdir(docs_dir) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"错误: {docs_dir} 中没有PDF文件")
        return

    print(f"找到 {len(pdf_files)} 个PDF文件")

    # 提取所有文本
    all_chunks = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(docs_dir, pdf_file)
        print(f"处理: {pdf_file}")
        chunks = extract_text_from_pdf(pdf_path)
        all_chunks.extend(chunks)
        print(f"  -> 提取 {len(chunks)} 个文本片段")

    print(f"共 {len(all_chunks)} 个文本片段，开始向量化...")

    # 向量化并存入ChromaDB
    client = PersistentClient(path=db_dir)

    # 删除旧collection（如果存在）
    try:
        client.delete_collection("regulations")
    except Exception:
        pass

    collection = client.create_collection(
        name="regulations",
        metadata={"description": "国标规范知识库"}
    )

    batch_size = 20
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]

        try:
            resp = emb_client.embeddings.create(model=emb_model, input=texts)
            embeddings = [e.embedding for e in resp.data]

            collection.add(
                ids=[f"chunk_{j}" for j in range(i, i + len(batch))],
                documents=texts,
                embeddings=embeddings,
                metadatas=[
                    {"source": c["source"], "page": c["page"]}
                    for c in batch
                ]
            )
            print(f"  已处理 {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")
        except Exception as e:
            print(f"  批次处理失败: {e}")

    print(f"知识库构建完成！共 {collection.count()} 条记录")


if __name__ == "__main__":
    build_index()
