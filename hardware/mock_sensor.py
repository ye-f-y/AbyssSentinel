# hardware/mock_sensor.py
# 模拟传感器数据发送，用于调试
# 用法: python mock_sensor.py [--broker localhost] [--port 1883]
import paho.mqtt.client as mqtt
import time
import json
import random
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--broker", default="localhost")
parser.add_argument("--port", default=1883, type=int)
parser.add_argument("--mode", default="random", choices=["random", "normal", "watch", "warning", "critical", "demo"])
args = parser.parse_args()

TOPIC = "sentinel/sensor_data"
STATUS_TOPIC = "sentinel/device_status"

client = mqtt.Client(client_id="MockSensor_01")

def on_connect(client, userdata, flags, rc):
    print(f"模拟器已连接 {args.broker}:{args.port}，状态码={rc}")

client.on_connect = on_connect
client.connect(args.broker, args.port, 60)
client.loop_start()

print(f"开始模拟数据发送 (模式={args.mode})...")

# 各模式的传感器数值 (weather: 8项, soil: 4项)
modes = {
    "normal": {
        "weather": {"wind_speed": 2.0, "wind_power": 1, "wind_dir": 90,
                    "air_temp": 26.0, "air_humidity": 55.0, "pressure": 101.5,
                    "light": 800, "noise": 45.0},
        "soil": {"soil_moisture": 28.0, "soil_temp": 23.0, "soil_ec": 120, "soil_ph": 7.0}
    },
    "watch": {
        "weather": {"wind_speed": 6.5, "wind_power": 3, "wind_dir": 135,
                    "air_temp": 24.5, "air_humidity": 76.0, "pressure": 100.2,
                    "light": 400, "noise": 55.0},
        "soil": {"soil_moisture": 55.0, "soil_temp": 22.5, "soil_ec": 145, "soil_ph": 6.8}
    },
    "warning": {
        "weather": {"wind_speed": 12.0, "wind_power": 6, "wind_dir": 180,
                    "air_temp": 22.0, "air_humidity": 88.0, "pressure": 99.5,
                    "light": 150, "noise": 68.0},
        "soil": {"soil_moisture": 78.0, "soil_temp": 21.5, "soil_ec": 175, "soil_ph": 6.5}
    },
    "critical": {
        "weather": {"wind_speed": 20.0, "wind_power": 8, "wind_dir": 200,
                    "air_temp": 20.0, "air_humidity": 95.0, "pressure": 98.5,
                    "light": 60, "noise": 78.0},
        "soil": {"soil_moisture": 92.0, "soil_temp": 20.5, "soil_ec": 210, "soil_ph": 6.2}
    }
}

def random_data():
    """随机生成数据（带噪声）"""
    base = {
        "weather": {"wind_speed": 3.0, "wind_power": 2, "wind_dir": 120,
                    "air_temp": 25.0, "air_humidity": 60.0, "pressure": 101.0,
                    "light": 500, "noise": 50.0},
        "soil": {"soil_moisture": 35.0, "soil_temp": 22.5, "soil_ec": 130, "soil_ph": 7.0}
    }
    base["weather"]["wind_speed"] += random.uniform(-2, 10)
    base["weather"]["air_humidity"] += random.uniform(-10, 30)
    base["weather"]["pressure"] += random.uniform(-3, 2)
    base["weather"]["air_temp"] += random.uniform(-3, 3)
    base["soil"]["soil_moisture"] += random.uniform(-10, 50)
    base["soil"]["soil_ph"] += random.uniform(-0.5, 0.5)
    return base

# 心跳计数
heartbeat_count = 0

try:
    while True:
        if args.mode == "random":
            data = random_data()
        elif args.mode == "demo":
            # 循环演示：normal->watch->warning->critical（每15秒切换）
            stages = ["normal", "watch", "warning", "critical"]
            idx = (heartbeat_count // 5) % len(stages)  # 每5次心跳 (15秒) 切换
            data = modes[stages[idx]]
        else:
            data = modes[args.mode]

        payload = {
            "device_id": "sentinel_001",
            "timestamp": int(datetime.now().timestamp()),
            "weather": {k: round(v, 1) for k, v in data["weather"].items()},
            "soil": {k: round(v, 1) for k, v in data["soil"].items()},
            "data_quality": "GOOD"
        }

        client.publish(TOPIC, json.dumps(payload, ensure_ascii=False))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 已发送 | "
              f"气压={payload['weather']['pressure']}kPa | "
              f"土湿={payload['soil']['soil_moisture']}%")

        # 每10次发送一次心跳
        heartbeat_count += 1
        if heartbeat_count % 10 == 0:
            status = {
                "device_id": "sentinel_001",
                "status": "online",
                "relay_state": 0,
                "timestamp": int(datetime.now().timestamp())
            }
            client.publish(STATUS_TOPIC, json.dumps(status))

        time.sleep(3)
except KeyboardInterrupt:
    client.loop_stop()
    print("模拟器已停止")
