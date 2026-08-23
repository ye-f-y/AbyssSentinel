// src/utils/mqttClient.js
// MQTT连接管理
import mqtt from 'mqtt'
import { store, updateSensors, updateAI, updateDevice, handleCommand } from './dataStore'

// 默认用公共EMQX测试服务器，也可以连本地
const BROKER_URL = 'ws://localhost:8083/mqtt'

let client = null

export function connectMQTT(brokerUrl) {
  const url = brokerUrl || BROKER_URL

  client = mqtt.connect(url, {
    clientId: 'dashboard_' + Math.random().toString(16).slice(2, 10),
    reconnectPeriod: 3000,
    connectTimeout: 10000
  })

  client.on('connect', () => {
    console.log('MQTT已连接:', url)
    store.mqtt_connected = true

    client.subscribe([
      'sentinel/sensor_data',
      'sentinel/ai_analysis',
      'sentinel/commands',
      'sentinel/device_status'
    ])
  })

  client.on('disconnect', () => {
    store.mqtt_connected = false
  })

  client.on('error', (err) => {
    console.log('MQTT错误:', err.message)
  })

  client.on('message', (topic, payload) => {
    let data
    try {
      data = JSON.parse(payload.toString())
    } catch {
      return
    }

    switch (topic) {
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

export function disconnectMQTT() {
  if (client) {
    client.end()
    client = null
  }
}
