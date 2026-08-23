# 深渊哨兵：城市防汛与边坡灾害AI数字孪生预警系统

# Abyss Sentinel: Urban Flood & Slope Hazard AI Digital Twin Early Warning System

> 📌 **本文档为用户原始需求记录，保留作历史参考。最后更新：2026-06-27**
>
> 当前项目实际实现状态：
>
> - **3D 引擎**：Three.js v0.170（下凹立交桥城市数字孪生场景，见 `frontend/src/components/AbyssScene.vue`）
> - **视觉风格**：专业蓝色渐变（主色 `#99c0fe → #4786d4`），非早期"梦幻紫粉地球"风格
> - **布局**：3D 场景全屏铺底 + 左右悬浮半透明卡片
> - **已弃用**：Cesium 3D地球（`CesiumGlobe.vue`，2026-06-26 替换）
> - **硬件状态（2026-06-27）**：
>   - ESP32-S3行空板K10：WiFi+MQTT+继电器已跑通，UART1 TX=IO16 RX=IO17
>   - XY-485 RS485-TTL模块：与ESP32 3.3V GPIO不兼容（详见§3.6）
>   - 传感器验证正常（PC USB-RS485直连可读，实测数据见§3.2）
>   - MAX3485 3.3V兼容模块已订购
>   - 临时方案C：PC USB-RS485桥接器 `hardware/pc_bridge.py`
> - **MQTT模拟注入器**：`hardware/test_inject.py` — 5阶段灾害链演示
> - **最新文档**：见 [docs/](docs/) 目录与 [devlog/](devlog/) 开发日志
>
> 以下为原始需求内容，部分细节可能已与最新实现不符。

## 第一章 · 项目概述

### 1.1 我们要做什么

传统系统的逻辑：

```
水位超过警戒线 → 报警 → 人工处理
（水已经淹了才知道）
```

我们系统的逻辑：

```
气压开始下降 + 土壤开始变湿
→ AI判断：2小时后可能暴雨引发内涝
→ AI查规范：符合GB51174预警条件
→ AI主动排水
（灾害还没发生就已经处理了）
```

### 1.2 系统三句话定位

```
第一句：用工业传感器感知灾害前兆
第二句：用AI结合国家规范推演灾害链
第三句：在数字孪生大屏上提前执行预防动作
```

### 1.3 核心创新点

| 创新点   | 传统系统           | 深渊哨兵                |
| -------- | ------------------ | ----------------------- |
| 决策时机 | 水位超警戒线才报警 | 气压骤降时AI就开始推演  |
| 决策依据 | 单一阈值           | 多参数灾害链 + 国家规范 |
| 决策主体 | 人工判断           | AI自动推演并下发指令    |
| 展示方式 | 数字仪表盘         | 3D数字孪生城市          |

### 1.4演示效果

- [X] hPa要变成kPa

```
┌─────────────────────────────────────────────────────┐
│                 演示效果清单                          │
│                                                      │
│  ① 大屏左侧：实时传感器数据跳动                      │
│     气压: 998.5 hPa ↓（正在下降）                   │
│     土壤湿度: 78% ↑（正在上升）                     │
│                                                      │
│  ② 大屏中央：3D城市模型                              │
│     天空变暗 → 开始下雨（粒子效果）                  │
│     山体颜色变深（土壤吸水效果）                     │
│                                                      │
│  ③ 大屏右侧：AI推演过程（打字机效果）                │
│     "检测到气压骤降至998hPa..."                     │
│     "依据GB51174-2017第5.2条..."                    │
│     "判定内涝风险等级：HIGH"                        │
│     "正在启动预排水..."                              │
│                                                      │
│  ④ 物理反馈：继电器咔哒一声                          │
│     指示灯亮起（AI真的控制了硬件）                   │
│                                                      │
│  ⑤ 3D场景：泵站亮绿灯，水位开始下降                 │
└─────────────────────────────────────────────────────┘
```

### 1.5 一键演示功能实现说明

为防止硬件在演示时出现问题，系统提供"一键演示"按钮，完整模拟城市防汛与边坡灾害AI数字孪生预警的全流程。

- [X] 一键演示5阶段全流程联动已实现

```
┌─────────────────────────────────────────────────────────────┐
│                  一键演示 · 5阶段灾害链推演流程                │
│                                                              │
│  阶段1/5 · 正常监测（2.5秒）                                  │
│    传感器：气压101.3kPa 土壤28% 风速1.5m/s                    │
│    风险等级：NORMAL（正常）                                    │
│    AI推演：系统自检，所有数据正常                              │
│    3D场景：晴天，无积水                                       │
│                                                              │
│  阶段2/5 · 关注预警（3秒）                                    │
│    传感器渐进变化：气压→100.5kPa 土壤→52% 风速→6m/s          │
│    风险等级：WATCH（关注）                                    │
│    AI推演：气压下降预示强对流，加密监测                        │
│    3D场景：天空渐暗，开始小雨                                  │
│                                                              │
│  阶段3/5 · 警告响应（4秒）                                    │
│    传感器渐进变化：气压→99.5kPa 土壤→78% 风速→12m/s          │
│    风险等级：WARNING（警告）                                  │
│    AI推演：暴雨来临+土壤接近饱和，建议预排水                   │
│    引用国标：GB51174-2017 第5.2.1条、GB50330-2013 第5.3条     │
│    3D场景：雨势加大，路面开始积水                              │
│                                                              │
│  阶段4/5 · 紧急预警（3秒）                                    │
│    传感器渐进变化：气压→98.5kPa 土壤→92% 风速→18m/s          │
│    风险等级：CRITICAL（紧急）                                 │
│    AI推演：复合灾害高风险，立即启动应急排水                    │
│    3D场景：暴雨倾盆，路面严重积水，洪水上涨                    │
│                                                              │
│  阶段5/5 · 排水响应（11秒）                                   │
│    继电器吸合 → 泵站亮绿灯 → 排水粒子启动                     │
│    3D场景：积水逐步下降，泵站工作灯闪烁                        │
│    数据恢复：气压回升→100.8kPa，土壤回落→45%                 │
│    风险降级：CRITICAL → WATCH → NORMAL                       │
│    AI总结：灾害链被提前化解                                    │
│                                                              │
│  顶部进度条实时显示当前阶段与进度百分比                         │
│  左侧传感器数据渐变跳动（非阶跃），趋势图同步更新               │
│  右侧AI终端分段打字显示推演过程，国标条款高亮                  │
│  中间3D场景暴雨/积水/排水全联动                                │
└─────────────────────────────────────────────────────────────┘
```

**技术实现要点：**

1. **渐进式数据变化**：`gradualChange()` 函数将目标值分20步插值，模拟真实传感器渐变，驱动左侧数据面板和趋势图实时更新
2. **分段AI推演**：每个阶段独立设置 `analysis_text`，AIConsole 组件按行打字机效果显示，国标条款（GB开头）自动高亮黄色
3. **3D场景联动**：
   - 风险等级 WARNING/CRITICAL → 暴雨模式（水位上涨、雨粒子加密、洪泛面出现）
   - 继电器 `relay_on=true` → 排水泵启动（泵站绿灯、排水粒子、水位下降动画）
   - 风险等级降级 → 暴雨停止，积水自然消退
4. **历史数据记录**：演示过程中每4步调用 `pushHistory()`，左侧ECharts趋势图实时绘制气压/土壤湿度/空气湿度曲线
5. **可中断**：演示中再次点击"停止演示"立即重置为正常基线状态

## 第二章 · 系统整体架构

### 2.1 四层架构全景图

- [X] 传感器的地址还需要改，要调

```
╔══════════════════════════════════════════════════════════════════╗
║              深渊哨兵  系统架构全景                               ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐     ║
║  │          第一层：感知层（硬件）                           │    ║
║  │                                                         │     ║
║  │   [气象传感器]                     [土壤传感器]           │    ║
║  │   地址：0x03                        地址：0x02           │    ║
║  │   风速/风力/风向/噪声分贝/空气温度/  水分/温度/            │    ║
║  │   空气湿度/大气压力/光照强度         EC/PH                │    ║
║  │        │                            │                   │    ║
║  │        └──── RS485总线 ─────────────┘                   │    ║
║  │                   │                                     │    ║
║  │          [RS485转TTL模块]                               │    ║
║  │                   │                                     │    ║
║  │           [ESP32-S3主控]  ←→  [继电器]                  │    ║
║  └───────────────────┼─────────────────────────────────────┘    ║
║                      │ MQTT协议（消息传递）                       ║
║  ┌───────────────────▼─────────────────────────────────────┐    ║
║  │          第二层：消息层（EMQX消息中间件）                  │    ║
║  │                                                         │    ║
║  │   上行Topic：sentinel/v1/sensor/raw   （数据上传）        │    ║
║  │   下行Topic：sentinel/v1/commands     （指令下发）        │    ║
║  │   心跳Topic：sentinel/v1/device/status（设备状态）        │    ║
║  │   告警Topic：sentinel/v1/alerts       （风险广播）        │    ║
║  └──────────┬──────────────────────────┬────────────────── ┘    ║
║             │                          │                        ║
║  ┌──────────▼──────────┐  ┌────────────▼──────────────────┐    ║
║  │  第三层：决策层(AI)  │  │    第四层：展示层(3D大屏)      │    ║
║  │                     │  │                               │    ║
║  │  ①规则引擎（快）     │  │  ① 3D城市场景（Three.js v0.170）│    ║
║  │    硬阈值判断        │  │     - 粒子雨特效               │    ║
║  │    毫秒级响应        │  │     - 山体饱和变色             │    ║
║  │                     │  │     - 虚拟泵站动画             │    ║
║  │  ②AI推演（慢）      │  │     - 下凹立交桥城市           │    ║
║  │    查询规范知识库    │  │  ② 数据面板（ECharts）        │    ║
║  │    LLM分析推理      │  │     - 实时折线图               │    ║
║  │    下发控制指令      │  │     - 风险仪表盘              │    ║
║  │                     │  │                               │    ║
║  │  ③安全校验          │  │  ③ AI推演黑板                │    ║
║  │    指令合法性检查    │  │     - 推理过程打字机效果       │    ║
║  │    防止误操作        │  │     - 国标条款高亮显示         │    ║
║  └─────────────────────┘  └───────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════╝
```

### 2.2 数据从传感器到大屏的完整旅程

```
传感器产生数据
     │
     ▼
ESP32 用Modbus协议读取
（每5秒读一次，先读气象，再读土壤）
     │
     ▼
ESP32 检查数据是否合理
（气压不能是0，湿度不能超100%）
     │
     ▼
通过MQTT发送到云端
Topic: sentinel/v1/sensor/raw
     │
     ├─────────────────────────────────────┐
     ▼                                     ▼
AI后端收到数据                        3D大屏收到数据
     │                                     │
     ▼                                     ▼
规则引擎快速判断风险等级              场景实时更新
（正常/关注/警告/紧急）               （雨变大、山变深色）
     │
     ▼ （风险等级 >= 警告）
AI查询规范知识库
（找相关的国标条款）
     │
     ▼
AI综合分析，写出推理过程
"气压990hPa，低于标准值，
 依据GB51174-2017第5.2条..."
     │
     ▼ （决定需要排水）
通过MQTT下发指令
Topic: sentinel/v1/commands
     │
     ├─────────────────────────────────────┐
     ▼                                     ▼
ESP32收到指令                        3D大屏收到指令
继电器咔哒（物理执行）               泵站亮绿灯，水位下降动画
```

## 第三章 · 硬件层详细设计

### 3.1 硬件清单

| 编号 | 设备             | 型号                   | 数量 | 作用                       |
| ---- | ---------------- | ---------------------- | ---- | -------------------------- |
| H1   | 主控板           | ESP32-S3（行空板K10）  | 1    | 读传感器、发MQTT、控继电器 |
| H2   | 气象传感器       | RS-FSXCS-N01-3         | 1    | 检测暴雨前兆               |
| H3   | 土壤传感器       | SN-3001-TR-ECTHPH-NO1  | 1    | 检测滑坡征兆               |
| H4   | 转换模块         | RS485转TTL（自动方向） | 1    | 协议转换                   |
| H5   | 继电器           | JQC3F-05VDC-C          | 1    | AI指令物理验证             |
| H6   | 电源             | 12V适配器              | 1    | 传感器供电                 |
| H7   | USB转RS485转换器 |                        | 1    | 串口调试传感器             |

### 3.2 传感器基本信息

- 气象传感器

```
型号：RS-FSXCS-N01-3
类型：八合一气象多参数传感器
通信：RS485 Modbus RTU
地址：3（出厂默认2，已被改过）
波特率：9600
A/B线：蓝线→B端子，黄线→A端子
供电：12V
```

```
寄存器    参数        换算        实测值      单位
──────────────────────────────────────────────────
0x01F8   空气湿度    ÷10        79.3        %RH
0x01F9   气温        ÷10        24.2        ℃
0x01FA   噪音分贝    ÷10        51.7        dB
0x01FB   风速        ÷10        0.0         m/s
0x01FC   风向角度    直接读     0           度(0-360)
0x01FD   大气压强    ÷10        100.1       kPa
0x01FE   风力等级    直接读     0           级(0-17)
0x01FF   光照强度    直接读     114         Lux
```

- 土壤传感器

```
型号：SN-3001-TR-ECTHPH-N01
类型：四合一土壤传感器
通信：RS485 Modbus RTU
地址：2（出厂默认）
波特率：9600
A/B线：蓝线→B端子，黄线→A端子（与气象传感器相同）
供电：12V
测量参数：4个
```

```
寄存器    参数        换算        实测值      单位
──────────────────────────────────────────────────
0x0000   土壤湿度    ÷10        0.0         %RH（未插土）
0x0001   土壤温度    ÷10        24.1        ℃
0x0002   电导率EC    直接读     0           μS/cm（未插土）
0x0003   酸碱度PH    ÷10        6.7~9.0     pH（未插土不稳定）
```

### 3.3 接线图

```
12V电源
  ├── 红线(+12V) ──→ 气象传感器 VCC
  ├── 红线(+12V) ──→ 土壤传感器 VCC  （并联供电）
  ├── 黑线(GND)  ──→ 气象传感器 GND
  ├── 黑线(GND)  ──→ 土壤传感器 GND
  └── 黑线(GND)  ──→ ESP32 GND        ⚠️ 共地！必须连！

气象传感器（地址改为0x03）
  ├── 🟡 黄线 ──→ RS485模块 A+
  └── 🔵 蓝线 ──→ RS485模块 B-

土壤传感器（地址保持0x02）
  ├── 🟡 黄线 ──→ RS485模块 A+  （并联在同一根线上）
  └── 🔵 蓝线 ──→ RS485模块 B-  （并联在同一根线上）

RS485转TTL模块
  ├── VCC ──→ ESP32  5V
  ├── GND ──→ ESP32  GND
  ├── TXD ──→ ESP32  RX引脚（IO16）
  └── RXD ──→ ESP32  TX引脚（IO17）  注意交叉！

继电器模块
  ├── VCC ──→ ESP32  5V
  ├── GND ──→ ESP32  GND
  └── IN  ──→ ESP32  IO15
```

### 3.4 UART引脚

```
  UART4  GND接电源负极
  UART15 IO15接继电器IN 5V接继电器VCC GND接继电器GND
  UART16 IO16接TTL的RXD 5V接TTL的VCC  GND接TTLGND
  UART17 IO17接TTL的TXD
```

### 3.5传感器数据字段

```
气象传感器读取的数据：
  wind_speed    风速      单位：m/s
  wind_power    风力      等级：无风、软风、轻风、微风、和风、轻和风、轻劲风、疾风、大风、烈风、狂风、暴风、飓风
  wind_dir      风向      单位：度(0-360)【风向单位和风向角度】
  air_temp      气温      单位：℃
  air_humidity  空气湿度  单位：%RH
  pressure      大气压    单位：KPa  ← 最重要，暴雨前会骤降
  light         光照      单位：Lux
  noise         噪音      单位：dB

土壤传感器读取的数据：
  soil_moisture 土壤湿度  单位：%RH    ← 最重要，滑坡前会飙升
  soil_temp     土壤温度  单位：℃
  soil_ec       电导率    单位：μS/cm
  soil_ph       酸碱度    单位：pH值
```

```
风力等级和风速的对应关系
风力等级    风速范围(m/s)    描述
  0级       0.0 ~ 0.2      无风
  1级       0.3 ~ 1.5      软风
  2级       1.6 ~ 3.3      轻风
  3级       3.4 ~ 5.4      微风
  4级       5.5 ~ 7.9      和风
  5级       8.0 ~ 10.7     轻和风（也叫清劲风）
  6级       10.8 ~ 13.8    轻劲风（也叫强风）
  7级       13.9 ~ 17.1    疾风（也叫劲风）
  8级       17.2 ~ 20.7    大风（也叫烈风）
  9级       20.8 ~ 24.4    烈风（也叫狂风）
  10级      24.5 ~ 28.4    狂风（也叫暴风）
  11级      28.5 ~ 32.6    暴风（也叫狂暴风）
  12级      32.7以上        飓风
```

### 3.6 已知硬件问题：XY-485 模块与ESP32 3.3V不兼容

- [X] 尝试TX内部上拉，无效

**根因**：XY-485(HW-726)模块使用MAX485芯片，TTL逻辑高电平阈值 `VIH ≈ 0.7×VCC = 3.5V`（5V供电）。ESP32 GPIO输出3.3V，低于阈值。自动方向检测电路无法识别TX的HIGH/LOW跳变 → 模块卡在"发送模式" → 传感器响应被丢弃。

**当前方案C（临时）**：PC USB-RS485转换器直连传感器，`hardware/pc_bridge.py` 读取后通过MQTT桥接。ESP32仅负责WiFi+MQTT+继电器控制（`hardware/esp32_relay.py`）。

**长期方案D**：MAX3485 3.3V兼容RS485模块已订购，到货后替换XY-485，恢复ESP32直连传感器。

## 第四章 · 边缘计算层详细设计

### 4.1 ESP32程序结构

```
hardware/
├── scanner.py       调试用：扫描传感器地址
├── change_addr.py   调试用：修改传感器地址
├── config.py        配置文件
├── modbus_utils.py  工具函数（CRC计算等）
└── main.py          主程序
```

### 4.2 主程序工作流程

```
ESP32上电启动
      │
      ▼
初始化UART（RS485通信）
初始化GPIO15（继电器）
      │
      ▼
连接WiFi（失败则10秒后重试）
      │
      ▼
连接MQTT服务器
订阅指令Topic
      │
      ▼
┌─── 主循环（每5秒一次）───────────────────┐
│                                         │
│  1. 读气象传感器（地址0x03）             │
│     等200ms                             │
│  2. 读土壤传感器（地址0x02）             │
│                                         │
│  3. 检查数据合理性                       │
│     （气压800-1100，湿度0-100）          │
│                                         │
│  4. 打包JSON发送MQTT                    │
│     Topic: sentinel/v1/sensor/raw       │
│                                         │
│  5. 检查有没有收到AI指令                 │
│     有pump_on指令 → 继电器吸合          │
│                                         │
│  6. 每30秒发一次心跳                    │
│     Topic: sentinel/v1/device/status    │
└─────────────────────────────────────────┘
```

### 4.3MQTT是什么

```
MQTT就像一个消息群：

ESP32（传感器数据）  ──发消息到──►  sentinel/sensor_data 频道
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                         AI后端订阅              前端大屏订阅
                        （接收并分析）           （接收并显示）

AI后端（排水指令）    ──发消息到──►  sentinel/commands 频道
                                          │
                                          ▼
                                     ESP32订阅
                                    （接收并执行）
```

### 4.4消息频道规划

| 频道名称               | 谁发   | 谁收         | 内容           |
| ---------------------- | ------ | ------------ | -------------- |
| sentinel/sensor_data   | ESP32  | AI后端、前端 | 传感器数据     |
| sentinel/commands      | AI后端 | ESP32、前端  | 控制指令       |
| sentinel/ai_analysis   | AI后端 | 前端         | AI推演过程文字 |
| sentinel/device_status | ESP32  | 前端         | 设备心跳状态   |

### 4.5 消息格式（JSON）

传感器数据（ESP32上报）：

```json
{
  "device_id": "sentinel_001",
  "timestamp": 1698765432,
  "weather": {
    "wind_speed": 15.2,
    "wind_power": "7级-疾风",
    "wind_dir": 180,
    "air_temp": 25.3,
    "air_humidity": 88.0,
    "pressure": 99.0,
    "light": 120,
    "noise": 65.2
  },
  "soil": {
    "soil_moisture": 85.5,
    "soil_temp": 22.1,
    "soil_ec": 150,
    "soil_ph": 6.5
  },
  "data_quality": "GOOD"
}
```

AI控制指令（后端下发）：

```json
{
  "action": "pump_on",
  "duration": 60,
  "reason": "依据GB51174-2017第5.2.1条，气压990hPa且土壤湿度85%，判定内涝风险为HIGH",
  "risk_level": "HIGH",
  "timestamp": 1698765432
}
```

AI推演内容（后端推送给前端）：

```json
{
  "type": "analysis",
  "content": "检测到气压骤降至990.5hPa，较正常值下降22.5hPa...",
  "risk_level": "HIGH",
  "regulation_cited": "GB51174-2017 第5.2.1条",
  "timestamp": 1698765432
}
```

## 第五章 · AI决策层详细设计

### 5.1 技术选型说明

| 技术       | 选择              | 为什么选这个                         |
| ---------- | ----------------- | ------------------------------------ |
| 编程语言   | Python 3.10       | AI库支持最好                         |
| Web框架    | FastAPI           | 快，支持异步，适合实时数据处理       |
| AI模型     | 通义千问Qwen-Plus | 国内直连不翻墙，演示稳定，有免费额度 |
| 向量数据库 | ChromaDB          | 轻量级，本地运行，无需额外服务器     |
| MQTT库     | paho-mqtt         | Python标准MQTT库                     |

### 5.2 AI决策流程

```
收到传感器数据
      │
      ▼
┌─────────────────┐
│   规则引擎       │  ← 快速判断，不调用AI
│   （毫秒级）     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  正常       异常
    │         │
    ▼         ▼
 继续监控   触发AI推演
              │
              ▼
    ┌─────────────────┐
    │  RAG检索规范     │  ← 在PDF规范里找相关条款
    │  （查国标文件）  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  AI分析推演      │  ← 通义千问分析数据+规范
    │  （生成报告）    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  判断是否排水    │
    └────────┬────────┘
             │
        ┌────┴────┐
        │         │
      不排水     排水
        │         │
        ▼         ▼
    发推演报告  发排水指令+推演报告
    给前端显示   给ESP32+前端
```

### 5.3 规则引擎判断标准

- [X] hPa要变成kPa

```
以下任意条件触发AI推演：

内涝风险指标：
  气压 < 1000 hPa           → 可能有强降雨
  气压 < 990  hPa           → 高风险，立即分析
  空气湿度 > 85%            → 配合气压判断

边坡滑坡指标：
  土壤湿度 > 75%            → 接近饱和，需关注
  土壤湿度 > 85%            → 高度危险

复合灾害指标（最危险）：
  气压 < 995 且 土壤湿度 > 80%  → 暴雨+饱和土壤，立即排水
```

```
内涝风险指标：
┌────────────────────────────────────────────────────┐
│ 指标        │ 阈值        │ 依据来源               │
├────────────────────────────────────────────────────┤
│ 气压        │ < 1000 hPa  │ 气象学强降雨特征       │
│ 气压        │ < 990 hPa   │ 强对流天气气压特征     │
│ 空气湿度    │ > 85%       │ 气象观测经验           │
│ 风速        │ > 10.8 m/s  │ 6级以上风，强对流特征  │
└────────────────────────────────────────────────────┘
依据文件：GB51174-2017《城镇内涝防治技术规范》第4章
          中国气象局暴雨预警标准

边坡滑坡指标：
┌────────────────────────────────────────────────────┐
│ 指标        │ 阈值        │ 依据来源               │
├────────────────────────────────────────────────────┤
│ 土壤湿度    │ > 75%       │ 边坡稳定性分析经验值   │
│ 土壤湿度    │ > 85%       │ 接近土壤饱和含水率     │
│ 土壤EC值   │ 突变 > 50%  │ 孔隙水压力变化特征     │
└────────────────────────────────────────────────────┘
依据文件：GB50330-2013《建筑边坡工程技术规范》第5章

复合灾害指标：
┌────────────────────────────────────────────────────┐
│ 条件组合                    │ 说明                  │
├────────────────────────────────────────────────────┤
│ 气压<995 且 土壤湿度>80%    │ 工程判断，两项独立    │
│                             │ 风险叠加，非单一规定  │
└────────────────────────────────────────────────────┘
```

### 5.4 AI Prompt设计

```
系统角色设定：
你是城市防灾AI助手，专注于内涝和边坡灾害预警。
你必须：
1. 基于传感器数据进行灾害链推演
2. 每个判断必须引用具体国标条款
3. 风险高时调用排水工具
4. 推演过程要清晰，分步骤说明

输入给AI的信息：
- 当前传感器数据（实时）
- 相关国标条款（从PDF检索的）
- 规则引擎初步判断结果

AI输出的格式：
1. 数据解读（各传感器数值说明什么）
2. 灾害链推演（暴雨→土壤饱和→滑坡→内涝）
3. 国标依据（引用具体条款）
4. 风险等级（NORMAL/WATCH/WARNING/CRITICAL）
5. 决策（是否触发排水）
```

### 5.5 后端文件结构

```
backend/
├── main.py              # 程序入口，启动FastAPI和MQTT
├── .env                 # API密钥（不要上传Git）
├── requirements.txt     # 依赖列表
│
├── core/
│   ├── mqtt_client.py   # MQTT连接、收发消息
│   ├── rule_engine.py   # 规则引擎（快速判断）
│   └── agent.py         # AI推演核心逻辑
│
└── rag/
    ├── docs/            # PDF文件放这里
    │   ├── 城镇内涝防治技术规范.pdf
    │   └── 建筑边坡工程技术规范.pdf
    ├── build_index.py   # 处理PDF，只运行一次
    ├── retriever.py     # 检索规范内容
    └── db/              # 向量数据库（自动生成）
```

### 5.6 核心代码

main.py

```python
# backend/main.py
"""
深渊哨兵 AI后端
启动方式：python main.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.mqtt_client import MQTTHandler
from core.agent import SentinelAgent
from core.rule_engine import RuleEngine
from rag.retriever import KnowledgeBase

load_dotenv()

app = FastAPI(title="深渊哨兵 AI后端")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
mqtt_handler = None
agent = None

@app.on_event("startup")
async def startup():
    """服务启动时初始化所有组件"""
    global mqtt_handler, agent
  
    print("正在启动深渊哨兵后端...")
  
    # 初始化知识库
    kb = KnowledgeBase(db_path="rag/db")
    print("✅ 知识库加载完成")
  
    # 初始化AI Agent
    agent = SentinelAgent(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        knowledge_base=kb
    )
    print("✅ AI Agent初始化完成")
  
    # 初始化MQTT
    mqtt_handler = MQTTHandler(
        broker=os.getenv("MQTT_BROKER", "localhost"),
        port=int(os.getenv("MQTT_PORT", 1883)),
        agent=agent
    )
    mqtt_handler.start()
    print("✅ MQTT连接完成")
  
    print("🚀 深渊哨兵后端启动成功！")

@app.get("/health")
def health_check():
    """健康检查接口，确认后端在线"""
    return {"status": "online", "service": "深渊哨兵"}

@app.get("/latest")
def get_latest_data():
    """获取最新传感器数据，供前端查询"""
    if mqtt_handler:
        return mqtt_handler.latest_data
    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

core/rule_engine.py

```python
# backend/main.py
"""
深渊哨兵 AI后端
启动方式：python main.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.mqtt_client import MQTTHandler
from core.agent import SentinelAgent
from core.rule_engine import RuleEngine
from rag.retriever import KnowledgeBase

load_dotenv()

app = FastAPI(title="深渊哨兵 AI后端")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
mqtt_handler = None
agent = None

@app.on_event("startup")
async def startup():
    """服务启动时初始化所有组件"""
    global mqtt_handler, agent
  
    print("正在启动深渊哨兵后端...")
  
    # 初始化知识库
    kb = KnowledgeBase(db_path="rag/db")
    print("✅ 知识库加载完成")
  
    # 初始化AI Agent
    agent = SentinelAgent(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        knowledge_base=kb
    )
    print("✅ AI Agent初始化完成")
  
    # 初始化MQTT
    mqtt_handler = MQTTHandler(
        broker=os.getenv("MQTT_BROKER", "localhost"),
        port=int(os.getenv("MQTT_PORT", 1883)),
        agent=agent
    )
    mqtt_handler.start()
    print("✅ MQTT连接完成")
  
    print("🚀 深渊哨兵后端启动成功！")

@app.get("/health")
def health_check():
    """健康检查接口，确认后端在线"""
    return {"status": "online", "service": "深渊哨兵"}

@app.get("/latest")
def get_latest_data():
    """获取最新传感器数据，供前端查询"""
    if mqtt_handler:
        return mqtt_handler.latest_data
    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

core/agent.py

```python
# backend/core/agent.py
"""
AI推演核心
负责：调用通义千问 + 查规范 + 决定是否排水
"""

import json
import time
import asyncio
from openai import OpenAI


class SentinelAgent:
  
    def __init__(self, api_key: str, knowledge_base):
        # 通义千问使用OpenAI兼容接口
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.kb = knowledge_base
        self.rule_engine = None  # 由外部注入
  
        # 防止AI太频繁触发（演示时两次指令最少间隔60秒）
        self._last_pump_time = 0
        self._pump_cooldown = 60
  
        # AI可以调用的工具（Function Calling）
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "activate_pump",
                    "description": "启动虚拟泵站进行预排水，同时触发物理继电器",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration": {
                                "type": "integer",
                                "description": "排水持续时间，单位秒，范围30到180"
                            },
                            "reason": {
                                "type": "string", 
                                "description": "排水原因，必须引用国标条款"
                            }
                        },
                        "required": ["duration", "reason"]
                    }
                }
            }
        ]
  
    async def analyze(self, sensor_data: dict, rule_result: dict) -> dict:
        """
        AI推演主函数
        输入：传感器数据 + 规则引擎结果
        输出：分析报告 + 执行动作
        """
  
        # 第一步：从知识库检索相关规范
        query = self._build_query(sensor_data, rule_result)
        regulations = self.kb.search(query, top_k=3)
        reg_text = self._format_regulations(regulations)
  
        # 第二步：构建发给AI的问题
        prompt = self._build_prompt(sensor_data, rule_result, reg_text)
  
        # 第三步：调用通义千问
        try:
            response = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {
                        "role": "system",
                        "content": self._system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                tools=self.tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1500,
                timeout=25  # 25秒超时
            )
        except Exception as e:
            print(f"AI调用失败: {e}")
            return self._fallback_response(rule_result)
  
        # 第四步：处理AI回复
        choice = response.choices[0]
        analysis_text = choice.message.content or ""
        action = None
  
        # 检查AI是否决定排水
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                if tool_call.function.name == "activate_pump":
                    args = json.loads(tool_call.function.arguments)
                    action = await self._execute_pump(args)
  
        return {
            "analysis": analysis_text,
            "risk_level": rule_result["level"],
            "regulations_cited": [r["source"] for r in regulations],
            "action": action,
            "timestamp": int(time.time())
        }
  
    async def _execute_pump(self, args: dict) -> dict:
        """执行排水指令（带冷却检查）"""
        current_time = time.time()
  
        # 检查冷却时间
        if current_time - self._last_pump_time < self._pump_cooldown:
            remaining = self._pump_cooldown - (current_time - self._last_pump_time)
            return {
                "status": "COOLDOWN",
                "message": f"距离上次排水还需等待{remaining:.0f}秒"
            }
  
        # 验证参数
        duration = max(30, min(180, args.get("duration", 60)))
        reason = args.get("reason", "")
  
        self._last_pump_time = current_time
  
        return {
            "status": "EXECUTED",
            "action": "pump_on",
            "duration": duration,
            "reason": reason
        }
  
    def _system_prompt(self) -> str:
        return """你是深渊哨兵防灾AI，专职分析城市内涝和边坡灾害风险。

工作规则：
1. 基于传感器数据进行灾害链推演（暴雨→土壤饱和→滑坡→内涝）
2. 每个判断必须引用具体国标条款（如"依据GB51174-2017第X.X条"）
3. 分析结果分步骤清晰展示
4. 只有风险等级为WARNING或CRITICAL时才调用排水工具

输出格式：
【数据解读】说明各传感器数值的含义
【灾害链推演】逐步推演可能的灾害发展
【国标依据】引用相关规范条款
【风险评级】NORMAL/WATCH/WARNING/CRITICAL
【决策说明】是否排水及原因"""
  
    def _build_prompt(self, sensor_data: dict, 
                      rule_result: dict, reg_text: str) -> str:
        weather = sensor_data.get("weather", {})
        soil = sensor_data.get("soil", {})
  
        return f"""
## 实时传感器数据

气象数据：
- 大气压：{weather.get('pressure', 'N/A')} hPa
- 空气湿度：{weather.get('air_humidity', 'N/A')} %
- 风速：{weather.get('wind_speed', 'N/A')} m/s
- 气温：{weather.get('air_temp', 'N/A')} ℃

土壤数据：
- 土壤湿度：{soil.get('soil_moisture', 'N/A')} %
- 土壤温度：{soil.get('soil_temp', 'N/A')} ℃
- 电导率：{soil.get('soil_ec', 'N/A')} μS/cm

## 规则引擎初步判断
风险等级：{rule_result['level']}
触发原因：{'; '.join(rule_result['reasons'])}

## 相关国标条款
{reg_text}

## 请进行灾害链推演分析
"""
  
    def _build_query(self, sensor_data: dict, rule_result: dict) -> str:
        """构建RAG检索关键词"""
        keywords = []
        pressure = sensor_data.get("weather", {}).get("pressure", 1013)
        soil_moisture = sensor_data.get("soil", {}).get("soil_moisture", 0)
  
        if pressure < 1000:
            keywords.extend(["暴雨预警", "强降雨", "内涝防治"])
        if soil_moisture > 75:
            keywords.extend(["土壤饱和", "边坡稳定", "滑坡风险"])
        if rule_result["level"] == "CRITICAL":
            keywords.extend(["应急排涝", "预警响应"])
  
        return " ".join(keywords) if keywords else "城市内涝防治"
  
    def _format_regulations(self, regulations: list) -> str:
        """格式化检索到的规范内容"""
        if not regulations:
            return "未检索到相关条款"
  
        result = []
        for reg in regulations:
            result.append(
                f"【{reg.get('source', '国标')}】\n{reg.get('content', '')}"
            )
        return "\n\n".join(result)
  
    def _fallback_response(self, rule_result: dict) -> dict:
        """AI调用失败时的兜底响应"""
        return {
            "analysis": f"AI服务暂时不可用，规则引擎判断：{rule_result['level']}\n触发规则：{'; '.join(rule_result['reasons'])}",
            "risk_level": rule_result["level"],
            "regulations_cited": [],
            "action": None,
            "timestamp": int(time.time()),
            "fallback": True
        }
```

core/mqtt_client.py

```python
# backend/core/mqtt_client.py
"""
MQTT通信处理
负责：接收传感器数据、发送AI分析结果、发送控制指令
"""

import json
import time
import asyncio
import threading
import paho.mqtt.client as mqtt

from core.rule_engine import RuleEngine
from core.agent import SentinelAgent


class MQTTHandler:
  
    # MQTT频道名称
    TOPIC_SENSOR = "sentinel/sensor_data"      # 收：传感器数据
    TOPIC_COMMANDS = "sentinel/commands"        # 发：控制指令
    TOPIC_ANALYSIS = "sentinel/ai_analysis"    # 发：AI推演内容
    TOPIC_STATUS = "sentinel/device_status"    # 收：设备心跳
  
    def __init__(self, broker: str, port: int, agent: SentinelAgent):
        self.broker = broker
        self.port = port
        self.agent = agent
        self.rule_engine = RuleEngine()
  
        self.client = mqtt.Client(client_id="sentinel_backend")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
  
        self.latest_data = {}      # 最新传感器数据
        self._analyzing = False    # 防止AI并发调用
  
        # 异步事件循环
        self._loop = asyncio.new_event_loop()
  
    def start(self):
        """启动MQTT连接（在后台线程运行）"""
        self.client.connect(self.broker, self.port, keepalive=60)
  
        # 在新线程中运行MQTT循环
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
  
        # 在新线程中运行异步事件循环
        loop_thread = threading.Thread(
            target=self._loop.run_forever, 
            daemon=True
        )
        loop_thread.start()
  
    def _run_loop(self):
        """MQTT消息循环"""
        self.client.loop_forever()
  
    def _on_connect(self, client, userdata, flags, rc):
        """连接成功后订阅频道"""
        if rc == 0:
            print(f"MQTT已连接到 {self.broker}")
            client.subscribe(self.TOPIC_SENSOR)
            client.subscribe(self.TOPIC_STATUS)
        else:
            print(f"MQTT连接失败，错误码: {rc}")
  
    def _on_message(self, client, userdata, msg):
        """收到消息时的处理"""
        topic = msg.topic
  
        try:
            data = json.loads(msg.payload.decode())
        except Exception as e:
            print(f"消息解析失败: {e}")
            return
  
        if topic == self.TOPIC_SENSOR:
            self._handle_sensor_data(data)
        elif topic == self.TOPIC_STATUS:
            self._handle_device_status(data)
  
    def _handle_sensor_data(self, data: dict):
        """处理传感器数据"""
        self.latest_data = data
  
        # 过滤质量差的数据
        if data.get("data_quality") == "SUSPECT":
            print("数据质量异常，跳过AI分析")
            return
  
        # 规则引擎快速判断
        rule_result = self.rule_engine.evaluate(data)
        print(f"规则引擎: {rule_result['level']} - {rule_result['reasons']}")
  
        # 需要AI分析且当前没有正在分析的任务
        if rule_result["need_ai"] and not self._analyzing:
            asyncio.run_coroutine_threadsafe(
                self._run_ai_analysis(data, rule_result),
                self._loop
            )
  
    def _handle_device_status(self, data: dict):
        """处理设备心跳，更新设备状态"""
        self.latest_data["device_online"] = True
        self.latest_data["relay_state"] = data.get("relay_state", 0)
  
    async def _run_ai_analysis(self, data: dict, rule_result: dict):
        """运行AI分析（异步）"""
        if self._analyzing:
            return
  
        self._analyzing = True
        print("开始AI推演...")
  
        try:
            result = await self.agent.analyze(data, rule_result)
  
            # 发送AI分析内容给前端显示
            self._publish(self.TOPIC_ANALYSIS, {
                "analysis": result["analysis"],
                "risk_level": result["risk_level"],
                "regulations_cited": result["regulations_cited"],
                "timestamp": result["timestamp"]
            })
  
            # 如果AI决定排水，发送控制指令
            action = result.get("action")
            if action and action.get("status") == "EXECUTED":
                command = {
                    "action": "pump_on",
                    "duration": action["duration"],
                    "reason": action["reason"],
                    "risk_level": result["risk_level"],
                    "timestamp": int(time.time())
                }
                self._publish(self.TOPIC_COMMANDS, command)
                print(f"已发送排水指令: {command}")
  
        except Exception as e:
            print(f"AI推演出错: {e}")
  
        finally:
            self._analyzing = False
  
    def _publish(self, topic: str, data: dict):
        """发布MQTT消息"""
        payload = json.dumps(data, ensure_ascii=False)
        self.client.publish(topic, payload, qos=1)
```

rag/retriever.py

```python
# backend/rag/retriever.py
"""
知识库检索
负责：在规范PDF中找到相关条款
"""

import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings


class KnowledgeBase:
  
    def __init__(self, db_path: str):
        """加载已构建的向量数据库"""
  
        if not os.path.exists(db_path):
            print(f"⚠️ 知识库不存在：{db_path}")
            print("请先运行 rag/build_index.py 构建知识库")
            self.vectorstore = None
            return
  
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
  
        self.vectorstore = Chroma(
            persist_directory=db_path,
            embedding_function=embeddings
        )
        print(f"✅ 知识库加载成功")
  
    def search(self, query: str, top_k: int = 3) -> list:
        """
        检索最相关的规范条款
        输入：查询关键词
        输出：相关条款列表
        """
        if not self.vectorstore:
            return []
  
        try:
            docs = self.vectorstore.similarity_search(query, k=top_k)
  
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "国家规范"),
                    "page": doc.metadata.get("page", 0)
                })
  
            return results
  
        except Exception as e:
            print(f"知识库检索失败: {e}")
            return []
```

.env文件

```bash
# backend/.env
# 注意：这个文件不要上传到GitHub！

# 通义千问API Key
# 获取地址：https://dashscope.aliyun.com/
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# MQTT配置
# 本地运行EMQX时填 localhost
MQTT_BROKER=localhost
MQTT_PORT=1883
```

requirements.txt

```txt
fastapi==0.111.0
uvicorn==0.29.0
paho-mqtt==2.0.0
openai==1.35.0
langchain==0.2.5
langchain-community==0.2.5
chromadb==0.5.0
PyMuPDF==1.24.0
dashscope==1.19.0
python-dotenv==1.0.1
```

## 第六章：展示层（3D数字孪生前端）

### 6.1 技术选型说明

| 技术     | 用途         | 为什么选                     |
| -------- | ------------ | ---------------------------- |
| Vue3     | 前端框架     | 组件化，数据驱动，主流       |
| Three.js | 3D渲染       | 浏览器运行，无需安装，效果好 |
| ECharts  | 数据图表     | 折线图、仪表盘，好看好用     |
| MQTT.js  | 接收实时数据 | 浏览器里连MQTT的标准库       |

## 6.2 大屏布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    深渊哨兵  城市防汛预警系统                      │
├──────────────┬──────────────────────────┬───────────────────────┤
│              │                          │                       │
│   传感器面板  │     3D城市场景            │   AI推演终端          │
│              │                          │                       │
│  气压: 998hPa│   ☁️ 阴云天空            │ > 检测到气压骤降...   │
│  ↓ 正在下降  │   🌧️ 粒子雨效果          │ > 依据GB51174...      │
│              │   🏔️ 山体变深色          │ > 判定风险: HIGH      │
│  土壤: 82%   │   🏙️ 3D城市建筑          │ > 启动预排水...       │
│  ↑ 接近饱和  │   💧 水位上涨动画         │                       │
│              │   🟢 泵站亮绿灯           │ ┌─────────────────┐  │
│  风速: 12m/s │   💦 排水口水流粒子       │ │  风险等级仪表盘   │  │
│              │                          │ │  ● CRITICAL     │  │
│  [折线图]    │                          │ └─────────────────┘  │
│  气压历史趋势 │                          │                       │
│              │                          │                       │
└──────────────┴──────────────────────────┴───────────────────────┘
```

### 6.3 视觉变化规则

```
传感器数据变化 → 3D场景对应变化

气压 < 1000 hPa
  → 天空颜色变暗（从蓝变灰）
  → 开始生成雨粒子
  → 气压越低，雨粒子越密集

土壤湿度 > 70%
  → 山体材质颜色变深（吸水变暗）
  → 湿度越高，颜色越深

收到 pump_on 指令
  → 泵站指示灯变绿
  → 排水口出现向外流的水流粒子
  → 水位线缓慢下降

风险等级变化
  → 右侧仪表盘颜色变化
    NORMAL  = 绿色
    WATCH   = 黄色
    WARNING = 橙色
    CRITICAL = 红色（闪烁）
```

### 6.4 前端文件结构

```
frontend/
├── index.html
├── package.json
└── src/
    ├── main.js              # 入口
    ├── App.vue              # 根组件
    │
    ├── utils/
    │   ├── mqttClient.js    # MQTT连接工具
    │   └── dataStore.js     # 全局数据状态
    │
    └── components/
        ├── Dashboard.vue    # 大屏主布局
        ├── SensorPanel.vue  # 左侧传感器面板
        ├── ThreeScene.vue   # 中间3D场景
        └── AIConsole.vue    # 右侧AI推演终端
```

### 6.5 核心代码

utils/dataStore.js

```javascript
// src/utils/dataStore.js
// 全局数据中心
// 所有组件共享这里的数据，数据变了，界面自动更新

import { reactive, computed } from 'vue'

// 系统状态
export const store = reactive({
  
  // 传感器数据
  sensors: {
    pressure: 1013,
    air_humidity: 60,
    wind_speed: 0,
    air_temp: 25,
    soil_moisture: 30,
    soil_ph: 7.0,
    soil_ec: 100,
    timestamp: null,
    data_quality: 'UNKNOWN'
  },
  
  // 设备状态
  device: {
    online: false,
    relay_on: false,       // 继电器是否开启
    last_seen: null
  },
  
  // AI分析结果
  ai: {
    risk_level: 'NORMAL',  // NORMAL/WATCH/WARNING/CRITICAL
    analysis_text: '',     // AI推演文字
    regulations: [],       // 引用的规范
    is_analyzing: false    // 是否正在推演中
  },
  
  // 连接状态
  mqtt_connected: false
})

// ── 计算属性：根据数据自动计算3D场景参数 ──────────

// 雨的强度 (0~1)，气压越低雨越大
export const rainIntensity = computed(() => {
  const p = store.sensors.pressure
  if (p >= 1013) return 0
  if (p <= 980)  return 1
  return (1013 - p) / 33  // 线性插值
})

// 山体饱和度 (0~1)，土壤湿度越高颜色越深
export const soilSaturation = computed(() => {
  return Math.min(1, store.sensors.soil_moisture / 100)
})

// 风险等级对应的颜色
export const riskColor = computed(() => {
  const colors = {
    'NORMAL':   '#00ff88',
    'WATCH':    '#ffff00',
    'WARNING':  '#ff8800',
    'CRITICAL': '#ff0000'
  }
  return colors[store.ai.risk_level] || '#00ff88'
})

// 更新传感器数据的函数
export function updateSensors(data) {
  if (data.weather) {
    Object.assign(store.sensors, data.weather)
  }
  if (data.soil) {
    Object.assign(store.sensors, data.soil)
  }
  store.sensors.timestamp = data.timestamp
  store.sensors.data_quality = data.data_quality || 'GOOD'
}

// 更新AI分析的函数
export function updateAI(data) {
  store.ai.risk_level = data.risk_level || 'NORMAL'
  store.ai.analysis_text = data.analysis || ''
  store.ai.regulations = data.regulations_cited || []
  store.ai.is_analyzing = false
}

// 更新设备状态的函数
export function updateDevice(data) {
  store.device.online = data.status === 'online'
  store.device.relay_on = data.relay_state === 1
  store.device.last_seen = data.timestamp
}

// 处理控制指令（更新前端状态）
export function handleCommand(data) {
  if (data.action === 'pump_on') {
    store.device.relay_on = true
    // 持续时间结束后自动关闭
    setTimeout(() => {
      store.device.relay_on = false
    }, data.duration * 1000)
  }
}
```

utils/mqttClient.js

```javascript
// src/utils/mqttClient.js
// MQTT连接，接收实时数据

import mqtt from 'mqtt'
import { store, updateSensors, updateAI, updateDevice, handleCommand } from './dataStore'

const BROKER_URL = 'ws://localhost:8083/mqtt'  // EMQX WebSocket端口

let client = null

export function initMQTT() {
  
  client = mqtt.connect(BROKER_URL, {
    clientId: `dashboard_${Math.random().toString(16).substr(2, 6)}`,
    reconnectPeriod: 3000,  // 断线3秒后自动重连
  })
  
  // 连接成功
  client.on('connect', () => {
    console.log('MQTT已连接')
    store.mqtt_connected = true
  
    // 订阅需要的频道
    client.subscribe('sentinel/sensor_data')
    client.subscribe('sentinel/ai_analysis')
    client.subscribe('sentinel/commands')
    client.subscribe('sentinel/device_status')
  })
  
  // 断线
  client.on('disconnect', () => {
    store.mqtt_connected = false
  })
  
  // 收到消息
  client.on('message', (topic, payload) => {
    let data
    try {
      data = JSON.parse(payload.toString())
    } catch (e) {
      return
    }
  
    // 根据频道分发数据
    switch(topic) {
      case 'sentinel/sensor_data':
        updateSensors(data)
        break
      case 'sentinel/ai_analysis':
        updateAI(data)
        break
      case 'sentinel/device_status':
        updateDevice(data)
        break
      case 'sentinel/commands':
        handleCommand(data)
        break
    }
  })
}
```

components/ThreeScene.vue

```vue
<!-- src/components/ThreeScene.vue -->
<!-- 3D城市场景 -->

<template>
  <div ref="container" class="three-container"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as THREE from 'three'
import { rainIntensity, soilSaturation, store } from '../utils/dataStore'

const container = ref(null)

// Three.js核心对象
let scene, camera, renderer
let rainParticles, mountain, pump, waterLevel
let animationId

onMounted(() => {
  initScene()
  animate()
})

function initScene() {
  // ── 基础设置 ────────────────────────────────────
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x87ceeb)  // 初始：晴天蓝
  
  camera = new THREE.PerspectiveCamera(
    60,
    container.value.clientWidth / container.value.clientHeight,
    0.1, 1000
  )
  camera.position.set(0, 30, 60)
  camera.lookAt(0, 0, 0)
  
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.shadowMap.enabled = true
  container.value.appendChild(renderer.domElement)
  
  // ── 灯光 ────────────────────────────────────────
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  
  const sunLight = new THREE.DirectionalLight(0xffffff, 0.8)
  sunLight.position.set(50, 80, 50)
  sunLight.castShadow = true
  scene.add(sunLight)
  
  // ── 地面 ────────────────────────────────────────
  const groundGeo = new THREE.PlaneGeometry(100, 100)
  const groundMat = new THREE.MeshLambertMaterial({ color: 0x4a7c59 })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)
  
  // ── 城市建筑（简化版）────────────────────────────
  createBuildings()
  
  // ── 山体/边坡 ─────────────────────────────────
  mountain = createMountain()
  scene.add(mountain)
  
  // ── 雨粒子系统 ─────────────────────────────────
  rainParticles = createRain()
  scene.add(rainParticles)
  
  // ── 泵站 ───────────────────────────────────────
  pump = createPump()
  scene.add(pump)
  
  // ── 水位面板 ────────────────────────────────────
  waterLevel = createWaterSurface()
  scene.add(waterLevel)
}

function createBuildings() {
  // 创建几栋简单的方块建筑
  const buildingData = [
    { x: -20, z: -10, w: 6, h: 15, d: 6 },
    { x: -10, z: -15, w: 4, h: 20, d: 4 },
    { x:   5, z: -12, w: 8, h: 12, d: 8 },
    { x:  18, z: -8,  w: 5, h: 18, d: 5 },
    { x: -25, z:  5,  w: 6, h: 10, d: 6 },
  ]
  
  buildingData.forEach(b => {
    const geo = new THREE.BoxGeometry(b.w, b.h, b.d)
    const mat = new THREE.MeshLambertMaterial({ color: 0x8888aa })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.set(b.x, b.h / 2, b.z)
    mesh.castShadow = true
    scene.add(mesh)
  })
}

function createMountain() {
  // 用锥体模拟山体/边坡
  const geo = new THREE.ConeGeometry(20, 25, 8)
  const mat = new THREE.MeshLambertMaterial({ color: 0x6b8c42 })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.set(35, 12, -20)
  mesh.castShadow = true
  return mesh
}

function createRain() {
  // 粒子系统：模拟雨滴
  const count = 3000
  const geo = new THREE.BufferGeometry()
  const positions = new Float32Array(count * 3)
  
  for (let i = 0; i < count * 3; i += 3) {
    positions[i]     = (Math.random() - 0.5) * 100  // x
    positions[i + 1] = Math.random() * 80            // y (高度)
    positions[i + 2] = (Math.random() - 0.5) * 100  // z
  }
  
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  
  const mat = new THREE.PointsMaterial({
    color: 0xaaccff,
    size: 0.3,
    transparent: true,
    opacity: 0.7
  })
  
  const particles = new THREE.Points(geo, mat)
  particles.visible = false  // 初始隐藏
  return particles
}

function createPump() {
  // 泵站：红色小方块，激活变绿
  const geo = new THREE.BoxGeometry(4, 4, 4)
  const mat = new THREE.MeshLambertMaterial({ color: 0xff4444 })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.set(-30, 2, 10)
  return mesh
}

function createWaterSurface() {
  // 水位面：半透明蓝色平面
  const geo = new THREE.PlaneGeometry(60, 40)
  const mat = new THREE.MeshLambertMaterial({
    color: 0x2244aa,
    transparent: true,
    opacity: 0.5
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.rotation.x = -Math.PI / 2
  mesh.position.y = -0.5  // 初始在地面以下
  return mesh
}

// ── 动画循环 ────────────────────────────────────────
function animate() {
  animationId = requestAnimationFrame(animate)
  
  // 更新雨粒子（让雨下落）
  if (rainParticles.visible) {
    const positions = rainParticles.geometry.attributes.position.array
    for (let i = 1; i < positions.length; i += 3) {
      positions[i] -= 0.8  // 下落速度
      if (positions[i] < 0) {
        positions[i] = 80  // 超出范围就重置到顶部
      }
    }
    rainParticles.geometry.attributes.position.needsUpdate = true
  }
  
  renderer.render(scene, camera)
}

// ── 监听数据变化，更新3D场景 ────────────────────────

// 监听雨强度
watch(rainIntensity, (intensity) => {
  rainParticles.visible = intensity > 0.05
  rainParticles.material.opacity = intensity * 0.8
  
  // 天空颜色随雨强变暗
  const brightness = 1 - intensity * 0.6
  scene.background = new THREE.Color(
    0.53 * brightness,
    0.81 * brightness,
    0.92 * brightness
  )
})

// 监听土壤湿度
watch(soilSaturation, (saturation) => {
  // 山体颜色从草绿变深棕
  const r = 0.42 - saturation * 0.15
  const g = 0.55 - saturation * 0.2
  const b = 0.26 - saturation * 0.1
  mountain.material.color.setRGB(r, g, b)
})

// 监听继电器状态（泵站）
watch(() => store.device.relay_on, (isOn) => {
  if (isOn) {
    // 泵站变绿
    pump.material.color.setHex(0x00ff44)
    // 水位开始下降
    animateWaterLevel('down')
  } else {
    pump.material.color.setHex(0xff4444)
  }
})

// 监听风险等级（水位上涨）
watch(() => store.ai.risk_level, (level) => {
  if (level === 'WARNING' || level === 'CRITICAL') {
    animateWaterLevel('up')
  }
})

function animateWaterLevel(direction) {
  const target = direction === 'up' ? 1.5 : -0.5
  const step = direction === 'up' ? 0.02 : -0.02
  
  function step_fn() {
    if (direction === 'up' && waterLevel.position.y < target) {
      waterLevel.position.y += step
      requestAnimationFrame(step_fn)
    } else if (direction === 'down' && waterLevel.position.y > target) {
      waterLevel.position.y += step
      requestAnimationFrame(step_fn)
    }
  }
  step_fn()
}
</script>

<style scoped>
.three-container {
  width: 100%;
  height: 100%;
}
</style>
```

components/AIConsole.vue

```vue
<!-- src/components/AIConsole.vue -->
<!-- AI推演显示终端（黑底绿字，打字机效果） -->

<template>
  <div class="ai-console">
  
    <!-- 风险等级仪表盘 -->
    <div class="risk-panel">
      <div class="risk-label">当前风险等级</div>
      <div class="risk-value" :style="{ color: riskColor }">
        {{ store.ai.risk_level }}
      </div>
      <!-- 闪烁效果（CRITICAL时） -->
      <div v-if="store.ai.risk_level === 'CRITICAL'" 
           class="blink-indicator">
        ⚠️ 紧急预警
      </div>
    </div>
  
    <!-- 推演终端 -->
    <div class="terminal">
      <div class="terminal-header">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
        <span class="terminal-title">深渊哨兵 AI推演终端</span>
      </div>
  
      <div class="terminal-body" ref="terminalBody">
        <!-- 历史记录 -->
        <div v-for="(line, idx) in historyLines" 
             :key="idx" 
             class="terminal-line">
          <span class="prompt">></span>
          <span>{{ line }}</span>
        </div>
  
        <!-- 当前正在打字的行 -->
        <div v-if="currentTyping" class="terminal-line typing">
          <span class="prompt">></span>
          <span>{{ currentTyping }}</span>
          <span class="cursor">█</span>
        </div>
  
        <!-- 等待状态 -->
        <div v-if="store.ai.is_analyzing" class="terminal-line">
          <span class="prompt">></span>
          <span class="analyzing">AI推演中...</span>
        </div>
      </div>
    </div>
  
    <!-- 引用规范标签 -->
    <div v-if="store.ai.regulations.length > 0" class="regulations">
      <div class="reg-title">引用规范</div>
      <div v-for="reg in store.ai.regulations" 
           :key="reg" 
           class="reg-tag">
        {{ reg }}
      </div>
    </div>
  
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { store, riskColor } from '../utils/dataStore'

const terminalBody = ref(null)
const historyLines = ref([
  '系统初始化完成',
  '传感器连接正常',
  '知识库加载完成',
  '等待数据分析...'
])
const currentTyping = ref('')

// 打字机效果函数
async function typeText(text) {
  currentTyping.value = ''
  
  for (const char of text) {
    currentTyping.value += char
    await new Promise(resolve => setTimeout(resolve, 30))
    scrollToBottom()
  }
  
  // 打完后移入历史
  historyLines.value.push(currentTyping.value)
  currentTyping.value = ''
  
  // 保留最近50行
  if (historyLines.value.length > 50) {
    historyLines.value = historyLines.value.slice(-50)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight
    }
  })
}

// 监听AI分析结果，逐行打字显示
watch(() => store.ai.analysis_text, async (newText) => {
  if (!newText) return
  
  // 按换行分割，逐行显示
  const lines = newText.split('\n').filter(l => l.trim())
  for (const line of lines) {
    await typeText(line)
    await new Promise(resolve => setTimeout(resolve, 200))
  }
})
</script>

<style scoped>
.ai-console {
  background: #0a0a0a;
  height: 100%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-family: 'Courier New', monospace;
}

.risk-panel {
  text-align: center;
  padding: 12px;
  border: 1px solid #333;
  border-radius: 8px;
}

.risk-label {
  color: #888;
  font-size: 12px;
}

.risk-value {
  font-size: 28px;
  font-weight: bold;
  margin: 4px 0;
  transition: color 0.5s;
}

.blink-indicator {
  color: #ff0000;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.terminal {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #333;
  border-radius: 8px;
  overflow: hidden;
}

.terminal-header {
  background: #2a2a2a;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.dot.red    { background: #ff5f57; }
.dot.yellow { background: #febc2e; }
.dot.green  { background: #28c840; }

.terminal-title {
  color: #888;
  font-size: 12px;
  margin-left: 8px;
}

.terminal-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #0a0a0a;
}

.terminal-line {
  color: #00ff88;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 2px;
}

.prompt {
  color: #00aaff;
  margin-right: 8px;
}

.cursor {
  animation: blink 1s infinite;
}

.analyzing {
  color: #ffaa00;
}

.regulations {
  padding: 8px;
  border: 1px solid #333;
  border-radius: 8px;
}

.reg-title {
  color: #888;
  font-size: 11px;
  margin-bottom: 6px;
}

.reg-tag {
  display: inline-block;
  background: #1a2a1a;
  color: #00ff88;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  margin: 2px;
  border: 1px solid #00ff8844;
}
</style>
```

## 第七章：开发环境搭建

### 7.1 需要安装的软件

```
硬件开发：
  Thonny IDE         → 烧录ESP32代码
  驱动：CH340/CP2102  → ESP32串口驱动

后端开发：
  Python 3.10        → 必须是3.10版本
  VS Code            → 代码编辑器

前端开发：
  Node.js v18或v20   → 前端运行环境
  VS Code            → 同上

消息队列：
  EMQX              → MQTT服务器（本地安装）
```

### 7.2 EMQX安装（最简单的方式）

```bash
# Windows用户：
# 1. 去 https://www.emqx.io/downloads 下载Windows安装包
# 2. 安装后在开始菜单启动 EMQX
# 3. 浏览器打开 http://localhost:18083
#    账号：admin  密码：public
# 4. 能打开就说明安装成功了

# Mac用户（有Homebrew）：
brew install emqx
emqx start
```

### 7.3 后端环境搭建

```bash
# 1. 创建虚拟环境（隔离依赖，不影响系统Python）
cd AbyssSentinel/backend
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置API Key
# 编辑 .env 文件，填入你的通义千问API Key

# 5. 处理PDF（只需要一次）
python rag/build_index.py

# 6. 启动后端
python main.py
# 看到"深渊哨兵后端启动成功"就好了
```

### 7.4 前端环境搭建

```bash
# 1. 进入前端目录
cd AbyssSentinel/frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev

# 4. 浏览器打开 http://localhost:5173
```

## 第八章：开发任务清单

```
【阶段一】硬件调通（目标：能看到传感器数据）
[X] 运行scanner.py，确认能找到传感器
[X] 改气象传感器地址为0x03
[X] 两个传感器同时接线，都能读到数据（PC USB-RS485验证通过）
[X] 安装EMQX，ESP32能成功发MQTT消息
[X] 用EMQX Dashboard验证能收到数据
[ ] ESP32直连传感器（待MAX3485模块到货）

【阶段二】后端搭通（目标：AI能分析数据）
[X] 安装Python依赖（paho-mqtt 1.6.1, httpx 0.27.2, chromadb>=0.5.23）
[X] 获取通义千问API Key并配置
[X] 运行build_index.py，处理PDF规范文件（含扫描版fallback）
[X] 运行main.py，后端成功启动
[ ] 模拟发一条高风险数据，看AI是否输出分析（待API验证）

【阶段三】前端做好（目标：大屏好看能用）
[X] 搭Vue3+Three.js基础框架
[X] 3D城市场景能显示（AbyssScene.vue，下凹立交桥城市）
[X] 传感器数据能实时显示
[X] 雨效果、山体颜色变化正常
[X] AI推演文字能打字机效果显示（5段结构化）
[X] 泵站待机/抽水视觉区分

【阶段四】联调（目标：全链路跑通）
[X] 传感器数据→MQTT→前端显示（PC Bridge + 全链路验证通过）
[X] 传感器数据→AI分析→推演文字显示（规则引擎触发AI已实现）
[ ] AI指令→继电器动作→前端泵站状态更新（待MAX3485后ESP32端到端验证）
[X] 模拟高风险场景，演示完整流程（一键演示5阶段 + MQTT注入器）

【阶段五】演示准备
[X] 准备演示脚本（说什么话，按什么顺序）—— 一键演示内置5阶段流程
[X] 准备一个"正常状态"的基准数据 —— resetToNormal() 函数
[X] 准备一个"高风险触发"的演示场景 —— runDemo() 渐进式灾害链推演
[X] MQTT灾害链模拟注入器 —— test_inject.py 批量推送极端数据
[ ] 确认评委网络环境，EMQX能正常访问
```

## 第九章：演示脚本

```
第1步（30秒）：介绍系统
说："这是深渊哨兵，一个在灾害发生之前就预警的系统。
    传统系统等水淹了才报警，我们在暴雨来临前就开始行动。"
看：大屏显示当前传感器数据（正常状态）

第2步（30秒）：展示传感器实时性
说："这是真实的工业传感器，通过RS485总线连接到ESP32主控"
做：遮住/靠近传感器，让数据产生变化
看：大屏数据实时更新

第3步（60秒）：触发AI分析
说："现在我模拟气压骤降的场景，看AI如何响应"
做：点击顶部"一键演示"按钮（硬件故障时的备用方案，无需真实传感器也能完整展示）
看：
  - 顶部进度条显示"阶段1/5 · 正常监测" → "阶段2/5 · 关注预警"
  - 左侧传感器数据渐变跳动（气压下降、土壤湿度上升），趋势图同步绘制
  - 天空变暗，开始下雨
  - 右侧AI终端开始打字："检测到气压骤降..."
  - 引用国标条款的文字出现（黄色高亮）

第4步（30秒）：AI触发排水
说："AI判断风险等级达到CRITICAL，依据国标自动触发预排水"
看：
  - 进度条进入"阶段5/5 · 排水响应"
  - 继电器咔哒响（在场能听到，硬件在线时）
  - 3D场景泵站变绿，排水粒子出现，水位开始下降
  - 左侧传感器数据逐步恢复正常，风险等级降级

第5步（30秒）：总结
说："整个过程：传感器感知→AI推演→查规范→自动执行
    在物理灾害发生前完成了预防性干预"
看：进度条到达100%，系统恢复NORMAL状态

注：一键演示全程约24秒，无需硬件即可完整展示灾害链推演流程。
   硬件在线时，演示中的继电器指令会同步下发真实硬件。
```

## 附录：常见问题

```
Q：传感器扫描不到怎么办？
A：按顺序检查  
   1. 12V是否供电（万用表量传感器VCC脚）
   2. GND是否共地（传感器GND和ESP32 GND拧在一起没）
   3. A/B线是否接反（试试黄线接A+，蓝线接B-）
   4. 只接一个传感器（排除地址冲突）
   5. 换uart_id和引脚组合再试

Q：AI分析太慢怎么办？
A：正常，通义千问需要3-10秒
   演示时可以提前几秒开始触发
   系统有25秒超时保护，超时后规则引擎兜底

Q：前端显示不了3D场景怎么办？
A：检查浏览器是否支持WebGL
   在浏览器地址栏输入 chrome://gpu/ 确认WebGL已启用
   换用Chrome浏览器

Q：API Key用完了怎么办？
A：通义千问每月有免费额度，演示够用
   如果不够，可以降低触发频率（调高规则引擎阈值）

Q：演示时网络断了怎么办？
A：提前把EMQX和后端部署到本地电脑
   演示时用手机开热点给ESP32
   前端、后端、EMQX都在同一台电脑上运行
   不依赖外网
```

- 记住开发顺序：硬件→后端→前端→联调→演示
