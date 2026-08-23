# hardware/raw_dump.py
"""
测试2：预置TX高电平 + 更长延迟 + 重试
"""
from machine import UART, Pin
import time


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def modbus_read(uart, addr, start_reg, count=1):
    frame = bytearray(8)
    frame[0] = addr
    frame[1] = 0x03
    frame[2] = (start_reg >> 8) & 0xFF
    frame[3] = start_reg & 0xFF
    frame[4] = (count >> 8) & 0xFF
    frame[5] = count & 0xFF
    crc = crc16(frame[:6])
    frame[6] = crc & 0xFF
    frame[7] = (crc >> 8) & 0xFF

    uart.read()
    uart.write(frame)

    # 等更久：200ms 后开始读
    time.sleep_ms(200)

    # 分两次读：先读 echo (前8字节)，再读传感器响应
    echo = uart.read(8)
    time.sleep_ms(100)
    resp = uart.read(128)

    return echo, resp


def main():
    # 关键：先手动把 TX 拉高，让自动方向模块稳定在接收模式
    tx = Pin(16, Pin.OUT, value=1)
    rx = Pin(17, Pin.IN)
    time.sleep_ms(100)  # 等模块稳定

    uart = UART(1, baudrate=9600, bits=8, parity=None, stop=1, tx=tx, rx=rx)
    time.sleep_ms(50)

    print("ESP32 Modbus 诊断 (TX预置高电平)")
    print("UART1 TX=IO16 RX=IO17 @9600bps")
    print()

    tests = [
        ("气象站 0x03 reg=0x01F8", 0x03, 0x01F8),
        ("土壤   0x02 reg=0x0000", 0x02, 0x0000),
    ]

    for name, addr, reg in tests:
        for attempt in range(3):
            echo, resp = modbus_read(uart, addr, reg, 1)
            total = (len(echo) if echo else 0) + (len(resp) if resp else 0)
            print(f"{name} 第{attempt+1}次: echo={len(echo) if echo else 0}B resp={len(resp) if resp else 0}B 总共={total}B")

            if resp:
                print(f"  传感器数据: {resp.hex()}")
                # 尝试解析
                if len(resp) >= 5:
                    r_addr = resp[0]
                    r_func = resp[1]
                    if r_func & 0x80:
                        print(f"  → 异常响应 func=0x{r_func:02X} code={resp[2]}")
                    else:
                        bc = resp[2]
                        print(f"  → addr={r_addr} func=0x{r_func:02X} byte_count={bc}")
                        if len(resp) >= 3 + bc + 2:
                            data = resp[3:3+bc]
                            vals = []
                            for i in range(0, bc, 2):
                                v = (data[i] << 8) | data[i+1]
                                vals.append(v)
                            print(f"  → 寄存器值: {vals}")
                break  # 有响应就停
            time.sleep_ms(100)

    print("\n完成！")

main()
