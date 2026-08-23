<template>
  <div class="dashboard" :class="themeClass">
    <!-- 顶部标题栏 -->
    <header class="header">
      <div class="header-left">
        <div class="status-dot" :class="store.mqtt_connected ? 'online' : 'offline'"></div>
        <span class="header-time">{{ currentTime }}</span>
      </div>

      <div class="header-center">
        <h1 class="title-main">ABYSS SENTINEL</h1>
        <p class="title-sub">城市防汛与边坡灾害AI数字孪生预警系统</p>
      </div>

      <div class="header-right">
        <button class="header-btn" :class="{ active: showSimulator }" @click="showSimulator = !showSimulator">
          {{ showSimulator ? '关闭模拟器' : '数据模拟器' }}
        </button>
        <button class="header-btn demo" :class="{ running: store.demo_running }" @click="toggleDemo">
          {{ store.demo_running ? '停止演示' : '一键演示' }}
        </button>
      </div>
    </header>

    <!-- 主内容区：场景作为背景，卡片悬浮其上 -->
    <div class="main-content">
      <!-- 3D 城市场景作为底层背景，铺满整个区域 -->
      <div class="scene-bg">
        <AbyssScene />
      </div>

      <!-- 左侧悬浮卡片 -->
      <aside class="panel-left">
        <SensorPanel :showSimulator="showSimulator" />
      </aside>

      <!-- 右侧悬浮卡片 -->
      <aside class="panel-right">
        <AIConsole />
      </aside>

      <!-- 积水深度显示（底部，趋势图右侧） -->
      <div class="water-depth-display">
        <div class="wd-card" :class="store.water_depth_cls">
          <span class="wd-icon">💧</span>
          <div class="wd-info">
            <span class="wd-label">积水深度</span>
            <span class="wd-value" :class="store.water_depth_cls">{{ store.water_depth_text }}</span>
          </div>
        </div>
      </div>

      <!-- 演示进度指示器 -->
      <div class="demo-progress-overlay" v-if="store.demo_running">
        <div class="demo-progress-info">
          <span class="demo-progress-phase">{{ store.demo_phase }}</span>
          <span class="demo-progress-percent">{{ store.demo_progress }}%</span>
        </div>
        <div class="demo-progress-bar">
          <div class="demo-progress-fill" :style="{ width: store.demo_progress + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { store, pushHistory, resetToNormal } from './utils/dataStore'
import { connectMQTT } from './utils/mqttClient'
import SensorPanel from './components/SensorPanel.vue'
import AbyssScene from './components/AbyssScene.vue'
import AIConsole from './components/AIConsole.vue'

const showSimulator = ref(false)

const currentTime = ref('')
setInterval(() => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}, 1000)

const themeClass = computed(() => {
  return 'theme-' + store.ai.risk_level.toLowerCase()
})

function toggleDemo() {
  if (store.demo_running) {
    // 停止演示：恢复正常状态
    store.demo_running = false
    store.demo_mode = false
    store.demo_phase = ''
    store.demo_progress = 0
    store.ai.is_analyzing = false
    store.device.relay_on = false
    resetToNormal()
    pushHistory()
    return
  }
  store.demo_mode = true
  store.demo_running = true
  runDemo()
}

// ==================== 一键演示：完整灾害链推演 ====================
// 五阶段：正常 → 关注 → 警告 → 紧急 → 排水恢复
// analysis_text 动态引用当前传感器参数，确保数据与内容一致

// 根据当前传感器参数动态生成5段分析文本
function genAnalysis(riskLevel, extra) {
  const s = store.sensors
  const p = s.pressure.toFixed(1), h = s.air_humidity.toFixed(0)
  const ws = s.wind_speed.toFixed(1), sm = s.soil_moisture.toFixed(0)
  const at = s.air_temp.toFixed(1), st = s.soil_temp.toFixed(1)
  const ec = s.soil_ec.toFixed(1), ph = s.soil_ph.toFixed(1)

  const pDrop = (101.3 - s.pressure).toFixed(1)

  const templates = {
    NORMAL: `【数据解读】大气压${p}kPa处于正常范围（标准值101.3kPa），空气湿度${h}%，风速${ws}m/s，气温${at}℃。土壤湿度${sm}%，温度${st}℃，电导率${ec}μS/cm，pH${ph}。各项指标均未触及预警阈值，数据质量良好。\n\n【灾害链推演】当前各项指标正常，未检测到灾害链发展迹象。气压稳定说明短期内无强对流天气系统过境，土壤湿度远低于饱和含水率（75%），边坡抗剪强度充足，稳定性良好。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第3.0.4条，当未达到暴雨预警条件时，内涝防治系统处于日常监测状态，各排涝设施保持待命。\n\n【风险评级】NORMAL —— 所有监测指标正常，无需预警响应。\n\n【决策说明】当前风险等级为NORMAL，无需启动排水。系统持续以5秒间隔采集传感器数据，规则引擎保持毫秒级待命。`,

    WATCH: `【数据解读】大气压已降至${p}kPa，较标准值101.3kPa下降${pDrop}kPa，呈现持续下降趋势。空气湿度升至${h}%，较正常值显著偏高。风速增强至${ws}m/s，空气湿度与气压同步变化，具备暴雨前兆特征。土壤湿度${sm}%较正常值偏高，含水率开始增长。\n\n【灾害链推演】1.气压持续下降预示强对流天气正在形成，未来2-4小时可能出现强降雨。2.空气湿度上升与气压下降耦合，符合短时强降雨前兆模式。3.土壤含水率呈上升趋势，若持续降雨将向饱和状态（75%）逼近。4.需加密监测，防范降雨引发内涝与滑坡风险。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第3.0.4条，当气象条件出现暴雨前兆时，内涝防治系统应加密监测并进入预警准备状态。依据GB50330-2013《建筑边坡工程技术规范》第4.2.2条，边坡工程勘察应关注地下水位动态变化。\n\n【风险评级】WATCH —— 存在灾害发展苗头，需加密监测频次。\n\n【决策说明】当前风险等级为关注，暂不启动排水。系统已将传感器采样频次提升至最高，持续跟踪气压和土壤湿度变化趋势。若气压进一步下降至99.0kPa以下，将立即升级为WARNING。`,

    WARNING: `【数据解读】大气压骤降至${p}kPa，较标准值下降${pDrop}kPa，已低于100.0kPa的强降雨预警线。空气湿度${h}%逼近饱和状态。风速${ws}m/s已达到强风级别。土壤湿度${sm}%已超过75%的边坡关注阈值，含水率持续走高，边坡土体抗剪强度开始下降。\n\n【灾害链推演】1.强对流天气已形成，降雨强度将持续增强，预计30分钟内达到暴雨级别。2.土壤快速吸水趋于饱和，含水率将在短时间内突破85%危险线。3.边坡土体孔隙水压力增大，抗剪强度降低，滑坡风险显著上升。4.路面径流增加，下凹立交桥区域开始积水，内涝与滑坡风险正在叠加。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第5.2.1条，当预报降雨量可能超过管网排水能力时，应在降雨前启动预排水程序，提前降低管网水位、预留调蓄空间。依据GB50330-2013《建筑边坡工程技术规范》第5.3.2条，边坡稳定安全系数应根据岩土体抗剪强度参数和地下水位变化进行复核。\n\n【风险评级】WARNING —— 复合灾害风险升高，建议立即启动预排水。\n\n【决策说明】风险等级达到警告，强烈建议立即启动预排水系统。请确认排水泵站运作正常，做好应急排涝准备。同时加密边坡位移监测频率。`,

    CRITICAL: `【数据解读】大气压骤降至${p}kPa，较标准值大幅下降${pDrop}kPa，远低于100.0kPa强降雨预警线和99.0kPa强对流警戒线。空气湿度${h}%接近或达到饱和。风速${ws}m/s达到烈风级别。土壤湿度${sm}%远超85%安全阈值，土壤孔隙水压力激增，边坡抗剪强度急剧下降。\n\n【灾害链推演】1.暴雨已倾盆而下，降雨强度超过管网排水能力。2.土壤完全饱和，超静孔隙水压力快速增大，有效应力骤降，边坡失稳风险极高。3.下凹立交桥低洼处积水深度快速上涨，预计超过2.8米。4.路面积水即将超过警戒线，内涝与滑坡形成复合型灾害，必须立即采取最高级别应急措施。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第5.2.1条，当预报降雨量可能超过设计标准时，必须提前开启排涝泵站进行预抽排，不得延误。依据GB50330-2013《建筑边坡工程技术规范》第5.3.1条，边坡稳定性系数小于安全系数时为不稳定状态，必须立即采取工程治理措施。\n\n【风险评级】CRITICAL —— 复合灾害高风险，必须立即响应！\n\n【决策说明】🚨 立即启动应急排水泵！已通过MQTT下发pump_on指令至ESP32，物理继电器吸合，排水泵全力运转。建议同步启动人员疏散预案，持续监测边坡位移数据。`,

    DRAIN: `【数据解读】应急排水泵已启动运行，物理继电器吸合正常、指示灯已亮。3D数字孪生场景中泵站绿灯闪烁、排水粒子喷涌而出。路面积水深度正在从峰值${extra || '2.83'}米逐步下降，排水流量正常。边坡监测传感器持续回传数据。\n\n【灾害链推演】1.排水泵全力运转后，路面积水水位正在以可见速度下降。2.气压开始从${p}kPa底部回升，降雨强度逐步减弱。3.土壤含水率将随排水和降雨减弱而逐步回落。4.边坡土体超静孔隙水压力消散后，稳定性将逐步恢复。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第4.2.2条，内涝防治系统应具备源头减排、排水管渠、排涝除险三重功能，应在降雨前、降雨中、降雨后分别采取相应措施。当前处于降雨中排水除险阶段。\n\n【风险评级】CRITICAL → 逐步降低中 —— 排水进行中，风险正在缓解。\n\n【决策说明】排水泵持续运行中。排水完成后将进入降雨后恢复监测阶段，持续观察边坡稳定性，确认各项指标完全恢复正常后降级为NORMAL。`,

    RECOVER: `【数据解读】排水作业完成，路面积水已全部排空。气压回升至${p}kPa，较最低点时回升明显，降雨已显著减弱。空气湿度${h}%持续下降中。土壤湿度回落至${sm}%，边坡趋于稳定状态。风速${ws}m/s已大幅减弱。各项指标向正常基线回归。\n\n【灾害链推演】1.排水完成消除了内涝灾害的直接威胁。2.气压回升说明强对流天气系统已过境，气象条件趋于稳定。3.土壤含水率回落使边坡抗剪强度逐步恢复至安全水平。4.本次灾害链从"暴雨前兆"到"提前排水化解"，完整展示了深渊哨兵"预防优于响应"的核心理念。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第4.2.2条，降雨后应采取排水检查、设施检修等恢复措施，确认排水系统完好。依据GB50330-2013《建筑边坡工程技术规范》第5.3.1条，边坡稳定性系数回升至安全范围后，边坡状态恢复至稳定。\n\n【风险评级】WATCH → NORMAL —— 灾害风险已解除，进入恢复观察期。\n\n【决策说明】排水已完成，风险等级逐步降级。系统将继续监测2小时，确认各项指标完全恢复后将自动转入日常NORMAL监测模式。`,

    DONE: `【数据解读】所有指标已完全恢复正常。气压${p}kPa回到标准基线附近，空气湿度${h}%正常，风速${ws}m/s恢复微风，土壤湿度${sm}%恢复干燥状态。数据质量GOOD，所有传感器在线。\n\n【灾害链推演】本次完整的预警-响应-恢复全流程：传感器在暴雨前兆阶段捕捉到气压骤降和土壤变湿信号 → 规则引擎快速判断风险等级 → AI结合国标进行灾害链推演 → 自动触发预排水决策 → MQTT下发控制指令 → ESP32继电器物理执行 → 泵站排水化解内涝风险 → 数据逐步恢复正常。整个过程在物理灾害发生前完成了完整的预防性干预，验证了"不等灾害发生就提前行动"的系统设计理念。\n\n【国标依据】依据GB51174-2017《城镇内涝防治技术规范》第3.0.4条，系统已恢复日常监测状态，各排涝设施保持完好待命。\n\n【风险评级】NORMAL —— 所有指标正常，系统恢复日常监测。\n\n【决策说明】演示完成。深渊哨兵持续守护城市安全，系统进入日常监测状态，随时准备响应下一次灾害预警。每5秒自动采集12项传感器参数，规则引擎毫秒级待命，AI推演引擎保持在线。`
  }
  return templates[riskLevel] || ''
}

async function runDemo() {
  // ── 阶段0：重置为正常基线 ──
  resetToNormal()
  store.ai.analysis_text = ''
  store.demo_phase = '阶段1/5 · 正常监测'
  store.demo_progress = 5
  pushHistory()
  await sleep(1500)

  // ── 阶段1：正常状态展示 ──
  if (!store.demo_running) return
  store.demo_progress = 15
  store.ai.risk_level = 'NORMAL'
  store.ai.analysis_text = genAnalysis('NORMAL')
  store.ai.regulations = ['GB51174-2017 第3.0.4条']
  await sleep(2500)

  // ── 阶段2：关注 - 气压下降，土壤变湿 ──
  if (!store.demo_running) return
  store.demo_phase = '阶段2/5 · 关注预警'
  store.demo_progress = 30
  await gradualChange({ pressure: 100.5, air_humidity: 72, wind_speed: 6, soil_moisture: 52 }, 2000)
  store.ai.risk_level = 'WATCH'
  store.ai.analysis_text = genAnalysis('WATCH')
  store.ai.regulations = ['GB51174-2017 第3.0.4条', 'GB50330-2013 第4.2.2条']
  await sleep(3000)

  // ── 阶段3：警告 - 暴雨来临，土壤接近饱和 ──
  if (!store.demo_running) return
  store.demo_phase = '阶段3/5 · 警告响应'
  store.demo_progress = 50
  store.ai.is_analyzing = true
  await gradualChange({ pressure: 99.5, air_humidity: 88, wind_speed: 12, soil_moisture: 78, wind_dir: 180 }, 2500)
  store.ai.risk_level = 'WARNING'
  store.ai.is_analyzing = false
  store.ai.analysis_text = genAnalysis('WARNING')
  store.ai.regulations = ['GB51174-2017 第5.2.1条', 'GB50330-2013 第5.3.2条']
  await sleep(4000)

  // ── 阶段4：紧急 - 暴雨倾盆，土壤饱和 ──
  if (!store.demo_running) return
  store.demo_phase = '阶段4/5 · 紧急预警'
  store.demo_progress = 70
  await gradualChange({ pressure: 98.5, air_humidity: 93, wind_speed: 18, soil_moisture: 92, wind_dir: 200, noise: 68 }, 2500)
  store.ai.risk_level = 'CRITICAL'
  store.ai.analysis_text = genAnalysis('CRITICAL')
  store.ai.regulations = ['GB51174-2017 第5.2.1条', 'GB50330-2013 第5.3.1条']
  await sleep(3000)

  // ── 阶段5：排水响应 + 恢复 ──
  if (!store.demo_running) return
  store.demo_phase = '阶段5/5 · 排水响应'
  store.demo_progress = 85
  // 触发继电器 → 泵站状态变"运行中"、3D泵站闪灯+排水粒子
  store.device.relay_on = true
  store.ai.analysis_text = genAnalysis('DRAIN')
  store.ai.regulations = ['GB51174-2017 第4.2.2条']
  // 等待3D排水动画完成（约6秒可见效果），泵站保持运行中
  await sleep(6000)

  // 排水完成，数据逐步恢复（relay由3D场景在排水自然结束后自动置false）
  if (!store.demo_running) return
  store.demo_progress = 95
  await gradualChange({ pressure: 100.8, air_humidity: 70, wind_speed: 4, soil_moisture: 45 }, 3000)
  store.ai.risk_level = 'WATCH'
  store.ai.analysis_text = genAnalysis('RECOVER')
  store.ai.regulations = ['GB51174-2017 第4.2.2条', 'GB50330-2013 第5.3.1条']
  await sleep(3000)

  // 完全恢复正常
  if (!store.demo_running) return
  store.demo_progress = 100
  await gradualChange({ pressure: 101.3, air_humidity: 55, wind_speed: 1.5, soil_moisture: 28 }, 2000)
  store.ai.risk_level = 'NORMAL'
  store.ai.analysis_text = genAnalysis('DONE')
  store.ai.regulations = ['GB51174-2017 第3.0.4条']
  store.demo_phase = '演示完成'
  store.demo_running = false
  store.demo_mode = false
}

// 渐进式数据变化（模拟真实传感器渐变）
async function gradualChange(target, duration) {
  const start = { ...store.sensors }
  const keys = Object.keys(target)
  const steps = 20
  const interval = duration / steps
  for (let i = 1; i <= steps; i++) {
    if (!store.demo_running) return
    const t = i / steps
    keys.forEach(k => {
      store.sensors[k] = start[k] + (target[k] - start[k]) * t
    })
    store.sensors.timestamp = Date.now()
    if (i % 4 === 0) pushHistory()  // 每4步记录一次历史，驱动趋势图
    await sleep(interval)
  }
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms))
}

onMounted(() => {
  connectMQTT()
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

:root {
  /* 主色：线性渐变 #99c0fe → #4786d4 */
  --brand-start: #99c0fe;
  --brand-end: #4786d4;
  --brand-gradient: linear-gradient(135deg, #99c0fe 0%, #4786d4 100%);
  --sky-normal: #99c0fe;
  --sky-watch: #7ba8f0;
  --sky-warning: #5a8fdd;
  --sky-critical: #4786d4;
  --accent-normal: #4786d4;
  --accent-watch: #f0c040;
  --accent-warning: #ff8800;
  --accent-critical: #ff3333;
  --panel-bg: rgba(15, 30, 70, 0.72);
  --panel-border: rgba(153, 192, 254, 0.18);
  --text-primary: #e8eef8;
  --text-secondary: #a8b8d0;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #0a1430; color: #e8eef8;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 16px;
}

.dashboard {
  width: 100vw; height: 100vh;
  display: flex; flex-direction: column;
  transition: background 2s ease;
  overflow: hidden;
}

/* 主题（蓝色渐变主色调 + 风险动态） */
.theme-normal  { background: linear-gradient(180deg, #99c0fe 0%, #2a4a7a 100%); }
.theme-watch   { background: linear-gradient(180deg, #7ba8f0 0%, #213a66 100%); }
.theme-warning { background: linear-gradient(180deg, #5a8fdd 0%, #163055 100%); }
.theme-critical{ background: linear-gradient(180deg, #4786d4 0%, #0d1f3e 100%); }

/* 顶部标题栏 */
.header {
  height: 68px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  background: linear-gradient(90deg, rgba(15, 30, 70, 0.92) 0%, rgba(30, 55, 110, 0.88) 50%, rgba(15, 30, 70, 0.92) 100%);
  border-bottom: 1px solid rgba(153,192,254,0.25);
  flex-shrink: 0;
  z-index: 10;
  backdrop-filter: blur(10px);
}
.header-left, .header-right { display: flex; align-items: center; gap: 18px; min-width: 240px; }
.header-right { justify-content: flex-end; }
.header-center { text-align: center; }

.title-main {
  font-family: 'Orbitron', sans-serif;
  font-size: 30px; font-weight: 900;
  letter-spacing: 8px;
  color: #ffffff;
  text-shadow: 0 2px 8px rgba(10, 20, 50, 0.8), 0 0 24px rgba(71,134,212,0.45);
}
.title-sub {
  font-size: 13px; color: #c8d6ec; letter-spacing: 4px;
  margin-top: 2px; font-weight: 500;
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
}
.header-time { color: #c8d6ec; font-size: 15px; }
.status-dot { width: 12px; height: 12px; border-radius: 50%; }
.status-dot.online { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
.status-dot.offline { background: #ff4444; box-shadow: 0 0 10px #ff4444; }

.header-btn {
  padding: 8px 20px;
  border: 1px solid #4786d4;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(71,134,212,0.55) 0%, rgba(153,192,254,0.35) 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
  white-space: nowrap;
  letter-spacing: 1px;
  box-shadow: 0 2px 8px rgba(71,134,212,0.3);
}
.header-btn:hover {
  background: var(--brand-gradient);
  border-color: rgba(153,192,254,0.8);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(71,134,212,0.5);
}
.header-btn:active { transform: translateY(0); }
/* 模拟器开启态：高亮显示 */
.header-btn.active {
  background: linear-gradient(135deg, #4786d4 0%, #99c0fe 100%);
  border-color: #99c0fe;
  color: #fff;
  box-shadow: 0 0 16px rgba(71,134,212,0.55), inset 0 1px 0 rgba(255,255,255,0.25);
}
/* 演示运行中态：脉冲提示 */
.header-btn.demo.running {
  background: linear-gradient(135deg, #ff6b4a 0%, #ff8a6a 100%);
  border-color: #ff8a6a;
  color: #fff;
  animation: btn-pulse 1.4s ease-in-out infinite;
  box-shadow: 0 0 18px rgba(255,107,74,0.55);
}
@keyframes btn-pulse {
  0%, 100% { box-shadow: 0 0 14px rgba(255,107,74,0.4); }
  50%      { box-shadow: 0 0 22px rgba(255,107,74,0.8); }
}

/* 主内容区：场景作为底层，卡片悬浮其上 */
.main-content {
  flex: 1; position: relative; overflow: hidden;
}

/* Cesium 场景铺满整个主内容区，作为背景层 */
.scene-bg {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  z-index: 1;
}
.scene-bg > :first-child { width: 100%; height: 100%; }

/* 左右悬浮卡片容器 - 透明背景，让场景透出 */
.panel-left, .panel-right {
  position: absolute; top: 0; bottom: 0;
  width: 360px;
  background: transparent;
  border: none;
  display: flex; flex-direction: column;
  padding: 14px;
  gap: 12px;
  z-index: 2;
  pointer-events: none;
  overflow: hidden;
}
.panel-left { left: 0; width: 600px; padding-right: 240px; }
.panel-right { right: 0; }
.panel-left > *, .panel-right > * { pointer-events: auto; }

/* 积水深度显示（底部，趋势图右侧） */
.water-depth-display {
  position: absolute; bottom: 20px; left: 600px;
  z-index: 5; pointer-events: none;
}
.wd-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 18px;
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.55) 0%, rgba(30, 55, 110, 0.40) 100%);
  border: 1px solid rgba(255,100,0,0.35);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  transition: all 0.4s;
}
.wd-card.ok { border-color: rgba(0,204,102,0.4); }
.wd-card.warn { border-color: rgba(255,170,0,0.5); }
.wd-card.danger { border-color: rgba(255,68,68,0.6); box-shadow: 0 0 18px rgba(255,68,68,0.25); }
.wd-icon { font-size: 22px; }
.wd-info { display: flex; flex-direction: column; gap: 2px; }
.wd-label { color: #a8b8d0; font-size: 11px; letter-spacing: 2px; }
.wd-value {
  color: #ff4444; font-size: 22px; font-weight: bold;
  font-family: 'Consolas', monospace;
  text-shadow: 0 0 12px rgba(255,68,68,0.4);
  transition: color 0.4s;
}
.wd-value.warn { color: #ffaa00; text-shadow: 0 0 12px rgba(255,170,0,0.4); }
.wd-value.ok { color: #00cc66; text-shadow: 0 0 12px rgba(0,204,102,0.4); }

/* 演示进度指示器 */
.demo-progress-overlay {
  position: absolute; top: 14px; left: 50%;
  transform: translateX(-50%);
  z-index: 6; width: 420px;
  pointer-events: none;
}
.demo-progress-info {
  display: flex; justify-content: space-between;
  color: #ffaa44; font-size: 12px; letter-spacing: 1px;
  margin-bottom: 4px; text-shadow: 0 1px 4px rgba(0,0,0,0.8);
}
.demo-progress-percent { color: #fff; font-weight: bold; font-family: 'Consolas', monospace; }
.demo-progress-bar {
  width: 100%; height: 4px;
  background: rgba(0,0,0,0.5);
  border-radius: 2px; overflow: hidden;
  border: 1px solid rgba(255,170,68,0.3);
}
.demo-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ff6622, #ffaa44, #00cc66);
  border-radius: 2px;
  transition: width 0.5s ease;
  box-shadow: 0 0 10px rgba(255,170,68,0.6);
}
</style>
