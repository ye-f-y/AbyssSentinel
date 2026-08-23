# hardware/modbus_reader.py
"""
Modbus RTU 读取封装 (MicroPython)
自实现 CRC16，TX 引脚加内部上拉帮助自动方向模块稳定
"""
import time
from machine import UART, Pin


# ============================================================
# CRC16 校验 (Modbus 标准)
# ============================================================
def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class ModbusRTU:
    """Modbus RTU Master - 方案A: TX上拉 + 延长等待"""

    def __init__(self, uart_id, tx_pin, rx_pin, baudrate=9600):
        # TX 引脚加内部上拉，确保空闲时高电平稳定
        # 帮助自动方向模块正确检测"空闲→接收"状态
        self._tx = Pin(tx_pin, Pin.OUT, value=1, pull=Pin.PULL_UP)
        self._rx = Pin(rx_pin, Pin.IN)

        # 先让 TX 稳定在高电平一段时间，确保模块处于接收模式
        time.sleep_ms(50)

        self.uart = UART(uart_id,
                         baudrate=baudrate,
                         bits=8,
                         parity=None,
                         stop=1,
                         tx=self._tx,
                         rx=self._rx)

        time.sleep_ms(30)  # UART 初始化后稳定
        self.retries = 3
        self.debug = True  # 调试模式，打印原始响应

    def _send_frame(self, frame: bytearray):
        """发送 Modbus 帧，确保 TX 时序正确"""
        # 先清接收缓冲
        self.uart.read()
        # 发送
        self.uart.write(frame)
        # 等待发送完成 + 传感器处理 + 响应返回
        # 9600bps: 8字节 ≈ 8.3ms, 传感器处理 ≈ 20-50ms, 响应 ≈ 8-20ms
        # 给足时间让自动方向模块切回接收模式
        time.sleep_ms(120)

    def read_holding(self, slave_addr, start_reg, count):
        """
        功能码 0x03: 读取保持寄存器
        返回: 寄存器值列表 (int)，失败返回 None
        """
        for attempt in range(self.retries):
            try:
                frame = bytearray(8)
                frame[0] = slave_addr
                frame[1] = 0x03
                frame[2] = (start_reg >> 8) & 0xFF
                frame[3] = start_reg & 0xFF
                frame[4] = (count >> 8) & 0xFF
                frame[5] = count & 0xFF
                crc = _crc16(frame[:6])
                frame[6] = crc & 0xFF
                frame[7] = (crc >> 8) & 0xFF

                self._send_frame(frame)

                # 读取所有可用字节
                raw = self.uart.read(128)
                if raw is None or len(raw) < 4:
                    if self.debug and attempt == 0:
                        print(f"  [DBG] addr=0x{slave_addr:02X} reg=0x{start_reg:04X}: "
                              f"no response (attempt {attempt+1}/{self.retries})")
                    if attempt < self.retries - 1:
                        time.sleep_ms(200)
                    continue

                if self.debug and attempt == 0:
                    print(f"  [DBG] addr=0x{slave_addr:02X} reg=0x{start_reg:04X}: "
                          f"{len(raw)}B {raw.hex()}")

                # 跳过 TX echo（前 8 字节 = 我们的请求被回音）
                resp = raw
                if len(resp) > 8 and resp[:6] == frame[:6]:
                    # 去掉 echo 部分
                    resp = resp[8:]
                    if self.debug and attempt == 0:
                        print(f"  [DBG] stripped echo, sensor response: {len(resp)}B {resp.hex()}")

                if len(resp) < 4:
                    continue

                resp_addr = resp[0]
                resp_func = resp[1]

                # 检查异常响应
                if resp_func & 0x80:
                    exc = resp[2] if len(resp) > 2 else -1
                    if self.debug:
                        print(f"  [DBG] exception: func=0x{resp_func:02X} code={exc}")
                    continue

                byte_count = resp[2]
                expected_len = 3 + byte_count + 2
                if len(resp) < expected_len:
                    continue

                data_bytes = resp[3:3 + byte_count]
                crc_bytes = resp[3 + byte_count:3 + byte_count + 2]

                # CRC 校验
                check_data = resp[:3 + byte_count]
                expected_crc = _crc16(check_data)
                received_crc = crc_bytes[0] | (crc_bytes[1] << 8)
                if expected_crc != received_crc:
                    if self.debug:
                        print(f"  [DBG] CRC mismatch: calc=0x{expected_crc:04X} recv=0x{received_crc:04X}")
                    continue

                # 解析寄存器值
                values = []
                for i in range(0, byte_count, 2):
                    val = (data_bytes[i] << 8) | data_bytes[i + 1]
                    values.append(val)

                if self.debug:
                    print(f"  [DBG] SUCCESS: {values}")
                return values

            except Exception as e:
                if self.debug and attempt == 0:
                    print(f"  [DBG] exception: {e}")

        return None

    def read_input(self, slave_addr, start_reg, count):
        """
        功能码 0x04: 读取输入寄存器
        """
        for attempt in range(self.retries):
            try:
                frame = bytearray(8)
                frame[0] = slave_addr
                frame[1] = 0x04
                frame[2] = (start_reg >> 8) & 0xFF
                frame[3] = start_reg & 0xFF
                frame[4] = (count >> 8) & 0xFF
                frame[5] = count & 0xFF
                crc = _crc16(frame[:6])
                frame[6] = crc & 0xFF
                frame[7] = (crc >> 8) & 0xFF

                self._send_frame(frame)

                raw = self.uart.read(128)
                if raw is None or len(raw) < 4:
                    if attempt < self.retries - 1:
                        time.sleep_ms(200)
                    continue

                # 跳过 echo
                resp = raw
                if len(resp) > 8 and resp[:6] == frame[:6]:
                    resp = resp[8:]

                if len(resp) < 4:
                    continue

                resp_addr = resp[0]
                resp_func = resp[1]

                if resp_func & 0x80:
                    continue

                byte_count = resp[2]
                expected_len = 3 + byte_count + 2
                if len(resp) < expected_len:
                    continue

                data_bytes = resp[3:3 + byte_count]
                crc_bytes = resp[3 + byte_count:3 + byte_count + 2]

                check_data = resp[:3 + byte_count]
                expected_crc = _crc16(check_data)
                received_crc = crc_bytes[0] | (crc_bytes[1] << 8)
                if expected_crc != received_crc:
                    continue

                values = []
                for i in range(0, byte_count, 2):
                    val = (data_bytes[i] << 8) | data_bytes[i + 1]
                    values.append(val)

                return values

            except Exception as e:
                if attempt < self.retries - 1:
                    time.sleep_ms(100)

        return None
