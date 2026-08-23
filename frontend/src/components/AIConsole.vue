<template>
  <div class="ai-console">
    <!-- 风险仪表盘 -->
    <div class="risk-panel">
      <div class="risk-label">当前风险等级</div>
      <div class="risk-value" :style="{ color: riskColor, textShadow: '0 0 30px ' + riskColor }">
        {{ riskLabel }}
      </div>
      <div v-if="store.ai.risk_level === 'CRITICAL'" class="blink-indicator">
        紧急预警 · 系统已启动应急响应
      </div>
    </div>

    <!-- 设备状态 -->
    <div class="status-bar">
      <div class="status-item">
        <span class="status-dot" :class="store.device.online ? 'green' : 'red'"></span>
        设备 {{ store.device.online ? '在线' : '离线' }}
      </div>
      <div class="status-item">
        <span class="status-dot" :class="store.device.relay_on ? 'green blink-dot' : 'gray'"></span>
        泵站 {{ store.device.relay_on ? '运行中' : '待机' }}
      </div>
      <div class="status-item">
        <span class="status-dot" :class="store.mqtt_connected ? 'green' : 'red'"></span>
        MQTT {{ store.mqtt_connected ? '已连接' : '未连接' }}
      </div>
    </div>

    <!-- 推演终端 -->
    <div class="terminal">
      <div class="terminal-header">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
        <span class="terminal-title">AI 推演终端</span>
      </div>
      <div class="terminal-body" ref="terminalBody">
        <!-- 初始化日志 -->
        <div v-for="(line, idx) in initLines" :key="'init-'+idx" class="terminal-line init-line">
          <span class="prompt">></span>
          <span>{{ line }}</span>
        </div>

        <!-- 历史推演区块（完整显示，不再被打断） -->
        <div v-for="(block, bIdx) in displayBlocks" :key="'blk-'+bIdx" class="analysis-block">
          <div v-for="(section, sIdx) in block.sections" :key="'s-'+bIdx+'-'+sIdx" class="analysis-section" :class="section.cls">
            <div class="section-title-text">{{ section.title }}</div>
            <div class="section-content" v-html="section.html"></div>
          </div>
        </div>

        <!-- 当前正在打字的区块 -->
        <div v-if="currentBlock.length > 0" class="analysis-block">
          <div v-for="(section, sIdx) in currentBlock" :key="'cur-'+sIdx" class="analysis-section" :class="section.cls">
            <div class="section-title-text">{{ section.title }}</div>
            <div class="section-content">
              <span v-if="section.typing" class="typing-text">{{ section.typing }}<span class="cursor">_</span></span>
              <span v-else v-html="section.html"></span>
            </div>
          </div>
        </div>

        <!-- AI分析中 -->
        <div v-if="store.ai.is_analyzing && currentBlock.length === 0 && displayBlocks.length === 0" class="terminal-line">
          <span class="prompt">></span>
          <span class="analyzing">AI推演中<span class="dots">...</span></span>
        </div>
      </div>
    </div>

    <!-- 引用规范标签 -->
    <div v-if="store.ai.regulations.length > 0" class="regulations">
      <div class="reg-title">引用国标规范</div>
      <div class="reg-list">
        <div v-for="(reg, idx) in store.ai.regulations" :key="idx" class="reg-tag">
          <span class="reg-icon">GB</span>{{ reg }}
        </div>
      </div>
    </div>

    <div class="quality" v-if="store.sensors.data_quality">
      数据质量: {{ store.sensors.data_quality }}
      <span v-if="store.sensors.timestamp"> | {{ formatTime(store.sensors.timestamp) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { store, riskColor } from '../utils/dataStore'

const terminalBody = ref(null)
const initLines = ref([
  '深渊哨兵 v1.0 初始化完成',
  '传感器数据链路就绪',
  'AI推演引擎已加载',
  '国标规范知识库在线',
  '等待实时数据...'
])

// 已完成的历史区块（每条analysis_text对应一个区块）
const displayBlocks = ref([])
// 当前正在打字的区块
const currentBlock = ref([])
// 打字控制标志
let isTyping = false
let pendingTexts = []   // 队列，不丢消息

// 风险等级中文映射
const riskLabel = computed(() => {
  const map = { NORMAL: '正常', WATCH: '关注', WARNING: '警告', CRITICAL: '紧急' }
  return map[store.ai.risk_level] || store.ai.risk_level
})

// 5段配置（无图标）
const SECTION_CONFIG = [
  { key: '数据解读', title: '数据解读', cls: 'sec-data' },
  { key: '灾害链推演', title: '灾害链推演', cls: 'sec-chain' },
  { key: '国标依据', title: '国标依据', cls: 'sec-reg' },
  { key: '风险评级', title: '风险评级', cls: 'sec-risk' },
  { key: '决策说明', title: '决策说明', cls: 'sec-decision' },
]

// 解析AI文本为5段结构
function parseSections(text) {
  const sections = {}
  const pattern = /【(数据解读|灾害链推演|国标依据|风险评级|决策说明)】\s*([\s\S]*?)(?=【(?:数据解读|灾害链推演|国标依据|风险评级|决策说明)】|$)/g
  let m
  while ((m = pattern.exec(text)) !== null) {
    const key = m[1]
    const content = m[2].trim()
    if (content) sections[key] = content
  }
  return sections
}

// 格式化段落内容（高亮国标条款）
function formatContent(key, content) {
  if (!content) return ''
  if (key === '国标依据') {
    return content
      .split('\n')
      .filter(l => l.trim())
      .map(line => {
        const highlighted = line.replace(
          /(GB\s*\d[\d\-]*[《][^》]*[》]|GB\s*\d[\d\-]*[^：:]*)/g,
          '<span class="highlight-gb">$1</span>'
        )
        return `<div class="reg-line">${highlighted}</div>`
      })
      .join('')
  }
  if (key === '灾害链推演') {
    return content
      .split(/(?<=。)\s*/)
      .filter(l => l.trim())
      .map(line => {
        const numbered = line.replace(/^(\d+[.、])/, '<span class="step-num">$1</span>')
        return `<div class="chain-step">${numbered}</div>`
      })
      .join('')
  }
  if (key === '风险评级') {
    return content.replace(/\b(NORMAL|WATCH|WARNING|CRITICAL)\b/g, '<span class="risk-highlight">$1</span>')
  }
  return content.replace(/\n/g, '<br>')
}

// 打字机效果：逐段完整打字，打完后整个区块移入历史
async function typeWriteBlock(sections) {
  const blockSections = []
  for (const config of SECTION_CONFIG) {
    const content = sections[config.key]
    if (!content) continue

    const sectionObj = {
      title: config.title,
      cls: config.cls,
      html: '',
      typing: ''
    }
    blockSections.push(sectionObj)
    currentBlock.value = [...blockSections]
    await nextTick()
    scrollToBottom()

    // 逐字打字（5ms/字，快节奏跟上演示速度）
    for (let i = 0; i <= content.length; i++) {
      sectionObj.typing = content.substring(0, i)
      currentBlock.value = [...blockSections]
      if (i % 5 === 0) scrollToBottom()
      await new Promise(r => setTimeout(r, 5))
    }

    // 打字完成，转为格式化HTML
    sectionObj.typing = ''
    sectionObj.html = formatContent(config.key, content)
    currentBlock.value = [...blockSections]
    await nextTick()
    scrollToBottom()
    await new Promise(r => setTimeout(r, 200))
  }

  // 整个区块打字完成，移入历史列表
  displayBlocks.value.push({ sections: blockSections })
  currentBlock.value = []
}

function scrollToBottom() {
  nextTick(() => {
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight
    }
  })
}

function formatTime(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('zh-CN')
}

// 即时显示（无打字机，用于演示模式）
function displayInstant(sections) {
  const blockSections = []
  for (const config of SECTION_CONFIG) {
    const content = sections[config.key]
    if (!content) continue
    blockSections.push({
      title: config.title,
      cls: config.cls,
      html: formatContent(config.key, content),
      typing: ''
    })
  }
  currentBlock.value = []
  displayBlocks.value.push({ sections: blockSections })
}

// 监听AI分析文字
watch(() => store.ai.analysis_text, async (text) => {
  if (!text) return
  initLines.value = []
  displayBlocks.value = []
  currentBlock.value = []

  const sections = parseSections(text)

  // 演示模式：跳过打字机，即时显示全部内容
  if (store.demo_mode) {
    displayInstant(sections)
    return
  }

  // 正常模式：打字机逐字显示
  if (isTyping) {
    pendingTexts.push(text)
    if (pendingTexts.length > 3) pendingTexts.shift()
    return
  }

  isTyping = true
  await typeWriteBlock(sections)
  isTyping = false

  while (pendingTexts.length > 0) {
    const next = pendingTexts.shift()
    isTyping = true
    const nextSections = parseSections(next)
    await typeWriteBlock(nextSections)
    isTyping = false
  }
}, { immediate: false })
</script>

<style scoped>
.ai-console {
  height: 100%; display: flex; flex-direction: column;
  gap: 12px;
  font-family: 'Consolas', 'Courier New', 'Microsoft YaHei', monospace;
}

/* 风险仪表盘 */
.risk-panel {
  text-align: center; padding: 14px;
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.35) 0%, rgba(30, 55, 110, 0.22) 100%);
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  transition: all 0.8s;
  flex-shrink: 0;
}
.risk-panel:hover {
  border-color: rgba(153,192,254,0.55);
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.50) 0%, rgba(30, 55, 110, 0.35) 100%);
}
.risk-label { color: #c8d6ec; font-size: 13px; letter-spacing: 3px; }
.risk-value {
  font-family: 'Orbitron', monospace;
  font-size: 40px; font-weight: 900;
  margin: 8px 0;
  transition: color 1s, text-shadow 1s;
}
.blink-indicator {
  color: #ff3333;
  font-size: 13px;
  animation: blink 0.6s infinite;
  letter-spacing: 2px;
  font-weight: 600;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.15; }
}

/* 状态栏 */
.status-bar {
  display: flex; flex-direction: column; gap: 5px;
  padding: 10px 12px;
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.35) 0%, rgba(30, 55, 110, 0.22) 100%);
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px;
  font-size: 13px; color: #c8d6ec;
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  flex-shrink: 0;
}
.status-item { display: flex; align-items: center; gap: 8px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.status-dot.green { background: #00ff88; box-shadow: 0 0 8px #00ff8888; }
.status-dot.red { background: #ff4444; box-shadow: 0 0 8px #ff444488; }
.status-dot.gray { background: #555; }
.status-dot.blink-dot { animation: blink 0.6s infinite; }

/* 终端 */
.terminal {
  flex: 1; display: flex; flex-direction: column;
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px; overflow: hidden;
  background: rgba(4, 8, 16, 0.88);
  box-shadow: 0 4px 16px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06);
  min-height: 200px;
}
.terminal-header {
  background: #0d1226;
  padding: 10px 14px;
  display: flex; align-items: center; gap: 8px;
}
.dot { width: 11px; height: 11px; border-radius: 50%; }
.dot.red { background: #ff5f57; }
.dot.yellow { background: #febc2e; }
.dot.green { background: #28c840; }
.terminal-title { color: #a8b8d0; font-size: 13px; margin-left: 8px; letter-spacing: 2px; }

.terminal-body {
  flex: 1; overflow-y: auto;
  padding: 14px;
  background: rgba(4, 8, 16, 0.88);
  scroll-behavior: smooth;
}

/* 初始化日志行 */
.terminal-line {
  color: #00cc66; font-size: 13px;
  line-height: 1.8; margin-bottom: 2px;
}
.init-line { color: #667788; font-size: 12px; }
.prompt { color: #4488cc; margin-right: 10px; font-weight: bold; font-size: 14px; }
.analyzing { color: #ffaa00; font-size: 14px; }
.dots { animation: blink 1s infinite; }
.cursor { color: #00ff88; animation: blink 1s infinite; }

/* 推演区块 */
.analysis-block {
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(153,192,254,0.12);
}
.analysis-block:last-child { border-bottom: none; }

/* 结构化段落 */
.analysis-section {
  margin-bottom: 10px;
  padding: 6px 10px;
  border-left: 3px solid;
  border-radius: 0 6px 6px 0;
  background: rgba(255,255,255,0.02);
}
.analysis-section.sec-data { border-left-color: #00b4d8; }
.analysis-section.sec-chain { border-left-color: #f0c040; }
.analysis-section.sec-reg { border-left-color: #00cc66; }
.analysis-section.sec-risk { border-left-color: #ff8800; }
.analysis-section.sec-decision { border-left-color: #ff4444; }

.section-title-text {
  font-size: 13px; font-weight: 700;
  margin-bottom: 5px;
  letter-spacing: 1px;
}
.sec-data .section-title-text { color: #00b4d8; }
.sec-chain .section-title-text { color: #f0c040; }
.sec-reg .section-title-text { color: #00cc66; }
.sec-risk .section-title-text { color: #ff8800; }
.sec-decision .section-title-text { color: #ff6644; }

.section-content {
  color: #c8dce8; font-size: 13px;
  line-height: 1.8; word-break: break-word;
}
.typing-text { color: #e0eaf8; }

/* 国标条款行 */
.reg-line {
  padding: 3px 0;
  border-bottom: 1px dashed rgba(0,204,102,0.15);
}
.reg-line:last-child { border-bottom: none; }
.highlight-gb {
  color: #f0c040;
  font-weight: bold;
  text-shadow: 0 0 6px rgba(240,192,64,0.3);
}

/* 灾害链步骤 */
.chain-step { padding: 2px 0; }
.step-num { color: #f0c040; font-weight: bold; margin-right: 4px; }

/* 风险等级高亮 */
.risk-highlight {
  font-weight: bold;
  padding: 0 4px;
  border-radius: 3px;
  background: rgba(255,136,0,0.2);
}

/* 规范标签 */
.regulations {
  padding: 10px;
  background: linear-gradient(180deg, rgba(15, 30, 70, 0.35) 0%, rgba(30, 55, 110, 0.22) 100%);
  border: 1px solid rgba(153,192,254,0.30);
  border-radius: 12px;
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.10);
  flex-shrink: 0;
}
.reg-title { color: #a8b8d0; font-size: 12px; margin-bottom: 6px; letter-spacing: 2px; font-weight: 600; }
.reg-list { display: flex; flex-wrap: wrap; gap: 6px; }
.reg-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(0,200,100,0.10);
  color: #00cc66;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 5px;
  border: 1px solid rgba(0,200,100,0.2);
  transition: all 0.2s;
}
.reg-tag:hover { background: rgba(0,200,100,0.18); }
.reg-icon {
  font-size: 10px; font-weight: 900;
  background: #00cc66; color: #040810;
  padding: 1px 4px; border-radius: 2px;
  letter-spacing: 1px;
}

.quality { color: #667788; font-size: 11px; text-align: center; }
</style>
