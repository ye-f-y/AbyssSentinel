# 🛡️ ABYSS SENTINEL · 深渊哨兵

## 城市防汛与边坡灾害 AI 数字孪生预警系统

---

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vuedotjs)](https://vuejs.org/)
[![Three.js](https://img.shields.io/badge/Three.js-v0.170-black?logo=threedotjs)](https://threejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--V3.1-4D6BFE)](https://aiping.cn/)
[![EMQX](https://img.shields.io/badge/EMQX-MQTT_Broker-00E4A0?logo=mqtt)](https://www.emqx.com/)
[![ESP32](https://img.shields.io/badge/ESP32--S3-MicroPython-00979D?logo=espressif)](https://www.espressif.com/)
[![SQLite](https://img.shields.io/badge/SQLite-审计链-003B57?logo=sqlite)](https://www.sqlite.org/)

---

## 📖 项目简介

**深渊哨兵**是一套基于大模型 Agent 与数字孪生技术的城市内涝与边坡灾害 AI 预警系统。

传统防汛系统在水位超警戒线后才被动报警——此时水已淹、损失已发生。深渊哨兵的核心创新在于 **"不等灾害发生，在暴雨前兆阶段由 AI 主动推演灾害链并提前执行预防措施"**，实现"灾害链超前阻断"，为城市韧性基础设施建设提供 AI 大脑。

系统感知层基于标准 MQTT 物联网协议，已完成工业级 RS485 气象/土壤传感器与 ESP32 执行终端的全链路开发，任何遵循该协议的传感设备均可即插即用；上层结合 RAG（检索增强生成）技术让大模型像防汛专家一样进行灾害链推演，并在灾害发生前于 3D 数字孪生大屏中执行预排空等干预指令。本仓库演示通过注入与真实硬件完全同构的传感器数据流，完整呈现 **"感知 → 规则判级 → RAG 检索 → AI 推演 → 决策执行 → 审计留痕"** 全流程。

> 🚀 **快速上手请看 [RUN.md](RUN.md) —— 完整启动/演示/排障手册**

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
│ 第一层：感知层（硬件 / 数据注入器）                         │
│   RS485 Modbus RTU → ESP32-S3 → WiFi → MQTT             │
│   （注入器 test_inject.py 走完全相同的协议与数据格式）      │
├─────────────────────────────────────────────────────────┤
│ 第二层：消息层（EMQX）                                     │
│   4个Topic：sensor_data / commands / ai_analysis / status│
├──────────────────────┬──────────────────────────────────┤
│ 第三层：决策层（AI）   │ 第四层：展示层（大屏）              │
│   Python FastAPI      │   Vue3 + Three.js + ECharts      │
│   规则引擎+RAG+LLM    │   MQTT.js WebSocket               │
│   ChromaDB 知识库     │   3D下凹立交 + 悬浮卡片 + 趋势图   │
│   SQLite 预警审计链   │                                  │
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
- ⚡ **规则引擎** — 毫秒级快速判断，AI 不可用时自动降级兜底
- 📚 **RAG 国标知识库** — GB51174-2017 + GB50330-2013 向量检索（ChromaDB 255 条切片）
- 🔌 **硬件控制** — AI 决策经 Function Calling 自动下发排水指令，ESP32 继电器物理执行
- 🗄️ **预警审计链** — SQLite 持久化 4 张表：传感器时序 / 风险事件 / AI 推演全文 / 控制指令，每次预警可追溯、可复盘

### 辅助功能

- 🎬 **一键演示** — 5 阶段全自动灾害链推演（断网/API 故障时的保底演示）
- 🕹️ **数据模拟器** — 滑块手动调整传感器参数
- 📊 **历史趋势图** — ECharts 实时绘制气压/土壤湿度曲线
- 💧 **积水深度显示** — 底部悬浮卡片，颜色状态（绿/黄/红）
- 🔧 **MQTT 注入器** — 批量推送极端数据，脱离硬件独立验证
- 📡 **历史查询 API** — 降采样时序查询 / 事件链 / 推演记录 / 指令审计 / 统计摘要

---

## 📦 技术栈

| 层                   | 技术                                         | 版本             |
| -------------------- | -------------------------------------------- | ---------------- |
| **硬件主控**   | ESP32-S3 (行空板 K10) MicroPython            | v1.28            |
| **传感器通信** | RS485 Modbus RTU, CRC16                      | 9600bps          |
| **消息中间件** | EMQX MQTT Broker                             | latest           |
| **后端框架**   | Python FastAPI + Uvicorn                     | 0.115            |
| **AI 模型**    | DeepSeek-V3.1（aiping.cn，OpenAI 兼容接口，可配置切换） | -        |
| **Embedding**  | Qwen3-Embedding-0.6B（RAG 向量化）           | 1024 维          |
| **向量数据库** | ChromaDB (本地)                              | ≥0.5.23          |
| **持久化**     | SQLite（WAL 模式 + 线程安全写入）            | 内置             |
| **3D 引擎**    | Three.js                                     | v0.170           |
| **前端框架**   | Vue3 + Vite                                  | Vue 3.4 / Vite 6 |
| **图表库**     | ECharts                                      | 5.5              |
| **MQTT 库**    | paho-mqtt (Python) / mqtt.js (Browser)       | 1.6.1 / 5.10     |

> LLM 与 Embedding 均通过 `.env` 配置化（`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `EMBEDDING_MODEL`），
> 换模型只改配置不改代码。

---

## 🚀 快速启动

### 前置条件

| 软件                  | 说明         |
| --------------------- | ------------ |
| **Python 3.12** | 后端运行环境 |
| **Node.js 18+** | 前端运行环境 |
| **EMQX**        | Docker       |
| **LLM API Key** | 任意 OpenAI 兼容接口（大赛用 aiping.cn） |

### 1. 克隆项目

```bash
git clone https://github.com/ye-f-y/AbyssSentinel.git
cd AbyssSentinel
```

### 2. 启动 EMQX

```bash
# Docker（推荐）
docker run -d --name emqx -p 1883:1883 -p 8083:8083 -p 18083:18083 emqx/emqx:latest
```

访问 http://localhost:18083 确认 Dashboard 可打开（默认账号 `admin`，密码 `public`）。

### 3. 启动后端

```powershell
cd backend

# 创建虚拟环境 + 安装依赖（仅首次）
python -m venv venv
.\venv\Scripts\activate
pip install -r requirement.txt

# 配置 API Key（仅首次）
copy .env.example .env
# 编辑 .env，填入你自己的 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

# 构建国标知识库（仅首次，需联网调用 embedding 接口）
python rag/build_index.py

# 启动后端
python main.py
```

看到以下输出即启动成功：

```
✅ 持久化数据库就绪: ...\backend\data\sentinel.db
知识库加载成功，共 255 条
AI推演模型: DeepSeek-V3.1 @ https://aiping.cn/api/v1
MQTT已连接: 127.0.0.1
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

### 5. 验证全链路（无需硬件）

```powershell
# 运行 MQTT 灾害链模拟注入器（与真实传感器走完全相同的协议和数据格式）
cd ..
python hardware/test_inject.py

# 只看紧急阶段
python hardware/test_inject.py --stage critical

# 循环播放
python hardware/test_inject.py --loop
```

注入过程中可观察：大屏 3D 场景联动（天空变暗→暴雨→积水→泵站排水）、AI 推演终端 5 段结构化输出、风险等级四色变化。

### 6. 查看预警审计链（AI 做过什么决策，全程可追溯）

| API                                  | 内容                             |
| ------------------------------------ | -------------------------------- |
| `GET /api/stats/summary`             | 总记录数 / 今日预警事件 / 历史最高风险等级 |
| `GET /api/history/events`            | 风险等级变化事件链（含触发原因与传感器快照） |
| `GET /api/history/analyses`          | AI 每次推演的全文和国标引用        |
| `GET /api/history/commands`          | AI 下发过的排水指令审计           |
| `GET /api/history/sensors?hours=24`  | 传感器时序历史（降采样）          |

---

## 📁 项目结构

```
AbyssSentinel/
├── README.md              ← 本文件
├── RUN.md                 ← 运行手册（启动/演示/排障）
│
├── backend/               ← Python 后端（FastAPI + MQTT + AI）
│   ├── main.py            ← 入口：启动 FastAPI + MQTT + 数据库
│   ├── .env.example       ← 环境变量模板（复制为 .env 使用）
│   ├── requirement.txt    ← Python 依赖清单
│   ├── core/
│   │   ├── rule_engine.py ← 规则引擎（毫秒级阈值判定）
│   │   ├── agent.py       ← AI 推演核心（5 段结构 + RAG + Function Calling）
│   │   ├── database.py    ← SQLite 持久化（4 张表 + 预警审计链）
│   │   └── mqtt_client.py ← MQTT 通信（收发 + 异步推演 + 入库钩子）
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
│           ├── AbyssScene.vue   ← 3D 下凹立交城市（Three.js）
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

### 5. Windows 下 localhost 解析不确定性

**现象**：本机 Docker EMQX 存在 IPv4（docker backend）/ IPv6（wslrelay）两条转发通路，`localhost` 解析结果不确定，偶发连不上或连错通路。

**解决**：`.env` 中固定 `MQTT_BROKER=127.0.0.1`（已内置）；前端如遇大屏不联动，将 `mqttClient.js` 中的 `ws://localhost:8083/mqtt` 改为 `ws://127.0.0.1:8083/mqtt`。

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

## 🗄️ 预警审计链（数据持久化）

每次灾害链推演的全过程自动写入 SQLite（`backend/data/sentinel.db`）：

```
sensor_readings ──→ risk_events ──→ ai_analyses ──→ control_commands
  传感器时序数据     风险等级事件      AI推演全文+国标引用   指令执行审计
```

- 回答评审/业主最关心的问题：**"AI 做过什么决策？依据是什么？"** —— 全程可追溯
- 数据支撑后续的阈值自学习、What-if 推演、预警复盘报告
- 线程安全写入（MQTT 线程 + AI 异步线程），WAL 模式提升读写并发

---

## 📞 联系方式

如有问题，请提交 Issue 或联系项目维护者。

---

<p align="center">
  <strong>ABYSS SENTINEL · 深渊哨兵</strong>
  <br>
  <em>不等灾害发生，提前预防干预 🛡️</em>
</p>
