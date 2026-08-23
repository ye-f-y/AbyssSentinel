// src/utils/dataStore.js
// 全局响应式数据中心，所有组件共享
import { reactive, computed } from 'vue'

export const store = reactive({
  // 传感器数据
  sensors: {
    pressure: 101.3,       // kPa
    air_humidity: 60,
    air_temp: 25,
    wind_speed: 0,
    wind_dir: 0,
    wind_power: 0,
    light: 500,
    noise: 45,
    soil_moisture: 30,
    soil_temp: 22,
    soil_ec: 100,
    soil_ph: 7.0,
    timestamp: null,
    data_quality: 'GOOD'
  },

  // 设备状态
  device: {
    online: false,
    relay_on: false,
    last_seen: null
  },

  // AI分析
  ai: {
    risk_level: 'NORMAL',
    analysis_text: '',
    regulations: [],
    is_analyzing: false
  },

  // 连接
  mqtt_connected: false,

  // 历史数据（最近200条）
  history: [],

  // 演示模式
  demo_mode: false,
  demo_running: false,
  demo_phase: '',        // 当前演示阶段描述（供 UI 显示）
  demo_progress: 0,      // 演示进度 0~100

  // 积水深度（由3D场景更新，供底部显示）
  water_depth_text: '2.83 m',
  water_depth_cls: '',

  // 当前城市
  current_city: 'default'
})

// ---- 演示辅助函数 ----

// 记录一条历史数据点（演示时调用，驱动趋势图）
export function pushHistory() {
  store.history.push({
    timestamp: Date.now(),
    pressure: store.sensors.pressure,
    soil_moisture: store.sensors.soil_moisture,
    air_humidity: store.sensors.air_humidity
  })
  if (store.history.length > 200) store.history.shift()
}

// 重置为正常基线数据
export function resetToNormal() {
  Object.assign(store.sensors, {
    pressure: 101.3, air_humidity: 55, air_temp: 26,
    wind_speed: 1.5, wind_dir: 90, wind_power: 1,
    light: 520, noise: 45,
    soil_moisture: 28, soil_temp: 24, soil_ec: 120, soil_ph: 7.0,
    timestamp: Date.now(), data_quality: 'GOOD'
  })
  store.ai.risk_level = 'NORMAL'
  store.ai.analysis_text = ''
  store.ai.regulations = []
  store.ai.is_analyzing = false
  store.device.relay_on = false
}

// ---- 计算属性：3D场景参数 ----

// 雨强度 0~1
export const rainIntensity = computed(() => {
  const p = store.sensors.pressure
  if (p >= 101.3) return 0
  if (p <= 98.0) return 1
  return (101.3 - p) / 3.3
})

// 土壤饱和度 0~1
export const soilSaturation = computed(() => {
  return Math.min(1, store.sensors.soil_moisture / 100)
})

// 风险颜色
export const riskColor = computed(() => {
  const colors = {
    NORMAL: '#00b4d8',
    WATCH: '#f0c040',
    WARNING: '#ff8800',
    CRITICAL: '#ff3333'
  }
  return colors[store.ai.risk_level] || '#00b4d8'
})

// ---- 更新函数 ----

export function updateSensors(data) {
  if (data.weather) {
    Object.assign(store.sensors, data.weather)
  }
  if (data.soil) {
    Object.assign(store.sensors, data.soil)
  }
  store.sensors.timestamp = data.timestamp || Date.now()
  store.sensors.data_quality = data.data_quality || 'GOOD'

  // 记录历史
  store.history.push({
    timestamp: store.sensors.timestamp,
    pressure: store.sensors.pressure,
    soil_moisture: store.sensors.soil_moisture,
    air_humidity: store.sensors.air_humidity
  })
  if (store.history.length > 200) {
    store.history.shift()
  }
}

export function updateAI(data) {
  store.ai.risk_level = data.risk_level || 'NORMAL'
  store.ai.analysis_text = data.content || data.analysis || ''
  store.ai.regulations = data.regulation_cited || data.regulations_cited || []
  store.ai.is_analyzing = false
}

export function updateDevice(data) {
  store.device.online = data.status === 'online' || data.online === true
  store.device.relay_on = data.relay_state === 1
  store.device.last_seen = data.timestamp
}

export function handleCommand(data) {
  if (data.action === 'pump_on') {
    store.device.relay_on = true
    setTimeout(() => {
      store.device.relay_on = false
    }, (data.duration || 60) * 1000)
  }
}
