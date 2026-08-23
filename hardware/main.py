# hardware/main.py
"""
深渊哨兵 ESP32-S3 (行空板K10) 传感器节点主程序
启动后：
  1. 连接WiFi + MQTT
  2. 每5秒读取 RS485 Modbus 传感器
  3. 上报 JSON 到 sentinel/sensor_data
  4. 监听 sentinel/commands 接收排水指令 → 控制继电器 GPIO15
"""
import time
import json
import network
import machine
from machine import Pin
from umqtt.simple import MQTTClient

from config import (
    WIFI_SSID, WIFI_PASS,
    MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, MQTT_KEEPALIVE,
    TOPIC_SENSOR, TOPIC_STATUS, TOPIC_COMMANDS, PUBLISH_INTERVAL,
    RS485_TX_PIN, RS485_RX_PIN, RS485_UART_ID, RS485_BAUDRATE,
    WEATHER_ADDR, SOIL_ADDR,
    WEATHER_REGISTERS, SOIL_REGISTERS, MODBUS_MAX_READ,
    RELAY_PIN,
)
from modbus_reader import ModbusRTU


# ============================================================
# 风力等级名称
# ============================================================
WIND_POWER_NAMES = {
    0: "无风", 1: "1级-软风", 2: "2级-轻风", 3: "3级-微风",
    4: "4级-和风", 5: "5级-清风", 6: "6级-强风", 7: "7级-疾风",
    8: "8级-大风", 9: "9级-烈风", 10: "10级-狂风",
    11: "11级-暴风", 12: "12级-飓风",
    13: "13级", 14: "14级", 15: "15级", 16: "16级", 17: "17级",
}


def wind_power_name(level):
    """风力等级数字 → 中文名"""
    level = int(level) if level is not None else 0
    return WIND_POWER_NAMES.get(level, f"{level}级")


# ============================================================
# 全局状态
# ============================================================
relay = None           # 继电器 Pin 对象
pump_until = 0         # 排水结束时间戳


# ============================================================
# WiFi 连接
# ============================================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"WiFi已连接: {wlan.ifconfig()[0]}")
        return True

    print(f"连接WiFi: {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASS)

    for i in range(40):  # 等最多20秒
        if wlan.isconnected():
            print(f"WiFi已连接, IP: {wlan.ifconfig()[0]}")
            return True
        time.sleep(0.5)

    print("WiFi连接超时")
    return False


# ============================================================
# MQTT 消息回调
# ============================================================
def on_mqtt_message(topic, msg):
    """收到 MQTT 消息的回调"""
    global pump_until

    try:
        data = json.loads(msg.decode())
    except Exception:
        return

    topic_str = topic.decode() if isinstance(topic, bytes) else topic

    if topic_str == "sentinel/commands":
        action = data.get("action", "")
        if action == "pump_on":
            duration = data.get("duration", 60)
            reason = data.get("reason", "")
            pump_until = time.time() + duration
            if relay:
                relay.value(1)
            print(f"[CMD] 排水指令! 持续{duration}秒 | 原因: {reason[:50]}...")


# ============================================================
# MQTT 连接
# ============================================================
def connect_mqtt():
    try:
        client = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_BROKER,
            port=MQTT_PORT,
            keepalive=MQTT_KEEPALIVE,
        )
        client.set_callback(on_mqtt_message)
        client.connect()
        # 订阅排水指令频道
        client.subscribe(TOPIC_COMMANDS)
        print(f"MQTT已连接: {MQTT_BROKER}:{MQTT_PORT}")
        return client
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        return None


# ============================================================
# 读取一组传感器寄存器
# ============================================================
def read_sensor_registers(modbus, slave_addr, register_map):
    """
    读取一个传感器的所有寄存器
    返回: dict {name: scaled_value}，失败返回 None
    """
    reg_list = list(register_map.values())
    start = min(r[0] for r in reg_list)
    end = max(r[0] for r in reg_list)
    count = end - start + 1

    # 先试 0x03（保持寄存器），再试 0x04（输入寄存器）
    raw = modbus.read_holding(slave_addr, start, count)
    if raw is None:
        raw = modbus.read_input(slave_addr, start, count)

    if raw is None:
        return None

    result = {}
    for name, (reg, scale, unit) in register_map.items():
        idx = reg - start
        if idx < len(raw):
            result[name] = round(raw[idx] * scale, 2)
        else:
            result[name] = None

    return result


# ============================================================
# 构建上报 JSON
# ============================================================
def build_payload(weather_data, soil_data, quality):
    """组装为后端期望的 JSON 格式"""
    w = weather_data or {}
    s = soil_data or {}

    wp_raw = w.get("wind_power", 0)
    wp_str = wind_power_name(wp_raw) if wp_raw is not None else "未知"

    return {
        "device_id": MQTT_CLIENT_ID,
        "timestamp": int(time.time()),
        "weather": {
            "wind_speed":    w.get("wind_speed",    0),
            "wind_power":    wp_str,
            "wind_dir":      w.get("wind_dir",      0),
            "air_temp":      w.get("air_temp",      0),
            "air_humidity":  w.get("air_humidity",  0),
            "pressure":      w.get("pressure",      101.3),
            "light":         w.get("light",         0),
            "noise":         w.get("noise",         0),
        },
        "soil": {
            "soil_moisture": s.get("soil_moisture", 0),
            "soil_temp":     s.get("soil_temp",     0),
            "soil_ec":       s.get("soil_ec",       0),
            "soil_ph":       s.get("soil_ph",       7.0),
        },
        "data_quality": quality,
    }


# ============================================================
# 检查并更新继电器状态
# ============================================================
def check_relay():
    """到时间自动关闭继电器"""
    global pump_until
    if pump_until > 0 and time.time() >= pump_until:
        pump_until = 0
        if relay:
            relay.value(0)
        print("[RELAY] 排水结束，继电器断开")


# ============================================================
# 主循环
# ============================================================
def main():
    global relay

    print("=== 深渊哨兵 ESP32-S3 节点启动 ===")

    # 1. 初始化继电器 GPIO15
    relay = Pin(RELAY_PIN, Pin.OUT)
    relay.value(0)
    print(f"继电器初始化: GPIO{RELAY_PIN} (断开)")

    # 2. 连接 WiFi
    if not connect_wifi():
        print("WiFi连接失败，60秒后重启...")
        time.sleep(60)
        machine.reset()

    # 3. 连接 MQTT
    mqtt = connect_mqtt()
    if mqtt is None:
        print("MQTT连接失败，重启...")
        machine.reset()

    # 4. 初始化 Modbus（自动方向 RS485 模块，无需 DE/RE 引脚）
    modbus = ModbusRTU(
        uart_id=RS485_UART_ID,
        tx_pin=RS485_TX_PIN,
        rx_pin=RS485_RX_PIN,
        baudrate=RS485_BAUDRATE,
    )
    print(f"Modbus初始化: UART{RS485_UART_ID}, TX=IO{RS485_TX_PIN}, RX=IO{RS485_RX_PIN}, {RS485_BAUDRATE}bps")

    # 5. 主循环
    heartbeat_count = 0
    mqtt_fail_count = 0
    MAX_MQTT_FAIL = 5  # MQTT连续失败5次才重启

    while True:
        # ---- 检查收到的 MQTT 消息（排水指令等）+ keepalive ----
        try:
            mqtt.check_msg()
        except Exception:
            pass

        # ---- 检查继电器超时 ----
        check_relay()

        # ---- 读取气象传感器 (0x03) ----
        weather_data = read_sensor_registers(modbus, WEATHER_ADDR, WEATHER_REGISTERS)
        weather_ok = (weather_data is not None)

        # ---- 读取土壤传感器 (0x02) ----
        time.sleep_ms(100)
        soil_data = read_sensor_registers(modbus, SOIL_ADDR, SOIL_REGISTERS)
        soil_ok = (soil_data is not None)

        # ---- 数据质量判断 ----
        if weather_ok and soil_ok:
            quality = "GOOD"
        else:
            quality = "SUSPECT"
            if not weather_ok:
                print("[WARN] 气象站(0x03)读取失败")
            if not soil_ok:
                print("[WARN] 土壤传感器(0x02)读取失败")

        # ---- 发送传感器数据 ----
        payload = build_payload(weather_data, soil_data, quality)

        try:
            mqtt.publish(TOPIC_SENSOR, json.dumps(payload))
            mqtt_fail_count = 0  # 成功则清零
            p = payload["weather"]["pressure"]
            sm = payload["soil"]["soil_moisture"]
            rl = "[ON]" if relay.value() else "OFF"
            print(f"[OK] 气压={p}kPa | 土湿={sm}% | 质量={quality} | 继电器={rl}")
        except OSError as e:
            mqtt_fail_count += 1
            print(f"[ERR] MQTT发送失败({mqtt_fail_count}/{MAX_MQTT_FAIL}): {e}")
            if mqtt_fail_count >= MAX_MQTT_FAIL:
                print(f"[CRIT] MQTT连续失败{mqtt_fail_count}次，重启ESP32...")
                time.sleep(1)
                machine.reset()
            # 尝试重连
            try:
                mqtt.disconnect()
            except Exception:
                pass
            time.sleep(2)
            mqtt = connect_mqtt()
            if mqtt is None:
                machine.reset()

        # ---- 心跳上报（每10次 = 50秒一次） ----
        heartbeat_count += 1
        if heartbeat_count % 10 == 0:
            try:
                status = {
                    "device_id": MQTT_CLIENT_ID,
                    "status": "online",
                    "relay_state": relay.value(),
                    "timestamp": int(time.time()),
                }
                mqtt.publish(TOPIC_STATUS, json.dumps(status))
                print(f"[HB] 心跳 #{heartbeat_count // 10} | relay={relay.value()}")
            except Exception:
                pass

        time.sleep(PUBLISH_INTERVAL)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    main()
