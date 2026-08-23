# hardware/diag.py
"""
ESP32 硬件诊断工具 - 自动尝试不同 UART/波特率/引脚组合
运行方式：mpremote connect COM17 run hardware/diag.py
"""
from machine import UART, Pin
import time


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def try_scan(uart_id, tx, rx, baud, slave_addr=0x03):
    """尝试用给定参数读取传感器"""
    try:
        uart = UART(uart_id,
                    baudrate=baud,
                    bits=8,
                    parity=None,
                    stop=1,
                    tx=Pin(tx),
                    rx=Pin(rx))
    except Exception as e:
        print(f"    UART初始化失败: {e}")
        return None

    # 构造 Modbus 请求 (读从站0x03的第一个寄存器）
    frame = bytearray(8)
    frame[0] = slave_addr
    frame[1] = 0x03
    frame[2] = 0x01  # 起始地址 0x01F8 高字节
    frame[3] = 0xF8  # 起始地址 0x01F8 低字节
    frame[4] = 0x00
    frame[5] = 0x01  # 读1个寄存器
    crc = crc16(frame[:6])
    frame[6] = crc & 0xFF
    frame[7] = (crc >> 8) & 0xFF

    # 清缓冲
    uart.read()
    # 发送
    uart.write(frame)
    time.sleep_ms(80)

    # 读取
    resp = uart.read(7)  # 地址+功能码+字节数+2字节数据+2字节CRC
    if resp and len(resp) >= 5:
        return resp
    return None


def scan_all():
    """遍历所有 UART ID + 引脚 + 波特率组合"""
    print("=" * 50)
    print("ESP32-S3 Modbus 诊断工具")
    print("=" * 50)

    # 列出可用的引脚组合
    pin_combos = [
        # (UART_ID, TX, RX)
        (2, 17, 16),
        (1, 17, 16),
        (2, 16, 17),
        (1, 16, 17),
    ]

    baud_rates = [9600, 4800, 19200]
    slave_addrs = [0x03, 0x02, 0x01]

    for uart_id, tx, rx in pin_combos:
        for baud in baud_rates:
            for addr in slave_addrs:
                print(f"UART{uart_id} TX=IO{tx} RX=IO{rx} @{baud}bps addr=0x{addr:02X} ...", end=" ")
                try:
                    result = try_scan(uart_id, tx, rx, baud, addr)
                    if result:
                        print(f"✅ 响应! {result.hex()}")
                    else:
                        print("❌ 无响应")
                except Exception as e:
                    print(f"💥 崩溃: {e}")
                time.sleep_ms(100)

    print("\n诊断完成。有 ✅ 的组合就是可用的配置。")

scan_all()
