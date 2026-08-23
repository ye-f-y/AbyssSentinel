# hardware/esp32_relay.py
"""
ESP32 简化版 - 仅负责 WiFi + 继电器控制 + 心跳
传感器读取由 PC USB-RS485 桥接器负责
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
    TOPIC_STATUS, TOPIC_COMMANDS, RELAY_PIN,
)

# ---- 全局 ----
relay = None
pump_until = 0


def on_mqtt_message(topic, msg):
    global pump_until
    try:
        data = json.loads(msg.decode())
    except:
        return
    if data.get("action") == "pump_on":
        duration = data.get("duration", 60)
        pump_until = time.time() + duration
        if relay:
            relay.value(1)
        print(f"[CMD] 排水 {duration}s")


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        print(f"WiFi: {wlan.ifconfig()[0]}")
        return True
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for _ in range(40):
        if wlan.isconnected():
            print(f"WiFi: {wlan.ifconfig()[0]}")
            return True
        time.sleep(0.5)
    return False


def connect_mqtt():
    try:
        c = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        c.set_callback(on_mqtt_message)
        c.connect()
        c.subscribe(TOPIC_COMMANDS)
        print(f"MQTT: {MQTT_BROKER}")
        return c
    except Exception as e:
        print(f"MQTT fail: {e}")
        return None


def check_relay():
    global pump_until
    if pump_until and time.time() >= pump_until:
        pump_until = 0
        if relay:
            relay.value(0)
        print("[RELAY] OFF")


def main():
    global relay

    relay = Pin(RELAY_PIN, Pin.OUT)
    relay.value(0)

    if not connect_wifi():
        print("WiFi fail, reboot")
        machine.reset()

    mqtt = connect_mqtt()
    if mqtt is None:
        machine.reset()

    hb = 0
    while True:
        try:
            mqtt.check_msg()
        except:
            pass

        check_relay()

        hb += 1
        if hb % 60 == 0:  # 每5分钟心跳
            try:
                mqtt.publish(TOPIC_STATUS, json.dumps({
                    "device_id": MQTT_CLIENT_ID,
                    "status": "online",
                    "relay_state": relay.value(),
                    "timestamp": int(time.time()),
                }))
                print(f"[HB] relay={relay.value()}")
            except Exception as e:
                print(f"[HB] fail: {e}")

        time.sleep(5)


if __name__ == "__main__":
    main()
