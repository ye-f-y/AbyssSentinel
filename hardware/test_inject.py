# hardware/test_inject.py
"""
MQTT 灾害链模拟数据注入器
向 EMQX 批量推送暴雨临界值，测试数字孪生预警系统

用法:
  python test_inject.py                    # 5阶段完整演示
  python test_inject.py --stage critical   # 只测紧急阶段
  python test_inject.py --stage warning    # 只测警告+紧急阶段
  python test_inject.py --interval 3       # 每3秒推一条（默认2秒）

查看数据:
  终端打印  — 每条报文逐行显示
  EMQX Dashboard — http://localhost:18083 → WebSocket客户端
"""

import time
import json
import argparse
import paho.mqtt.client as mqtt


# ============================================================
# 5 阶段灾害链数据集
# ============================================================
STAGES = [
    {
        "name": "阶段1/5 · 正常监测",
        "duration": 6,   # 秒
        "steps": 3,      # 分3步渐变
        "start": {
            "pressure": 101.3, "air_humidity": 55, "wind_speed": 1.5,
            "wind_dir": 90, "air_temp": 26.0, "light": 520, "noise": 45,
            "soil_moisture": 28, "soil_temp": 24.0, "soil_ec": 120, "soil_ph": 7.0,
        },
        "end": {
            "pressure": 101.3, "air_humidity": 55, "wind_speed": 1.5,
            "wind_dir": 90, "air_temp": 26.0, "light": 520, "noise": 45,
            "soil_moisture": 28, "soil_temp": 24.0, "soil_ec": 120, "soil_ph": 7.0,
        },
        "risk": "NORMAL",
        "ai_text": "系统自检完成，所有传感器在线，当前气象条件正常。",
    },
    {
        "name": "阶段2/5 · 关注预警",
        "duration": 8,
        "steps": 4,
        "start": {
            "pressure": 100.5, "air_humidity": 65, "wind_speed": 6.0,
            "wind_dir": 135, "air_temp": 24.5, "light": 380, "noise": 55,
            "soil_moisture": 52, "soil_temp": 23.0, "soil_ec": 140, "soil_ph": 6.9,
        },
        "end": {
            "pressure": 99.8, "air_humidity": 76, "wind_speed": 9.0,
            "wind_dir": 160, "air_temp": 23.0, "light": 250, "noise": 62,
            "soil_moisture": 68, "soil_temp": 22.5, "soil_ec": 155, "soil_ph": 6.8,
        },
        "risk": "WATCH",
        "ai_text": "气压持续下降至99.8kPa，湿度上升至76%，风速增强至9m/s，表明强对流天气正在逼近。建议加密监测频率。",
    },
    {
        "name": "阶段3/5 · 警告响应",
        "duration": 10,
        "steps": 5,
        "start": {
            "pressure": 99.5, "air_humidity": 78, "wind_speed": 12.0,
            "wind_dir": 180, "air_temp": 22.0, "light": 150, "noise": 68,
            "soil_moisture": 78, "soil_temp": 21.5, "soil_ec": 175, "soil_ph": 6.5,
        },
        "end": {
            "pressure": 99.0, "air_humidity": 88, "wind_speed": 15.0,
            "wind_dir": 200, "air_temp": 21.0, "light": 80, "noise": 72,
            "soil_moisture": 82, "soil_temp": 21.0, "soil_ec": 190, "soil_ph": 6.3,
        },
        "risk": "WARNING",
        "ai_text": "气压降至99.0kPa，接近强对流阈值；土壤湿度82%已超过边坡关注线75%。依据GB51174-2017第5.2.1条，建议启动预排水程序。",
    },
    {
        "name": "阶段4/5 · 紧急预警",
        "duration": 8,
        "steps": 4,
        "start": {
            "pressure": 98.5, "air_humidity": 90, "wind_speed": 18.0,
            "wind_dir": 210, "air_temp": 20.0, "light": 60, "noise": 78,
            "soil_moisture": 85, "soil_temp": 20.5, "soil_ec": 210, "soil_ph": 6.2,
        },
        "end": {
            "pressure": 98.0, "air_humidity": 95, "wind_speed": 20.0,
            "wind_dir": 225, "air_temp": 19.5, "light": 40, "noise": 82,
            "soil_moisture": 92, "soil_temp": 20.0, "soil_ec": 230, "soil_ph": 6.0,
        },
        "risk": "CRITICAL",
        "ai_text": (
            "气压骤降至98.0kPa(980hPa)，远低于标准大气压101.3kPa，"
            "符合气象学强降雨前兆特征；土壤湿度92%已接近饱和含水率，"
            "依据GB51174-2017第5.2.1条及GB50330-2013第5.3条，"
            "判定内涝风险等级为CRITICAL（紧急），复合灾害风险极高，立即启动排水！"
        ),
    },
    {
        "name": "阶段5/5 · 排水响应与恢复",
        "duration": 14,
        "steps": 7,
        "start": {
            "pressure": 98.5, "air_humidity": 90, "wind_speed": 16.0,
            "wind_dir": 200, "air_temp": 20.5, "light": 80, "noise": 70,
            "soil_moisture": 85, "soil_temp": 21.0, "soil_ec": 200, "soil_ph": 6.3,
        },
        "end": {
            "pressure": 100.8, "air_humidity": 55, "wind_speed": 2.0,
            "wind_dir": 120, "air_temp": 25.5, "light": 500, "noise": 48,
            "soil_moisture": 45, "soil_temp": 23.5, "soil_ec": 130, "soil_ph": 7.0,
        },
        "risk": "WARNING",
        "ai_text": "预排水系统已启动，积水开始消退。气压逐步回升，土壤湿度下降，灾害链已被提前化解。",
    },
]


# ============================================================
# 辅助函数
# ============================================================
WIND_NAMES = {
    0:"无风",1:"1级-软风",2:"2级-轻风",3:"3级-微风",4:"4级-和风",
    5:"5级-清风",6:"6级-强风",7:"7级-疾风",8:"8级-大风",9:"9级-烈风",
    10:"10级-狂风",11:"11级-暴风",12:"12级-飓风",
}
def wind_name(ws):
    level = min(12, int(ws / 3.0))
    return WIND_NAMES.get(level, f"{level}级")


def lerp(a, b, t):
    return a + (b - a) * t


def build_msg(data: dict) -> dict:
    """构建与ESP32/bridge相同格式的JSON"""
    return {
        "device_id": "sentinel_001",
        "timestamp": int(time.time()),
        "weather": {
            "wind_speed":    round(data["wind_speed"], 1),
            "wind_power":    wind_name(data["wind_speed"]),
            "wind_dir":      round(data["wind_dir"]),
            "air_temp":      round(data["air_temp"], 1),
            "air_humidity":  round(data["air_humidity"], 1),
            "pressure":      round(data["pressure"], 1),
            "light":         round(data["light"]),
            "noise":         round(data["noise"], 1),
        },
        "soil": {
            "soil_moisture": round(data["soil_moisture"], 1),
            "soil_temp":     round(data["soil_temp"], 1),
            "soil_ec":       round(data["soil_ec"]),
            "soil_ph":       round(data["soil_ph"], 1),
        },
        "data_quality": "GOOD",
    }


def color_for_risk(risk):
    return {"NORMAL":"\033[32m","WATCH":"\033[33m",
            "WARNING":"\033[91m","CRITICAL":"\033[41m\033[97m"}.get(risk,"\033[0m")


def print_msg(msg: dict, risk: str):
    """彩色打印消息摘要"""
    c = color_for_risk(risk)
    rst = "\033[0m"
    w = msg["weather"]
    s = msg["soil"]
    print(f"{c}  {risk:>8s}{rst} | "
          f"气压:{w['pressure']:>5.1f}kPa | "
          f"湿度:{w['air_humidity']:>4.1f}% | "
          f"风速:{w['wind_speed']:>4.1f}m/s | "
          f"土湿:{s['soil_moisture']:>4.1f}% | "
          f"{w['wind_power']}")


# ============================================================
# 主程序
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="MQTT灾害链模拟数据注入器")
    parser.add_argument("--broker", default="localhost", help="MQTT broker地址")
    parser.add_argument("--port", type=int, default=1883, help="MQTT端口")
    parser.add_argument("--topic", default="sentinel/sensor_data", help="MQTT topic")
    parser.add_argument("--interval", type=float, default=2.0, help="每条消息间隔(秒)")
    parser.add_argument("--stage", choices=["normal","watch","warning","critical","all"],
                        default="all", help="从哪个阶段开始")
    parser.add_argument("--loop", action="store_true", help="循环播放")
    args = parser.parse_args()

    stage_map = {"normal":0, "watch":1, "warning":2, "critical":3, "all":0}
    start_idx = stage_map[args.stage]

    print("=" * 70)
    print("  深渊哨兵 · MQTT 灾害链模拟数据注入器")
    print(f"  Broker: {args.broker}:{args.port} | Topic: {args.topic}")
    print(f"  间隔: {args.interval}s | 阶段: {args.stage} | 循环: {args.loop}")
    print("=" * 70)
    print()
    print("  查看数据:")
    print(f"    1. 本终端 — 实时打印每条报文")
    print(f"    2. EMQX Dashboard — http://localhost:18083 → WebSocket客户端")
    print(f"       - 连接: ws://localhost:8083/mqtt")
    print(f"       - 订阅: {args.topic}")
    print(f"    3. 浏览器大屏 — http://localhost:5173")
    print()

    # 连接 MQTT（兼容 paho-mqtt 1.x 与 2.x）
    print("连接 MQTT...", end=" ", flush=True)
    try:
        client = mqtt.Client(client_id="test_injector",
                             callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client(client_id="test_injector")
    client.connect(args.broker, args.port, 60)
    client.loop_start()  # 关键！启动后台发送线程
    print("OK")
    print()

    stages_to_run = STAGES[start_idx:]

    while True:
        for stage in stages_to_run:
            s = stage
            step_duration = args.interval
            total_steps = s["steps"]
            total_duration = s["duration"]

            print(f"{'─'*60}")
            print(f"  {s['name']} | 目标风险: {s['risk']}")
            print(f"  AI推演: {s['ai_text'][:80]}...")
            print(f"{'─'*60}")

            for step in range(total_steps):
                t = step / max(total_steps - 1, 1)  # 0 → 1
                data = {}
                for key in s["start"]:
                    data[key] = lerp(s["start"][key], s["end"][key], t)

                msg = build_msg(data)
                payload = json.dumps(msg, ensure_ascii=False)
                client.publish(args.topic, payload)
                print_msg(msg, s["risk"])

                time.sleep(step_duration)

            print()

        if not args.loop:
            break
        print("=" * 60)
        print("  一轮完成，重新开始...")
        print("=" * 60)

    print("演示完成！")
    client.disconnect()


if __name__ == "__main__":
    main()
