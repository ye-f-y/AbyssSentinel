# 🛡️ ABYSS SENTINEL · 深渊哨兵

## 城市防汛与边坡灾害 AI 数字孪生预警系统

---

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vuedotjs)](https://vuejs.org/)
[![Three.js](https://img.shields.io/badge/Three.js-v0.170-black?logo=threedotjs)](https://threejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![EMQX](https://img.shields.io/badge/EMQX-MQTT_Broker-00E4A0?logo=mqtt)](https://www.emqx.com/)
[![ESP32](https://img.shields.io/badge/ESP32--S3-MicroPython-00979D?logo=espressif)](https://www.espressif.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

---

## 📖 项目简介

**深渊哨兵**是一套面向城市防汛与边坡地质灾害场景的 **AI 数字孪生预警系统**。

传统防汛系统在水位超警戒线后才被动报警——此时水已淹、损失已发生。深渊哨兵的核心创新在于 **"不等灾害发生，在暴雨前兆阶段由 AI 主动推演并提前执行预防措施"**。

系统通过工业级 RS485 传感器实时采集气象（8项）与土壤（4项）数据，经 MQTT 消息中间件传输至 AI 决策后端。后端由规则引擎（毫秒级快速判断）+ ChromaDB 国标知识库（RAG 向量检索）+ 通义千问大模型（灾害链推演 + Function Calling 自动排水决策）组成三级智能。分析结果驱动 Three.js 3D 下凹立交桥城市数字孪生场景实时联动，并通过 ESP32 继电器实现物理层面的排水执行。

---

## 🎯 核心理念

```
传统系统：  水位超警戒 → 被动报警 → 人工处理  （水已淹）
深渊哨兵：  气压骤降 + 土壤变湿 → AI主动推演 → 提前排水  （灾害未发生）
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│ 第一层：感知层（硬件）                                     │
│   RS485 Modbus RTU → ESP32-S3 → WiFi → MQTT              │
├─────────────────────────────────────────────────────────┤
│ 第二层：消息层（EMQX）                                     │
│   4个Topic：sensor_data / commands / ai_analysis / status│
├──────────────────────┬──────────────────────────────────┤
│ 第三层：决策层（AI）   │ 第四层：展示层（大屏）              │
│   Python FastAPI      │   Vue3 + Three.js + ECharts      │
│   规则引擎+RAG+LLM    │   MQTT.js WebSocket               │
│   ChromaDB 知识库     │   3D下凹立交 + 悬浮卡片 + 趋势图   │
└──────────────────────┴──────────────────────────────────┘
```

数据流闭环延迟 < 2 秒。四层独立解耦，每层可单独开发、测试、替换。

---

## ✨ 功能特性

### 核心功能

- 📡 **实时传感器监测** — 气象站 8 项 + 土壤 4 项参数，5 秒刷新，趋势箭头
- 🌐 **3D 数字孪生场景** — Three.js 下凹立交桥城市，数据驱动暴雨/积水/排水
- 🧠 **AI 推演终端** — 5 段结构化输出（数据解读/灾害链推演/国标依据/风险评级/决策说明）
- 🎚️ **风险仪表盘** — NORMAL→WATCH→WARNING→CRITICAL 四色升级，紧急时红色闪烁
- 📨 **MQTT 实时通信** — EMQX 本地 Broker，4 个 Topic，QoS 1 可靠传输
- ⚡ **规则引擎** — 12 条硬阈值规则，毫秒级快速判断
- 📚 **RAG 国标知识库** — GB51174-2017 + GB50330-2013 向量检索
- 🔌 **硬件控制** — AI 决策自动下发排水指令，ESP32 继电器物理执行

### 辅助功能

- 🎬 **一键演示** — 5 阶段全自动灾害链推演（约 60 秒）
- 🕹️ **数据模拟器** — 滑块手动调整传感器参数
- 📊 **历史趋势图** — ECharts 实时绘制气压/土壤湿度曲线
- 💧 **积水深度显示** — 底部悬浮卡片，颜色状态（绿/黄/红）
- 🔧 **MQTT 注入器** — 批量推送极端数据，脱离硬件独立验证

---

## 📦 技术栈

| 层                   | 技术                                   | 版本             |
| -------------------- | -------------------------------------- | ---------------- |
| **硬件主控**   | ESP32-S3 (行空板 K10) MicroPython      | v1.28            |
| **传感器通信** | RS485 Modbus RTU, CRC16                | 9600bps          |
| **消息中间件** | EMQX MQTT Broker                       | latest           |
| **后端框架**   | Python FastAPI + Uvicorn               | 0.115            |
| **AI 模型**    | 通义千问 Qwen-Plus (DashScope API)     | -                |
| **向量数据库** | ChromaDB (本地)                        | ≥0.5.23         |
| **3D 引擎**    | Three.js                               | v0.170           |
| **前端框架**   | Vue3 + Vite                            | Vue 3.4 / Vite 6 |
| **图表库**     | ECharts                                | 5.5              |
| **MQTT 库**    | paho-mqtt (Python) / mqtt.js (Browser) | 1.6.1 / 5.10     |

---

## 🚀 快速启动

### 前置条件

| 软件                  | 说明         |
| --------------------- | ------------ |
| **Python 3.12** | 后端运行环境 |
| **Node.js 18+** | 前端运行环境 |
| **EMQX**        | Docker       |

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd AbyssSentinel
```

### 2. 启动 EMQX

```bash
# Docker（推荐）
docker run -d --name emqx -p 1883:1883 -p 8083:8083 -p 18083:18083 emqx/emqx:latest

# Windows 安装包：开始菜单启动 EMQX
```

访问 http://localhost:18083 确认 Dashboard 可打开（默认账号 `admin`，密码 `public`）。

### 3. 启动后端

```powershell
cd backend

# 创建虚拟环境 + 安装依赖（仅首次）
python -m venv venv
.\venv\Scripts\activate
pip install -r requirement.txt

# 配置通义千问 API Key
# 编辑 backend/.env，填入: DASHSCOPE_API_KEY=sk-xxxxxxxx

# 构建国标知识库（仅首次，约 30 秒）
python rag/build_index.py

# 启动后端
python main.py
```

### 4. 启动前端

```powershell
cd frontend

# 安装依赖（仅首次）
npm install

# 启动开发服务器
npm run dev
```

打开浏览器访问 **http://localhost:5173**。

### 5. 验证全链路

```powershell
# 无需硬件——运行 MQTT 灾害链模拟注入器
cd ..
python hardware/test_inject.py

# 只看紧急阶段
python hardware/test_inject.py --stage critical

# 循环播放
python hardware/test_inject.py --loop
```

---

## 📁 项目结构

```
AbyssSentinel/
├── README.md              ← 本文件
│
├── backend/               ← Python 后端（FastAPI + MQTT + AI）
│   ├── main.py            ← 入口：启动 FastAPI + MQTT
│   ├── .env               ← API Key 配置
│   ├── .env.example       ← 环境变量模板
│   ├── requirement.txt    ← Python 依赖清单
│   ├── core/
│   │   ├── rule_engine.py ← 规则引擎（12 条阈值规则，毫秒判定）
│   │   ├── agent.py       ← AI 推演核心（5 段结构 + RAG + Function Calling）
│   │   └── mqtt_client.py ← MQTT 通信（收发 + 异步推演）
│   └── rag/
│       ├── build_index.py ← 知识库构建（扫描版 PDF 检测 + 预置条款）
│       ├── retriever.py   ← ChromaDB 向量检索
│       └── docs/          ← 国标 PDF 原文件（2 份）
│
├── frontend/              ← Vue3 前端（数字孪生大屏）
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue        ← 根组件（一键演示 + 悬浮布局）
│       ├── utils/
│       │   ├── dataStore.js  ← 全局数据中心（reactive）
│       │   └── mqttClient.js ← MQTT.js 浏览器连接
│       └── components/
│           ├── AbyssScene.vue   ← 3D 下凹立交城市（~1900 行，Three.js）
│           ├── SensorPanel.vue  ← 左侧传感器面板
│           └── AIConsole.vue    ← 右侧 AI 推演终端
│
└── hardware/              ← ESP32 MicroPython + PC 端工具
    ├── config.py          ← ESP32 配置（WiFi/MQTT/Modbus/继电器）
    ├── main.py            ← ESP32 主程序（采集+上报+继电器）
    ├── modbus_reader.py   ← Modbus RTU 读取器（CRC16 自实现）
    ├── modbus_scanner.py  ← 总线扫描调试工具
    ├── esp32_relay.py     ← ESP32 简化版（仅 WiFi+继电器+心跳）
    ├── pc_bridge.py       ← PC 端传感器桥接器（USB-RS485→MQTT）
    ├── pc_modbus_test.py  ← PC 端 Modbus 直连测试工具
    ├── test_inject.py     ← MQTT 灾害链模拟数据注入器 ⭐
    ├── mqtt_listener.py   ← MQTT 频道监听工具
    ├── mock_sensor.py     ← 传感器模拟器
    └── diag.py            ← UART/Modbus 硬件诊断工具
```

---

## 🔧 硬件配置

### 硬件清单

| 编号 | 设备       | 型号                            | 数量 |
| :--: | ---------- | ------------------------------- | :--: |
|  H1  | 主控板     | ESP32-S3 行空板 K10             |  1  |
|  H2  | 气象传感器 | RS-FSXCS-N01-3（8 合 1）        |  1  |
|  H3  | 土壤传感器 | SN-3001-TR-ECTHPH-N01（4 合 1） |  1  |
|  H4  | RS485 模块 | MAX3485（3.3V 兼容）            |  1  |
|  H5  | 继电器     | JQC3F-05VDC-C                   |  1  |
|  H6  | 电源       | 12V 适配器                      |  1  |

### 传感器寄存器映射

**气象站 (RS-FSXCS-N01-3, Modbus 地址 0x03)**：

| 寄存器 | 参数     | 换算 | 单位 |
| ------ | -------- | :--: | ---- |
| 0x01F8 | 空气湿度 | ÷10 | %RH  |
| 0x01F9 | 气温     | ÷10 | ℃   |
| 0x01FA | 噪音     | ÷10 | dB   |
| 0x01FB | 风速     | ÷10 | m/s  |
| 0x01FC | 风向     | 直读 | °   |
| 0x01FD | 大气压   | ÷10 | kPa  |
| 0x01FE | 风力等级 | 直读 | 0-17 |
| 0x01FF | 光照     | 直读 | Lux  |

**土壤传感器 (SN-3001-TR-ECTHPH-N01, Modbus 地址 0x02)**：

| 寄存器 | 参数      | 换算 | 单位   |
| ------ | --------- | :--: | ------ |
| 0x0000 | 土壤湿度  | ÷10 | %RH    |
| 0x0001 | 土壤温度  | ÷10 | ℃     |
| 0x0002 | EC 电导率 | 直读 | μS/cm |
| 0x0003 | pH 酸碱度 | ÷10 | —     |

### ESP32 引脚接线

| ESP32 引脚 | 连接目标       | 说明          |
| ---------- | -------------- | ------------- |
| IO16 (TX)  | RS485 模块 RXD | UART1 发送    |
| IO17 (RX)  | RS485 模块 TXD | UART1 接收    |
| IO15       | 继电器 IN      | 排水控制      |
| 5V         | RS485 模块 VCC | 模块供电      |
| GND        | 所有设备共地   | ⚠️ 必须连接 |

### 上传 ESP32 代码

```powershell
# 安装上传工具
pip install mpremote

# 安装 ESP32 MQTT 库
python -m mpremote connect COM17 mip install umqtt.simple

# 上传代码
python -m mpremote connect COM17 cp hardware/config.py :config.py
python -m mpremote connect COM17 cp hardware/modbus_reader.py :modbus_reader.py
python -m mpremote connect COM17 cp hardware/main.py :main.py

# 运行（ESP32 上电即自动执行 main.py）
```

---

## 🧪 测试工具

| 工具                        | 命令                                        | 用途                     |
| --------------------------- | ------------------------------------------- | ------------------------ |
| **MQTT 灾害链注入器** | `python hardware/test_inject.py`          | 5 阶段极端数据批量注入   |
| **MQTT 频道监听**     | `python hardware/mqtt_listener.py`        | 监听 sensor_data 频道    |
| **PC Modbus 测试**    | `python hardware/pc_modbus_test.py COM18` | USB-RS485 直连传感器验证 |
| **EMQX Dashboard**    | http://localhost:18083                      | WebSocket 客户端实时查看 |
| **后端 API 文档**     | http://localhost:8000/docs                  | FastAPI Swagger UI       |
| **前端大屏**          | http://localhost:5173                       | 数字孪生可视化           |

---

## 🐛 已知问题与解决

### 1. XY-485 RS485 模块不兼容 ESP32 (已解决)

**现象**：ESP32 发送 Modbus 请求后只收到 TX 回音，传感器零响应。

**根因**：XY-485(HW-726) 使用 MAX485 芯片，TTL 高电平阈值约 3.5V（5V 供电时），ESP32 GPIO 输出仅 3.3V。自动方向检测电路卡在发送模式。

**解决方案**：

- **临时方案 C**：PC USB-RS485 桥接器 (`pc_bridge.py`)
- **永久方案 D**：替换为 MAX3485（3.3V 兼容），已订购

### 2. ChromaDB 0.5.0 需要 MSVC 编译

**解决**：更新至 `chromadb>=0.5.23`（提供 Windows 预编译 wheel）。

### 3. httpx 0.28+ 与 openai 1.50 不兼容

**解决**：锁定 `httpx==0.27.2`。

### 4. paho-mqtt 2.0 API 不兼容现有代码

**解决**：锁定 `paho-mqtt==1.6.1`。

---

## 📋 MQTT 频道定义

| 频道                       | 方向                  | QoS | 内容                                                 |
| -------------------------- | --------------------- | :-: | ---------------------------------------------------- |
| `sentinel/sensor_data`   | ESP32/PC → 后端+前端 |  1  | 传感器 JSON（weather 8 项 + soil 4 项）              |
| `sentinel/commands`      | 后端 → ESP32+前端    |  1  | 排水控制指令`{action:"pump_on", duration, reason}` |
| `sentinel/ai_analysis`   | 后端 → 前端          |  1  | AI 推演 5 段结构化文字                               |
| `sentinel/device_status` | ESP32 → 前端         |  1  | 设备心跳`{status, relay_state, timestamp}`         |

---

## 🎨 视觉设计

- **主色调**：蓝色渐变 `#99c0fe → #4786d4`
- **布局**：3D 场景全屏铺底 + 左右悬浮半透明卡片
- **风险配色**：NORMAL 蓝 / WATCH 淡金 / WARNING 橙 / CRITICAL 红闪
- **字体**：Orbitron（英文标题）+ Consolas（等宽数据）+ Microsoft YaHei（中文）

---
