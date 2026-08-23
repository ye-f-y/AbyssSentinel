# hardware/pc_bridge.py
"""
PC 端传感器桥接器 v2 - 先开串口，再连MQTT
用法: python pc_bridge.py COM19
"""
import sys
import time
import json
import serial
import paho.mqtt.client as mqtt


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def modbus_read(ser, slave_addr, start_reg, count):
    frame = bytearray(8)
    frame[0] = slave_addr
    frame[1] = 0x03
    frame[2] = (start_reg >> 8) & 0xFF
    frame[3] = start_reg & 0xFF
    frame[4] = (count >> 8) & 0xFF
    frame[5] = count & 0xFF
    c = crc16(frame[:6])
    frame[6] = c & 0xFF
    frame[7] = (c >> 8) & 0xFF

    ser.reset_input_buffer()
    ser.write(bytes(frame))
    time.sleep(0.15)
    resp = ser.read(256)
    if not resp or len(resp) < 5:
        return None
    if resp[0] != slave_addr or resp[1] & 0x80:
        return None
    byte_count = resp[2]
    if len(resp) < 3 + byte_count + 2:
        return None
    data_bytes = resp[3:3 + byte_count]
    if crc16(resp[:3 + byte_count]) != (resp[3 + byte_count] | (resp[3 + byte_count + 1] << 8)):
        return None
    vals = []
    for i in range(0, byte_count, 2):
        vals.append((data_bytes[i] << 8) | data_bytes[i + 1])
    return vals


WIND_NAMES = {
    0: "无风", 1: "1级-软风", 2: "2级-轻风", 3: "3级-微风",
    4: "4级-和风", 5: "5级-清风", 6: "6级-强风", 7: "7级-疾风",
    8: "8级-大风", 9: "9级-烈风", 10: "10级-狂风",
    11: "11级-暴风", 12: "12级-飓风",
}


def build_payload(weather_vals, soil_vals):
    if weather_vals:
        w = {
            "air_humidity": weather_vals[0] * 0.1,
            "air_temp":     weather_vals[1] * 0.1,
            "noise":        weather_vals[2] * 0.1,
            "wind_speed":   weather_vals[3] * 0.1,
            "wind_dir":     weather_vals[4] * 1.0,
            "pressure":     weather_vals[5] * 0.1,
            "wind_power":   WIND_NAMES.get(int(weather_vals[6]), f"{int(weather_vals[6])}级"),
            "light":        weather_vals[7] * 1.0,
        }
    else:
        w = {}
    if soil_vals:
        s = {
            "soil_moisture": soil_vals[0] * 0.1,
            "soil_temp":     soil_vals[1] * 0.1,
            "soil_ec":       soil_vals[2] * 1.0,
            "soil_ph":       soil_vals[3] * 0.1,
        }
    else:
        s = {}
    quality = "GOOD" if (weather_vals and soil_vals) else "SUSPECT"
    return {
        "device_id": "sentinel_001",
        "timestamp": int(time.time()),
        "weather": w, "soil": s,
        "data_quality": quality,
    }


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM19"
    print(f"Bridge v2 starting on {port}")

    # ====== 第1步: 先抓串口 ======
    print(f"Opening {port}...", flush=True)
    try:
        ser = serial.Serial(port, baudrate=9600, timeout=1)
    except Exception as e:
        print(f"FATAL: Cannot open {port}: {e}")
        print("Please re-plug USB-RS485 and try again.")
        sys.exit(1)
    print(f"Serial {port} opened OK")

    # ====== 第2步: 再连MQTT ======
    print("Connecting MQTT...", flush=True)
    mqtt_client = mqtt.Client(client_id="pc_bridge",
                              callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start()
    print("MQTT connected OK")

    # ====== 第3步: 循环读取 + 发布 ======
    count = 0
    try:
        while True:
            if count == 0:
                print("Reading sensors...", flush=True)

            weather_vals = modbus_read(ser, 0x03, 0x01F8, 8)
            time.sleep(0.15)
            soil_vals = modbus_read(ser, 0x02, 0x0000, 4)

            payload = build_payload(weather_vals, soil_vals)
            mqtt_client.publish("sentinel/sensor_data",
                              json.dumps(payload, ensure_ascii=False))

            count += 1
            p = payload["weather"].get("pressure", "?")
            sm = payload["soil"].get("soil_moisture", "?")
            q = payload["data_quality"]
            print(f"[{count}] pressure={p}kPa moisture={sm}% {q}", flush=True)

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        ser.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Bridge stopped.")


if __name__ == "__main__":
    main()
