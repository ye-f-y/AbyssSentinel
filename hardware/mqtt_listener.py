# hardware/mqtt_listener.py
"""监听 sentinel/sensor_data 频道，打印收到的每条数据"""
import json
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        w = data.get("weather", {})
        s = data.get("soil", {})
        print(f"[{data.get('device_id','?')}] "
              f"p={w.get('pressure','?')}kPa "
              f"h={w.get('air_humidity','?')}% "
              f"ws={w.get('wind_speed','?')}m/s "
              f"sm={s.get('soil_moisture','?')}% "
              f"q={data.get('data_quality','?')}")
    except Exception as e:
        print(f"Parse error: {e} | raw: {msg.payload[:100]}")

client = mqtt.Client(client_id="listener",
                     callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("sentinel/sensor_data")
print("Listening on sentinel/sensor_data ... (Ctrl+C to stop)")
client.loop_forever()
