<template>
  <div class="sensor-panel" :class="{ 'demo-mode': store.demo_mode }">
    <div class="panel-title">实时传感器数据</div>

    <!-- 气象传感器 -->
    <div class="section card">
      <div class="section-title">气象传感器</div>
      <div class="data-row" v-for="item in weatherItems" :key="item.key">
        <span class="data-label">{{ item.label }}</span>
        <span class="data-value" :class="{ warning: item.warning, danger: item.danger }">
          {{ item.display }}
        </span>
        <span class="data-unit">{{ item.unit }}</span>
        <span class="data-trend" v-if="item.trend">{{ item.trend }}</span>
      </div>
    </div>

    <!-- 土壤传感器 -->
    <div class="section card">
      <div class="section-title">土壤传感器</div>
      <div class="data-row" v-for="item in soilItems" :key="item.key">
        <span class="data-label">{{ item.label }}</span>
        <span class="data-value" :class="{ warning: item.warning, danger: item.danger }">
          {{ item.display }}
        </span>
        <span class="data-unit">{{ item.unit }}</span>
      </div>
    </div>

    <!-- ECharts趋势图（模拟器关闭时显示） -->
    <div class="section card chart-card" v-if="!showSimulator">
      <div class="section-title">气压与土壤湿度趋势</div>
      <div ref="chartEl" class="chart-container"></div>
    </div>

    <!-- 模拟器面板（模拟器开启时显示，替换趋势图位置） -->
    <div class="section card chart-card simulator-section" v-if="showSimulator">
      <div class="section-title">数据模拟器</div>
      <div class="sim-row" v-for="s in sliders" :key="s.key">
        <span class="sim-label">{{ s.label }}</span>
        <button class="sim-btn" @click="adjustSlider(s.key, -s.step)">−</button>
        <input type="range" :min="s.min" :max="s.max" :step="s.step"
               :value="store.sensors[s.key]"
               @input="setSensor(s.key, $event.target.value)"
               class="sim-slider" />
        <button class="sim-btn" @click="adjustSlider(s.key, s.step)">+</button>
        <input type="number" :min="s.min" :max="s.max" :step="s.step"
               :value="store.sensors[s.key]"
               @change="setSensor(s.key, $event.target.value)"
               class="sim-input" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch, nextTick } from 'vue'
import { store } from '../utils/dataStore'
import * as echarts from 'echarts'

const props = defineProps({ showSimulator: Boolean })

const chartEl = ref(null)
let chart = null

const weatherItems = computed(() => {
  const s = store.sensors
  return [
    { label: '大气压', key: 'pressure', display: s.pressure?.toFixed(1),
      unit: 'kPa', warning: s.pressure < 100, danger: s.pressure < 99,
      trend: s.pressure < 101 ? '下降中' : '稳定' },
    { label: '空气湿度', key: 'air_humidity', display: s.air_humidity?.toFixed(1),
      unit: '%', warning: s.air_humidity > 75, danger: s.air_humidity > 85 },
    { label: '风速', key: 'wind_speed', display: s.wind_speed?.toFixed(1),
      unit: 'm/s', warning: s.wind_speed > 8, danger: s.wind_speed > 10.8 },
    { label: '风向', key: 'wind_dir', display: s.wind_dir?.toFixed(0), unit: '°' },
    { label: '气温', key: 'air_temp', display: s.air_temp?.toFixed(1), unit: '℃' },
    { label: '光照', key: 'light', display: s.light?.toFixed(0), unit: 'Lux' },
    { label: '噪音', key: 'noise', display: s.noise?.toFixed(1), unit: 'dB' },
  ]
})

const soilItems = computed(() => {
  const s = store.sensors
  return [
    { label: '土壤湿度', key: 'soil_moisture', display: s.soil_moisture?.toFixed(1),
      unit: '%', warning: s.soil_moisture > 70, danger: s.soil_moisture > 85 },
    { label: '土壤温度', key: 'soil_temp', display: s.soil_temp?.toFixed(1), unit: '℃' },
    { label: '电导率', key: 'soil_ec', display: s.soil_ec?.toFixed(0), unit: 'μS/cm' },
    { label: 'pH值', key: 'soil_ph', display: s.soil_ph?.toFixed(1), unit: 'pH' },
  ]
})

const sliders = [
  { label: '气压', key: 'pressure', min: 96, max: 103, step: 0.1 },
  { label: '空气湿度', key: 'air_humidity', min: 20, max: 100, step: 1 },
  { label: '风速', key: 'wind_speed', min: 0, max: 30, step: 0.5 },
  { label: '土壤湿度', key: 'soil_moisture', min: 10, max: 100, step: 1 },
  { label: '气温', key: 'air_temp', min: 0, max: 45, step: 0.5 },
]

function setSensor(key, val) {
  store.sensors[key] = parseFloat(val)
}

function adjustSlider(key, delta) {
  const s = sliders.find(s => s.key === key)
  if (!s) return
  let val = (store.sensors[key] || 0) + delta
  val = Math.round(val / s.step) * s.step  // 对齐步长
  val = Math.max(s.min, Math.min(s.max, val))
  store.sensors[key] = parseFloat(val.toFixed(1))
}

function initChart() {
  if (!chartEl.value) return
  chart = echarts.init(chartEl.value)
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { top: 12, right: 35, bottom: 35, left: 50 },
    legend: { data: ['气压(kPa)', '土壤湿度(%)', '空气湿度(%)'],
              textStyle: { color: '#aabbcc', fontSize: 12 }, top: 0 },
    xAxis: { type: 'category', data: [],
             axisLine: { lineStyle: { color: '#445' } },
             axisLabel: { color: '#889', fontSize: 10, rotate: 45 } },
    yAxis: [
      { type: 'value', name: 'kPa', min: 96, max: 104,
        axisLine: { lineStyle: { color: '#445' } },
        axisLabel: { color: '#889', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      { type: 'value', name: '%', min: 0, max: 100,
        axisLine: { lineStyle: { color: '#445' } },
        axisLabel: { color: '#889', fontSize: 10 },
        splitLine: { show: false } }
    ],
    series: [
      { name: '气压(kPa)', type: 'line', data: [], smooth: true,
        lineStyle: { color: '#00b4d8', width: 2 },
        itemStyle: { color: '#00b4d8' }, symbol: 'none' },
      { name: '土壤湿度(%)', type: 'line', yAxisIndex: 1, data: [], smooth: true,
        lineStyle: { color: '#ff8800', width: 2 },
        itemStyle: { color: '#ff8800' }, symbol: 'none' },
      { name: '空气湿度(%)', type: 'line', yAxisIndex: 1, data: [], smooth: true,
        lineStyle: { color: '#4488cc', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#4488cc' }, symbol: 'none' }
    ]
  })
}

watch(() => store.history.length, () => {
  if (!chart) return
  const recent = store.history.slice(-60)
  const timeLabels = recent.map(h => {
    const d = new Date(h.timestamp * 1000)
    return d.getHours().toString().padStart(2,'0') + ':' +
           d.getMinutes().toString().padStart(2,'0') + ':' +
           d.getSeconds().toString().padStart(2,'0')
  })
  chart.setOption({
    xAxis: { data: timeLabels },
    series: [
      { data: recent.map(h => h.pressure) },
      { data: recent.map(h => h.soil_moisture) },
      { data: recent.map(h => h.air_humidity) }
    ]
  })
})

onMounted(() => { nextTick(() => initChart()) })

// 模拟器切换：关闭时重新初始化图表（DOM重建后chart实例已失效）
watch(() => props.showSimulator, (on) => {
  if (!on) {
    nextTick(() => {
      if (chart) { try { chart.dispose() } catch(e){} chart = null }
      initChart()
    })
  } else if (chart) {
    try { chart.dispose() } catch(e){}
    chart = null
  }
})
</script>

<style scoped>
.sensor-panel {
  height: 100%; display: flex; flex-direction: column;
  gap: 12px; overflow: visible;
}
.panel-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 15px; font-weight: 700;
  color: #ffffff;
  text-align: left;
  padding: 8px 14px;
  letter-spacing: 3px;
  flex-shrink: 0;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}

/* 独立悬浮卡片 - 半透明，可隐约透出背后城市 */
.section.card {
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.35) 0%, rgba(30, 55, 110, 0.22) 100%);
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  transition: all 0.3s;
}
.section.card:hover {
  border-color: rgba(153,192,254,0.55);
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.50) 0%, rgba(30, 55, 110, 0.35) 100%);
  box-shadow: 0 6px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.15);
}

/* 兼容旧样式（模拟器面板仍使用 .section） */
.section {
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.35) 0%, rgba(30, 55, 110, 0.22) 100%);
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px; padding: 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}
.section-title {
  color: #c8d6ec; font-size: 13px;
  margin-bottom: 10px; letter-spacing: 1px; font-weight: 600;
  display: flex; align-items: center; gap: 6px;
}
.section.card .section-title::before {
  content: ''; display: inline-block;
  width: 3px; height: 14px; border-radius: 2px;
  background: linear-gradient(180deg, #99c0fe 0%, #4786d4 100%);
}

.data-row {
  display: flex; align-items: center; gap: 10px;
  padding: 5px 0; font-size: 14px;
}
.data-label { color: #a8b8d0; min-width: 65px; }
.data-value {
  color: #e0eaf8; font-family: 'Consolas', monospace; font-weight: 600;
  min-width: 52px; text-align: right; font-size: 15px;
}
.data-value.warning { color: #ff8800; }
.data-value.danger { color: #ff3333; text-shadow: 0 0 10px rgba(255,51,51,0.5); }
.data-unit { color: #8a9bb5; font-size: 12px; min-width: 44px; }
.data-trend { color: #ff6666; font-size: 12px; font-weight: 600; }

/* 趋势图卡片：横向拉宽，延伸至面板右侧预留空间 */
.chart-card {
  flex: 1 0 auto; display: flex; flex-direction: column;
  min-height: 200px;
  margin-right: -220px;
}
.chart-container { flex: 1; min-height: 160px; width: 100%; }

/* 一键演示模式：趋势卡片高度自适应 */
.sensor-panel.demo-mode .section.card { flex-shrink: 0; }
.sensor-panel.demo-mode .chart-card {
  min-height: 260px;
}
.sensor-panel.demo-mode .chart-container { min-height: 220px; }

/* 模拟器滑块（继承chart-card的宽屏布局，但不继承高度/拉伸） */
.sensor-panel .section.card.simulator-section {
  flex: 0 0 auto;
  min-height: auto;
}
.sensor-panel.demo-mode .section.card.simulator-section {
  min-height: auto;
}
.sim-row {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 0; font-size: 13px;
}
.sim-label { color: #aabbcc; min-width: 65px; font-size: 12px; }
.sim-slider {
  flex: 1; height: 8px;
  accent-color: #4786d4;
  cursor: pointer;
}
.sim-btn {
  width: 26px; height: 26px;
  border: 1px solid rgba(153,192,254,0.25);
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: #d8e4f5;
  font-size: 16px; font-weight: bold;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.sim-btn:hover {
  background: rgba(71,134,212,0.25);
  border-color: #4786d4;
  color: #fff;
}
.sim-btn:active { background: rgba(71,134,212,0.4); }
.sim-input {
  width: 56px; height: 28px;
  border: 1px solid rgba(153,192,254,0.25);
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: #99c0fe;
  font-family: 'Consolas', monospace;
  font-size: 13px; text-align: center;
  flex-shrink: 0;
}
.sim-input:focus { outline: none; border-color: #4786d4; box-shadow: 0 0 8px rgba(71,134,212,0.25); }

/* 隐藏number输入框的上下箭头 */
.sim-input::-webkit-inner-spin-button,
.sim-input::-webkit-outer-spin-button { -webkit-appearance: none; }
</style>
