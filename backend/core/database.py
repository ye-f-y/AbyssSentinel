# backend/core/database.py
"""
SQLite 持久化层：传感器时序数据 + 预警闭环审计链

四张表:
  sensor_readings   传感器时序数据（趋势回放/阈值自学习原料）
  risk_events       风险等级变化事件（预警闭环审计核心）
  ai_analyses       AI推演记录（复盘判断依据与国标引用）
  control_commands  控制指令审计（AI何时执行了什么动作）

线程模型: MQTT回调(paho线程)与AI分析(asyncio线程)都会写入，
使用 threading.Lock 串行化写操作（写入频率低，锁竞争可忽略）。
"""
import json
import os
import sqlite3
import threading
import time


class Database:

    def __init__(self, db_path: str):
        # 确保数据目录存在（如 backend/data/）
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self._lock = threading.Lock()
        # check_same_thread=False: 允许多线程共用连接（写操作由锁保护）
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row  # 查询结果按列名取值
        self._conn.execute("PRAGMA journal_mode=WAL")  # 提升读写并发

        self._create_tables()
        print(f"✅ 持久化数据库就绪: {db_path}")

    def _create_tables(self):
        """建表（幂等，已存在则跳过）"""
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                ts INTEGER NOT NULL,
                wind_speed REAL, wind_dir REAL, air_temp REAL, air_humidity REAL,
                pressure REAL, light REAL, noise REAL,
                soil_moisture REAL, soil_temp REAL, soil_ec REAL, soil_ph REAL,
                data_quality TEXT,
                risk_level TEXT, risk_score INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_readings(ts);

            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                prev_level TEXT, new_level TEXT, score INTEGER,
                reasons TEXT,
                snapshot TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_ts ON risk_events(ts);

            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                risk_level TEXT,
                analysis_text TEXT,
                regulations_cited TEXT,
                is_fallback INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS control_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                action TEXT, duration INTEGER, reason TEXT,
                risk_level TEXT, status TEXT
            );
            """)
            self._conn.commit()

    # ==================== 写入 ====================

    @staticmethod
    def _ts(data: dict) -> int:
        """取消息时间戳，缺失则用当前时间"""
        ts = data.get("timestamp")
        return int(ts) if isinstance(ts, (int, float)) else int(time.time())

    def insert_sensor_reading(self, data: dict, rule_result: dict):
        """每条传感器数据入库（冗余存当时规则引擎判级）"""
        w = data.get("weather", {})
        s = data.get("soil", {})
        with self._lock:
            self._conn.execute(
                """INSERT INTO sensor_readings
                   (device_id, ts, wind_speed, wind_dir, air_temp, air_humidity,
                    pressure, light, noise, soil_moisture, soil_temp, soil_ec, soil_ph,
                    data_quality, risk_level, risk_score)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data.get("device_id", "unknown"),
                    self._ts(data),
                    w.get("wind_speed"), w.get("wind_dir"), w.get("air_temp"),
                    w.get("air_humidity"), w.get("pressure"), w.get("light"), w.get("noise"),
                    s.get("soil_moisture"), s.get("soil_temp"), s.get("soil_ec"), s.get("soil_ph"),
                    data.get("data_quality", "GOOD"),
                    rule_result.get("level"), rule_result.get("score"),
                )
            )
            self._conn.commit()

    def insert_risk_event(self, prev_level: str, new_level: str,
                          rule_result: dict, data: dict):
        """风险等级发生变化时记录事件（含触发时刻快照）"""
        w = data.get("weather", {})
        s = data.get("soil", {})
        snapshot = {
            "pressure": w.get("pressure"),
            "air_humidity": w.get("air_humidity"),
            "wind_speed": w.get("wind_speed"),
            "soil_moisture": s.get("soil_moisture"),
        }
        with self._lock:
            self._conn.execute(
                """INSERT INTO risk_events (ts, prev_level, new_level, score, reasons, snapshot)
                   VALUES (?,?,?,?,?,?)""",
                (
                    self._ts(data),
                    prev_level, new_level,
                    rule_result.get("score"),
                    json.dumps(rule_result.get("reasons", []), ensure_ascii=False),
                    json.dumps(snapshot, ensure_ascii=False),
                )
            )
            self._conn.commit()

    def insert_ai_analysis(self, result: dict):
        """AI推演结果入库"""
        with self._lock:
            self._conn.execute(
                """INSERT INTO ai_analyses
                   (ts, risk_level, analysis_text, regulations_cited, is_fallback)
                   VALUES (?,?,?,?,?)""",
                (
                    result.get("timestamp", int(time.time())),
                    result.get("risk_level"),
                    result.get("analysis", ""),
                    json.dumps(result.get("regulations_cited", []), ensure_ascii=False),
                    1 if result.get("fallback") else 0,
                )
            )
            self._conn.commit()

    def insert_command(self, cmd: dict, status: str):
        """下发的控制指令入库（审计）"""
        with self._lock:
            self._conn.execute(
                """INSERT INTO control_commands
                   (ts, action, duration, reason, risk_level, status)
                   VALUES (?,?,?,?,?,?)""",
                (
                    cmd.get("timestamp", int(time.time())),
                    cmd.get("action"),
                    cmd.get("duration"),
                    cmd.get("reason"),
                    cmd.get("risk_level"),
                    status,
                )
            )
            self._conn.commit()

    # ==================== 查询 ====================

    def query_sensors(self, hours: int = 24, interval: int = 60, limit: int = 2000) -> list:
        """传感器历史，按 interval 秒分桶 AVG 降采样"""
        since = int(time.time()) - hours * 3600
        with self._lock:
            rows = self._conn.execute(
                """SELECT (ts / ?) * ? AS bucket,
                          AVG(pressure) AS pressure, AVG(air_humidity) AS air_humidity,
                          AVG(wind_speed) AS wind_speed, AVG(air_temp) AS air_temp,
                          AVG(soil_moisture) AS soil_moisture, AVG(soil_temp) AS soil_temp,
                          AVG(risk_score) AS risk_score,
                          MAX(risk_level) AS risk_level
                   FROM sensor_readings
                   WHERE ts >= ?
                   GROUP BY bucket ORDER BY bucket LIMIT ?""",
                (interval, interval, since, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_events(self, limit: int = 50) -> list:
        """风险事件列表（含快照）"""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, ts, prev_level, new_level, score, reasons, snapshot
                   FROM risk_events ORDER BY ts DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_analyses(self, limit: int = 20) -> list:
        """AI推演历史"""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, ts, risk_level, analysis_text, regulations_cited, is_fallback
                   FROM ai_analyses ORDER BY ts DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_commands(self, limit: int = 20) -> list:
        """控制指令历史"""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, ts, action, duration, reason, risk_level, status
                   FROM control_commands ORDER BY ts DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats_summary(self) -> dict:
        """统计摘要：总量/今日事件数/历史最高等级/最近事件"""
        now = int(time.time())
        today_start = now - (now % 86400)  # 当日零点（UTC）
        with self._lock:
            cur = self._conn.cursor()
            total_readings = cur.execute(
                "SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
            total_analyses = cur.execute(
                "SELECT COUNT(*) FROM ai_analyses").fetchone()[0]
            total_commands = cur.execute(
                "SELECT COUNT(*) FROM control_commands").fetchone()[0]
            today_events = cur.execute(
                "SELECT COUNT(*) FROM risk_events WHERE ts >= ?",
                (today_start,)).fetchone()[0]
            # 等级序: CRITICAL > WARNING > WATCH > NORMAL
            top_level = cur.execute(
                """SELECT new_level FROM risk_events
                   WHERE new_level IN ('WATCH','WARNING','CRITICAL')
                   ORDER BY CASE new_level
                       WHEN 'CRITICAL' THEN 3 WHEN 'WARNING' THEN 2 ELSE 1 END DESC,
                       ts DESC LIMIT 1"""
            ).fetchone()
            last_event = cur.execute(
                """SELECT ts, prev_level, new_level FROM risk_events
                   ORDER BY ts DESC LIMIT 1"""
            ).fetchone()
        return {
            "total_readings": total_readings,
            "total_analyses": total_analyses,
            "total_commands": total_commands,
            "today_events": today_events,
            "top_risk_level": top_level[0] if top_level else None,
            "last_event": dict(last_event) if last_event else None,
        }

    def close(self):
        with self._lock:
            self._conn.close()
