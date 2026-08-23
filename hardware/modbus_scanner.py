# hardware/modbus_scanner.py
"""
Modbus 总线扫描工具
用于首次调试：扫描 RS485 总线上有哪些设备、dump 寄存器
运行方式：mpremote connect COM17 run hardware/modbus_scanner.py
"""
from modbus_reader import ModbusRTU

# ---- 硬件参数（与 config.py 保持一致） ----
TX = 16
RX = 17
UART_ID = 1
BAUD = 9600


def scan_devices():
    """
    扫描从站地址 1~10，检测哪些地址有响应
    """
    modbus = ModbusRTU(UART_ID, TX, RX, BAUD)
    print("=" * 50)
    print("Modbus 总线扫描")
    print(f"UART{UART_ID}, TX=IO{TX}, RX=IO{RX}, {BAUD}bps")
    print("=" * 50)

    found = []
    for addr in range(1, 11):
        # 尝试功能码 0x03 读取第一个寄存器
        result = modbus.read_holding(addr, 0x0000, 1)
        if result is not None:
            print(f"  [找到] 地址 0x{addr:02X} (={addr}) - 保持寄存器[0]= {result[0]}")
            found.append(addr)
            continue

        # 再试 0x04
        result2 = modbus.read_input(addr, 0x0000, 1)
        if result2 is not None:
            print(f"  [找到] 地址 0x{addr:02X} (={addr}) - 输入寄存器[0]= {result2[0]} (0x04)")
            found.append(addr)

    if not found:
        print("\n  ⚠️ 未发现任何设备！请检查：")
        print("    1. 12V 电源是否供电？")
        print("    2. A/B 线是否接反？（试试黄线接A+、蓝线接B-）")
        print("    3. 波特率是否正确？(当前 {})".format(BAUD))
        print("    4. 传感器和ESP32是否共地？")
    else:
        print(f"\n找到 {len(found)} 个设备: {[hex(a) for a in found]}")
        print("期望: 气象站=0x03, 土壤=0x02")

    return found


def dump_registers(slave_addr, start=0, count=10):
    """dump 指定从站的寄存器内容"""
    modbus = ModbusRTU(UART_ID, TX, RX, BAUD)

    print(f"\n读取从站 0x{slave_addr:02X} 的寄存器 [0x{start:04X} ~ 0x{start+count-1:04X}]:")

    # 先 0x03 再 0x04
    vals = modbus.read_holding(slave_addr, start, count)
    func = "03(保持)"
    if vals is None:
        vals = modbus.read_input(slave_addr, start, count)
        func = "04(输入)"

    if vals is None:
        print("  ❌ 读取失败")
        return None

    print(f"  功能码={func}")
    print(f"  {'地址':>6s}  {'原始值':>8s}  {'÷10换算':>10s}")
    print(f"  {'-'*6}  {'-'*8}  {'-'*10}")
    for i, v in enumerate(vals):
        reg_addr = start + i
        converted = v / 10.0
        print(f"  0x{reg_addr:04X}  {v:>8d}  {converted:>10.1f}")

    return vals


def dump_all():
    """一键扫描 + dump 气象站和土壤传感器"""
    devices = scan_devices()
    if 0x03 in devices:
        print("\n" + "=" * 50)
        print("气象站 (0x03) 全部寄存器 dump")
        print("期望起始地址: 0x01F8")
        print("=" * 50)
        dump_registers(0x03, 0x01F8, 8)
    if 0x02 in devices:
        print("\n" + "=" * 50)
        print("土壤传感器 (0x02) 全部寄存器 dump")
        print("期望起始地址: 0x0000")
        print("=" * 50)
        dump_registers(0x02, 0x0000, 4)


# 直接运行时执行扫描
if __name__ == "__main__":
    dump_all()
