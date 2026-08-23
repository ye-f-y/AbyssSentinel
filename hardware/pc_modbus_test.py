# hardware/pc_modbus_test.py
"""PC USB-RS485 Modbus sensor test - no emoji version"""
import sys
import time
import serial


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


def modbus_read(ser, slave_addr, start_reg, count=1):
    frame = bytearray(8)
    frame[0] = slave_addr
    frame[1] = 0x03
    frame[2] = (start_reg >> 8) & 0xFF
    frame[3] = start_reg & 0xFF
    frame[4] = (count >> 8) & 0xFF
    frame[5] = count & 0xFF
    crc = crc16(frame[:6])
    frame[6] = crc & 0xFF
    frame[7] = (crc >> 8) & 0xFF

    ser.reset_input_buffer()
    ser.write(bytes(frame))
    time.sleep(0.1)
    resp = ser.read(256)
    return resp


def parse_response(resp, addr, scales=None):
    """Parse Modbus response and print decoded values"""
    if resp[0] != addr:
        print(f"  WARN: address mismatch, got 0x{resp[0]:02X}")
        return

    if resp[1] & 0x80:
        exc = resp[2] if len(resp) > 2 else -1
        exc_names = {1: "illegal function", 2: "illegal address",
                     3: "illegal data", 4: "slave failure"}
        print(f"  EXCEPTION: code={exc} ({exc_names.get(exc, '?')})")
        return

    byte_count = resp[2]
    data = resp[3:3 + byte_count]

    # CRC check
    check_data = resp[:3 + byte_count]
    crc_bytes = resp[3 + byte_count:3 + byte_count + 2]
    calc_crc = crc16(check_data)
    recv_crc = crc_bytes[0] | (crc_bytes[1] << 8)
    crc_ok = "OK" if calc_crc == recv_crc else f"MISMATCH(calc=0x{calc_crc:04X})"

    print(f"  func=0x{resp[1]:02X} byte_count={byte_count} CRC={crc_ok}")
    print(f"  raw_data: {data.hex()}")

    # Parse 16-bit registers
    vals = []
    for i in range(0, byte_count, 2):
        v = (data[i] << 8) | data[i + 1]
        vals.append(v)

    if scales:
        print(f"  registers:", end="")
        for i, v in enumerate(vals):
            s = scales[i] if i < len(scales) else 1.0
            print(f" [{i}] raw={v} scaled={v*s:.1f}", end="")
        print()
    else:
        print(f"  registers: {vals}")


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    print(f"PC Modbus Test - Port: {port}")
    print("=" * 60)

    ser = serial.Serial(port, baudrate=9600, bytesize=8,
                        parity='N', stopbits=1, timeout=0.3)

    # --- Weather Station 0x03: read 0x01F8 x8 ---
    print("\n[1] Weather Station addr=0x03 reg=0x01F8 x8")
    resp = modbus_read(ser, 0x03, 0x01F8, 8)
    if resp:
        print(f"  {len(resp)} bytes: {resp.hex()}")
        if len(resp) >= 5:
            weather_scales = [0.1, 0.1, 0.1, 0.1, 1.0, 0.1, 1.0, 1.0]
            weather_names = ["humidity", "air_temp", "noise", "wind_speed",
                             "wind_dir", "pressure", "wind_power", "light"]
            weather_units = ["%RH", "C", "dB", "m/s", "deg", "kPa", "level", "Lux"]
            parse_response(resp, 0x03, weather_scales)
            # Detailed print
            byte_count = resp[2]
            data = resp[3:3 + byte_count]
            vals = []
            for i in range(0, byte_count, 2):
                v = (data[i] << 8) | data[i + 1]
                vals.append(v)
            print(f"  --- Decoded ---")
            for i, v in enumerate(vals):
                s = weather_scales[i]
                print(f"  {weather_names[i]:>12s}: {v:>5d} * {s:>4} = {v*s:>8.1f} {weather_units[i]}")
    else:
        print("  NO RESPONSE")

    time.sleep(0.2)

    # --- Soil Sensor 0x02: read 0x0000 x4 ---
    print("\n[2] Soil Sensor addr=0x02 reg=0x0000 x4")
    resp = modbus_read(ser, 0x02, 0x0000, 4)
    if resp:
        print(f"  {len(resp)} bytes: {resp.hex()}")
        if len(resp) >= 5:
            soil_scales = [0.1, 0.1, 1.0, 0.1]
            soil_names = ["moisture", "temp", "EC", "pH"]
            soil_units = ["%RH", "C", "uS/cm", "pH"]
            parse_response(resp, 0x02, soil_scales)
            byte_count = resp[2]
            data = resp[3:3 + byte_count]
            vals = []
            for i in range(0, byte_count, 2):
                v = (data[i] << 8) | data[i + 1]
                vals.append(v)
            print(f"  --- Decoded ---")
            for i, v in enumerate(vals):
                s = soil_scales[i]
                print(f"  {soil_names[i]:>12s}: {v:>5d} * {s:>4} = {v*s:>8.1f} {soil_units[i]}")
    else:
        print("  NO RESPONSE")

    ser.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
