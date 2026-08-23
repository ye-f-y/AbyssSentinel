# backend/core/mqtt_client.py
"""
MQTT通信处理：接收传感器数据、发送AI分析结果、下发控制指令
"""
import json
import time
import asyncio
import threading

import paho.mqtt.client as mqtt

from core.rule_engine import RuleEngine

# MQTT频道定义
TOPIC_SENSOR = "sentinel/sensor_data"
TOPIC_COMMANDS = "sentinel/commands"
TOPIC_ANALYSIS = "sentinel/ai_analysis"
TOPIC_STATUS = "sentinel/device_status"


class MQTTHandler:

    def __init__(self, broker: str, port: int, agent, rule_engine: RuleEngine, db=None):
        self.broker = broker
        self.port = port
        self.agent = agent
        self.rule_engine = rule_engine
        self.db = db  # 持久化层（可为None，无库时仅内存运行）

        self.client = mqtt.Client(client_id="sentinel_backend")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.latest_data = {}
        self._analyzing = False
        self._last_level = None  # 上次风险等级（变化时记事件）
        self._loop = asyncio.new_event_loop()

    def start(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as e:
            print(f"MQTT连接失败({self.broker}:{self.port}): {e}")
            print("提示: 请先启动EMQX，或设置环境变量 MQTT_BROKER / MQTT_PORT")
            return

        t = threading.Thread(target=self._run_mqtt, daemon=True)
        t.start()

        t2 = threading.Thread(target=self._run_async, daemon=True)
        t2.start()

    def _run_mqtt(self):
        self.client.loop_forever()

    def _run_async(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"MQTT已连接: {self.broker}")
            client.subscribe(TOPIC_SENSOR)
            client.subscribe(TOPIC_STATUS)
        else:
            print(f"MQTT连接失败，错误码: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except Exception:
            return

        topic = msg.topic
        if topic == TOPIC_SENSOR:
            self._handle_sensor(data)
        elif topic == TOPIC_STATUS:
            self._handle_status(data)

    def _handle_sensor(self, data: dict):
        self.latest_data = data

        result = self.rule_engine.evaluate(data)
        print(f"规则引擎: {result['level']} (得分{result['score']})")

        # 持久化：每条数据入库（含当时判级，SUSPECT数据也有分析价值）
        if self.db:
            try:
                self.db.insert_sensor_reading(data, result)
            except Exception as e:
                print(f"传感器数据入库失败: {e}")

        # 持久化：风险等级变化事件
        if self.db and result["level"] != self._last_level:
            try:
                self.db.insert_risk_event(self._last_level, result["level"], result, data)
                print(f"风险等级变化: {self._last_level} -> {result['level']}")
            except Exception as e:
                print(f"风险事件入库失败: {e}")
        self._last_level = result["level"]

        if data.get("data_quality") == "SUSPECT":
            print("数据质量异常，跳过AI分析")
            return

        if result["need_ai"] and not self._analyzing:
            asyncio.run_coroutine_threadsafe(
                self._do_analysis(data, result),
                self._loop
            )

    def _handle_status(self, data: dict):
        self.latest_data["device_online"] = True
        self.latest_data["relay_state"] = data.get("relay_state", 0)

    async def _do_analysis(self, data: dict, rule_result: dict):
        if self._analyzing:
            return
        self._analyzing = True
        print("开始AI推演...")

        try:
            result = await self.agent.analyze(data, rule_result)

            # 推送AI分析结果
            self._publish(TOPIC_ANALYSIS, {
                "type": "analysis",
                "content": result["analysis"],
                "risk_level": result["risk_level"],
                "regulation_cited": result.get("regulations_cited", []),
                "timestamp": result["timestamp"]
            })

            # 持久化：AI推演记录
            if self.db:
                try:
                    self.db.insert_ai_analysis(result)
                except Exception as e:
                    print(f"AI推演记录入库失败: {e}")

            # AI决定排水 -> 下发控制指令
            action = result.get("action")
            if action and action.get("status") == "EXECUTED":
                cmd = {
                    "action": "pump_on",
                    "duration": action["duration"],
                    "reason": action["reason"],
                    "risk_level": result["risk_level"],
                    "timestamp": int(time.time())
                }
                self._publish(TOPIC_COMMANDS, cmd)
                print(f"已下发排水指令: {cmd}")

                # 持久化：控制指令审计
                if self.db:
                    try:
                        self.db.insert_command(cmd, "EXECUTED")
                    except Exception as e:
                        print(f"控制指令入库失败: {e}")
        except Exception as e:
            print(f"AI推演出错: {e}")
        finally:
            self._analyzing = False

    def _publish(self, topic: str, data: dict):
        payload = json.dumps(data, ensure_ascii=False)
        self.client.publish(topic, payload, qos=1)
