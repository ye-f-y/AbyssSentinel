# backend/main.py
"""
深渊哨兵 AI后端入口
启动: python main.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.mqtt_client import MQTTHandler
from core.agent import SentinelAgent
from core.rule_engine import RuleEngine
from core.database import Database
from rag.retriever import KnowledgeBase

app = FastAPI(title="深渊哨兵AI后端")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mqtt_handler = None
agent = None
rule_engine = RuleEngine()
db = None


@app.on_event("startup")
async def startup():
    global mqtt_handler, agent, db

    print("深渊哨兵后端启动中...")

    # 持久化数据库（SQLite）
    db_path = os.path.join(os.path.dirname(__file__), "data", "sentinel.db")
    try:
        db = Database(db_path)
    except Exception as e:
        print(f"数据库初始化失败（降级为纯内存运行）: {e}")
        db = None

    # 知识库（如果db目录存在就加载）
    kb_path = os.path.join(os.path.dirname(__file__), "rag", "db")
    try:
        kb = KnowledgeBase(db_path=kb_path)
    except Exception as e:
        print(f"知识库加载失败（可稍后处理）: {e}")
        kb = None

    # AI Agent（优先用LLM_API_KEY，兼容旧的DASHSCOPE_API_KEY）
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
    agent = SentinelAgent(api_key=api_key, knowledge_base=kb)

    # MQTT
    broker = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_handler = MQTTHandler(broker=broker, port=port, agent=agent, rule_engine=rule_engine, db=db)
    mqtt_handler.start()

    print("深渊哨兵后端启动完成")


@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "深渊哨兵",
        "mqtt_connected": mqtt_handler is not None
    }


@app.get("/latest")
def latest():
    if mqtt_handler:
        return mqtt_handler.latest_data
    return {"message": "暂无数据"}


# ==================== 历史数据查询 API ====================

@app.get("/api/history/sensors")
def api_history_sensors(hours: int = 24, interval: int = 60, limit: int = 2000):
    """传感器历史（按interval秒分桶降采样）"""
    if not db:
        return {"error": "数据库未启用"}
    hours = max(1, min(hours, 720))          # 最多30天
    interval = max(10, min(interval, 3600))  # 桶宽10秒~1小时
    return {"data": db.query_sensors(hours, interval, limit)}


@app.get("/api/history/events")
def api_history_events(limit: int = 50):
    """风险等级变化事件（预警审计链）"""
    if not db:
        return {"error": "数据库未启用"}
    limit = max(1, min(limit, 500))
    return {"data": db.query_events(limit)}


@app.get("/api/history/analyses")
def api_history_analyses(limit: int = 20):
    """AI推演历史"""
    if not db:
        return {"error": "数据库未启用"}
    limit = max(1, min(limit, 100))
    return {"data": db.query_analyses(limit)}


@app.get("/api/history/commands")
def api_history_commands(limit: int = 20):
    """控制指令历史"""
    if not db:
        return {"error": "数据库未启用"}
    limit = max(1, min(limit, 100))
    return {"data": db.query_commands(limit)}


@app.get("/api/stats/summary")
def api_stats_summary():
    """统计摘要：总量/今日事件/历史最高等级"""
    if not db:
        return {"error": "数据库未启用"}
    return db.stats_summary()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
