# m ABYSS SENTINEL 项目开发指引

> **深渊哨兵**是一套基于大模型Agent与数字孪生技术的城市内涝与边坡灾害AI预警系统。系统感知层基于标准MQTT物联网协议，已完成工业级RS485气象/土壤传感器与ESP32执行终端的全链路开发，任何遵循该协议的传感设备均可即插即用；上层结合RAG（检索增强生成）技术让大模型像防汛专家一样进行灾害链推演，并在灾害发生前于3D数字孪生大屏中执行预排空等干预指令，实现"灾害链超前阻断"，为城市韧性基础设施建设提供AI大脑。

## 项目简介

城市防汛与边坡灾害AI  数字孪生预警系统。ESP32-S3硬件采集传感器数据 → MQTT消息 → Python后端AI分析 → Vue3+Three.js前端大屏展示。

## 快速启动（开发环境）

```powershell
# 1. 启动 EMQX（Windows 开始菜单 或 Docker）
# 2. 启动后端
cd backend
.\venv\Scripts\activate
python main.py

# 3. 启动前端
cd frontend
npm run dev

# 4. 打开浏览器 http://localhost:5173
```

### MQTT 模拟测试（不需要硬件）

```powershell
# 完整5阶段灾害链演示（约60秒）
python hardware/test_inject.py

# 只看紧急阶段
python hardware/test_inject.py --stage critical

# 循环播放
python hardware/test_inject.py --loop
```

### 硬件传感器接入（当前方案C）

```powershell
# USB-RS485转换器直连传感器 → MQTT桥接
python hardware/pc_bridge.py COM18    # COM口号按实际调整
```

## 重要文件路径

### 项目标准文档

- [运行手册](RUN.md) — 完整启动/演示/排障指南（含黑客松现场注意事项）
- [开发需求](docs/requirements.md) — 功能清单与用户确认的完整需求
- [技术规范](docs/tech_spec.md) — 技术栈、MQTT频道定义、数据格式
- [设计规范](docs/design_spec.md) — 视觉风格、配色方案、布局规范
- [need.md](need.md) — 用户原始需求文档（含硬件接线、传感器参数）

### 开发日志

- 日志目录：[devlog/](devlog/)
- 最新日志：[devlog/2026-08-22.md](devlog/2026-08-22.md)

## 工作约定

### 语言

- 与用户对话使用中文
- 代码注释使用中文（简洁）
- 变量和函数命名使用英文

### 开发原则

- 一步一步来，每次只做一个模块，做完验证没问题再做下一个
- 不要一口气写大量代码，确保项目稳定安全推进
- 每完成一个模块，更新开发日志
- 优先使用项目已有的模拟数据来验证功能，不依赖硬件

### 项目结构

```
AbyssSentinel/
├── CLAUDE.md          ← AI工作指引（本文件）
├── need.md            ← 用户原始需求文档（含传感器参数、接线图）
├── docs/              ← 项目标准文档
│   ├── requirements.md
│   ├── tech_spec.md
│   └── design_spec.md
├── devlog/            ← 开发日志（每日）
├── hardware/          ← ESP32 MicroPython代码 + PC端工具
│   ├── config.py           ← ESP32 WiFi/MQTT/Modbus/继电器配置
│   ├── main.py             ← ESP32主程序（传感器+MQTT+继电器）
│   ├── modbus_reader.py    ← Modbus RTU读取器（CRC16自实现）
│   ├── modbus_scanner.py   ← 总线扫描调试工具
│   ├── esp32_relay.py      ← ESP32简化版（仅WiFi+继电器+心跳）
│   ├── pc_bridge.py        ← PC端传感器桥接器（USB-RS485→MQTT）
│   ├── pc_modbus_test.py   ← PC端Modbus直连测试工具
│   ├── test_inject.py      ← MQTT灾害链模拟数据注入器
│   ├── mqtt_listener.py    ← MQTT频道监听调试工具
│   ├── mock_sensor.py      ← 传感器模拟器（无硬件时用）
│   ├── diag.py             ← UART/Modbus诊断工具
│   └── raw_dump.py         ← 原始Modbus字节dump工具
├── backend/           ← Python后端（FastAPI + MQTT + AI）
│   ├── main.py
│   ├── .env
│   ├── requirement.txt
│   ├── core/
│   │   ├── rule_engine.py  ← 规则引擎：毫秒级快速风险判断
│   │   ├── agent.py        ← AI推演核心（5段结构+预置国标+Function Calling）
│   │   ├── database.py     ← SQLite持久化（4张表+线程安全+预警审计链）
│   │   └── mqtt_client.py  ← MQTT通信处理
│   └── rag/
│       ├── build_index.py  ← 知识库构建（含扫描版PDF检测）
│       ├── retriever.py
│       └── docs/           ← 国标PDF文件
└── frontend/          ← Vue3前端
    ├── index.html
    ├── package.json
    └── src/
        ├── main.js
        ├── App.vue          ← 根组件（一键演示5阶段 + 悬浮卡片布局）
        ├── utils/
        │   ├── dataStore.js ← 全局状态（含演示进度、积水深度）
        │   └── mqttClient.js
        └── components/
            ├── AbyssScene.vue   ← 3D下凹立交城市（Three.js，当前使用）
            ├── SensorPanel.vue  ← 左侧传感器面板（半透明悬浮卡片）
            └── AIConsole.vue    ← 右侧AI推演终端（5段结构化打字机）
```

## 当前技术栈要点

### AI 模型（2026-08-22 迁移至 aiping.cn，深圳黑客松大赛）

- **当前使用**：DeepSeek-V3.1 @ `https://aiping.cn/api/v1`（OpenAI兼容接口），RAG embedding 用 Qwen3-Embedding-0.6B
- **配置化**：`.env` 中 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `EMBEDDING_MODEL`，换模型只改配置不改代码
- **备用**：通义千问 qwen-plus @ dashscope（旧 DASHSCOPE_API_KEY 仍保留在 .env）
- **知识库**：向量空间必须与建库时的 embedding 模型一致，切换 EMBEDDING_MODEL 后必须运行 `python rag/build_index.py` 重建

### 3D 引擎

- **当前使用**：Three.js v0.170 — 下凹立交桥城市数字孪生场景（`AbyssScene.vue`）
- **历史**：Cesium.js 3D地球（2026-06-26 替换）；旧组件 `CesiumGlobe.vue`/`ThreeScene.vue`、根目录原型 `abyss-sentinel.html`/`3dcity.md` 已于 2026-08-22 清理删除，`cesium`/`vite-plugin-cesium` 依赖同步移除

### MQTT 频道

| 频道                       | 方向                  | 内容         |
| -------------------------- | --------------------- | ------------ |
| `sentinel/sensor_data`   | ESP32/PC → 后端+前端 | 传感器JSON   |
| `sentinel/commands`      | 后端 → ESP32+前端    | 排水控制指令 |
| `sentinel/ai_analysis`   | 后端 → 前端          | AI推演文字   |
| `sentinel/device_status` | ESP32 → 前端         | 设备心跳     |

### 依赖版本注意事项

- **paho-mqtt**: 必须 `1.6.1`（2.0 API不兼容现有代码）
- **httpx**: 必须 `0.27.2`（0.28+ 移除 `proxies` 参数，openai 1.50 不兼容）
- **chromadb**: 最低 `0.5.23`（0.5.0 需要MSVC编译，新版有Windows预编译wheel）

### 后台运行与排障规约

- **以后台任务跑后端时**，print 日志有 stdout 块缓冲（积压不落盘），uvicorn 日志（stderr）才实时——判断后端是否收到 MQTT 消息以 `/api/stats/summary` 数据库结果为准，不要依赖 print 日志
- 需要实时日志：终端直接 `python main.py`，或加环境变量 `PYTHONUNBUFFERED=1`
- MQTT broker 用 `127.0.0.1`（.env 已固化）：本机 Docker EMQX 有 IPv4(docker backend)/IPv6(wslrelay) 两条转发通路，`localhost` 解析结果不确定
- 强杀后端进程会在 EMQX 留下半死连接（需 keepalive 超时清理），可能引起同 clientId 抢线

### 硬件已知问题

- **XY-485(HW-726) RS485模块**：MAX485芯片需要5V逻辑，ESP32 3.3V GPIO不兼容 → 自动方向检测失败
- **当前方案C（临时）**：PC USB-RS485桥接器（`pc_bridge.py`），ESP32仅负责WiFi+继电器
- **长期方案D**：MAX3485 3.3V兼容模块已订购，到货后替换

### 视觉风格

- 主色调：蓝色渐变 `#99c0fe → #4786d4`（2026-06-25 从紫粉色系改为蓝色系）
- 布局：3D 场景全屏铺底 + 左右悬浮半透明卡片
- 详细规范见 [docs/design_spec.md](docs/design_spec.md)
