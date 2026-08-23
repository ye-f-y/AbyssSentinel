# 🚀 ABYSS SENTINEL 运行手册

> 深渊哨兵 · 城市防汛与边坡灾害AI数字孪生预警系统
> 从零启动到完整演示的操作指南（含常见问题排查）

---

## 一、启动前检查（每次演示前过一遍）

| 检查项           | 方法                              | 预期                                        |
| ---------------- | --------------------------------- | ------------------------------------------- |
| EMQX 容器在跑    | 浏览器打开 http://localhost:18083 | 能看到 EMQX Dashboard 登录页                |
| 后端密钥已配置   | 打开`backend/.env`              | 有`LLM_API_KEY=QC-...`（aiping 大赛密钥） |
| 没有残留的旧进程 | 任务管理器搜`python`            | 没有旧的`main.py` 进程（有就结束掉）      |

---

## 二、三步启动

### 第 1 步：启动 EMQX（消息中间件）

如果你的 EMQX 是 Docker 方式（本机现状）：

```powershell
docker start emqx    # 容器名按实际调整，docker ps -a 可查
```

验证：浏览器打开 http://localhost:18083 能进 Dashboard 即可。

### 第 2 步：启动后端（AI 分析 + 数据库）

新开一个终端：

```powershell
cd c:\Users\ye_\Desktop\AbyssSentinel\backend
.\venv\Scripts\activate
python main.py
```

**看到以下四行才算成功**（缺一不可）：

```
✅ 持久化数据库就绪: ...\backend\data\sentinel.db
知识库加载成功，共 255 条
AI推演模型: DeepSeek-V3.1 @ https://aiping.cn/api/v1
MQTT已连接: 127.0.0.1
```

> ⚠️ 必须**在终端直接跑**，不要用后台/重定向方式运行——后台运行的日志有缓冲，
> print 输出会积压看不到，容易误判系统状态。这个终端保持开着别关。

### 第 3 步：启动前端（3D 数字孪生大屏）

再开一个终端：

```powershell
cd c:\Users\ye_\Desktop\AbyssSentinel\frontend
npm run dev
```

浏览器打开 **http://localhost:5173** —— 看到 3D 下凹立交城市 + 左右悬浮卡片即成功。

---

## 三、怎么演示

### 方式 A：真实 AI 链路（主打，约 60 秒）

再开一个终端，注入 5 阶段灾害链数据：

```powershell
cd c:\Users\ye_\Desktop\AbyssSentinel\backend
.\venv\Scripts\activate
cd ..
python hardware\test_inject.py
```

注入期间自动发生（对着大屏讲解）：

1. **阶段 1-2**：气压渐降、土壤变湿 → 大屏天空变暗、开始下雨、AI 终端开始推演
2. **阶段 3-4**：数据到 CRITICAL → 暴雨倾盆、积水上涨 → **DeepSeek-V3.1 实时推演**：
   5 段结构（数据解读→灾害链推演→国标依据→风险评级→决策说明）打字机逐字显示，
   引用 GB51174 / GB50330 真实条款
3. **阶段 5**：AI 决策启动排水 → 泵站绿灯、水位下降、风险等级逐步回落 NORMAL

### 方式 B：一键演示（保底方案，约 25 秒）

大屏顶部 **「一键演示」按钮** —— 纯前端模拟 5 阶段流程，**不依赖网络、不依赖 API、不依赖后端**。
断网/API 故障时用这个兜底。

### 加分项：展示预警审计链（评审问"AI 做过什么决策"时的硬证据）

演示完方式 A 后，浏览器打开：

| 地址                                       | 内容                                             |
| ------------------------------------------ | ------------------------------------------------ |
| http://localhost:8000/api/stats/summary    | 总记录数 / 今日预警事件 / 历史最高风险等级       |
| http://localhost:8000/api/history/events   | 风险等级变化事件链（含每次触发原因和传感器快照） |
| http://localhost:8000/api/history/analyses | AI 每次推演的全文和国标引用                      |
| http://localhost:8000/api/history/commands | AI 下发过的排水指令审计                          |

数据库实体文件在 `backend/data/sentinel.db`（SQLite）。

---

## 四、常见问题排查（实战踩坑记录）

### ❌ 后端报「MQTT连接失败(127.0.0.1:1883)」

EMQX 没启动。`docker start emqx`，确认 18083 能打开后，**重启后端**（Ctrl+C 后重新 `python main.py`）。

### ❌ 大屏数据不动 / 不联动

前端 MQTT 走的是 WebSocket，可能遇到 localhost 解析问题。打开
`frontend/src/utils/mqttClient.js`，把

```js
const BROKER_URL = 'ws://localhost:8083/mqtt'
```

改成

```js
const BROKER_URL = 'ws://127.0.0.1:8083/mqtt'
```

保存后前端会自动热更新（Vite）。

### ❌ AI 终端一直不出推演文字

1. 确认后端终端有 `AI推演模型: DeepSeek-V3.1 @ https://aiping.cn/api/v1` 这行（没有 = .env 密钥问题）
2. 确认演示电脑能访问外网（aiping.cn 是公网 API）
3. AI 推演需要 5~30 秒，注入 WARNING/CRITICAL 数据后耐心等一下
4. AI 不可用时系统会自动降级为规则引擎输出（5 段结构仍在，标注 fallback），演示不至于中断

### ❌ 想重新演示一遍（清空历史数据）

```powershell
# 停掉后端（Ctrl+C），然后：
cd c:\Users\ye_\Desktop\AbyssSentinel\backend
del data\sentinel.db
python main.py        # 重启后端，自动新建空库
```

### ❌ 后端起不来报端口占用

8000 端口被旧进程占了。任务管理器搜 `python`，结束旧的 `main.py` 进程再启动。

### ❌ EMQX 中途重启过

后端的 MQTT 连接会失效但**不会自动恢复订阅**。重启后端（Ctrl+C → `python main.py`）即可。

---

## 五、关闭顺序

1. 前端终端 `Ctrl+C`
2. 后端终端 `Ctrl+C`（正常退出会释放 MQTT 连接，不留半死连接）
3. EMQX：演示结束不用关，下次直接用

---

## 六、系统架构速查（讲解用）

```
传感器/注入器 ──MQTT──► EMQX ──► 后端(FastAPI)
                                    ├─ 规则引擎（毫秒级四色判级）
                                    ├─ RAG 国标检索（ChromaDB 255条）
                                    ├─ DeepSeek-V3.1 推演（aiping API）
                                    ├─ SQLite 审计链（4张表）
                                    └──MQTT──► ESP32继电器（硬件在线时）
                        └──────────► 前端大屏（Three.js 3D 联动）
```

| 频道                       | 方向                | 内容             |
| -------------------------- | ------------------- | ---------------- |
| `sentinel/sensor_data`   | 采集端 → 后端+前端 | 传感器 JSON      |
| `sentinel/commands`      | 后端 → ESP32+前端  | 排水控制指令     |
| `sentinel/ai_analysis`   | 后端 → 前端        | AI 推演 5 段文字 |
| `sentinel/device_status` | ESP32 → 前端       | 设备心跳         |

更多技术细节见 [docs/tech_spec.md](docs/tech_spec.md)。
