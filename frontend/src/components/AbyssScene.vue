<template>
  <div ref="container" class="abyss-scene">
    <!-- 触控反馈 Toast -->
    <div ref="toastEl" class="touch-toast">{{ toastMsg }}</div>

    <!-- 加载提示 -->
    <div class="scene-loading" v-if="loading">
      <div class="loading-spinner"></div>
      <p>3D 城市加载中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { store, rainIntensity, soilSaturation } from '../utils/dataStore'

// ==================== 模板引用 ====================
const container = ref(null)
const toastEl = ref(null)
const loading = ref(true)

// ==================== 响应式 UI 状态 ====================
const demoActive = ref(false)
const stormActive = ref(false)
const toastMsg = ref('')

let _demoPhase = 0 // 0=idle, 1=flowing back, 2=pump draining, 3=finished

// ==================== Three.js 核心变量 ====================
let scene, camera, renderer, controls, canvasEl, clock
let animationId

// 场景对象引用
let skyDome, skyMat, skyTex
let ambientLight, dirLight, fillLight, hemiLight
let terrain, terrainGeo, terrainMat
let water, waterGeo, waterMat
let drain, drainHole
let rain, rainGeo, rainMat
let mist, mistGeo, mistMat
let inletSplash, inletSplashGeo, inletSplashMat, inletSplashVel
let inletPositions, inletSplashCount
let floodWater, floodGeo, floodTex
let waterPump
let flowGeo, flowCount, flowMat, flowParticles
let weatherSensor, soilSensor, weatherSign, soilSign
let trafficLight, trafficLight2
let buildings = []
let bridge1Cars = []
let bridge2Cars = []
let overflowWaters = []
let overflowWaterTex

// 共享材质 / 纹理
let depYellowMat, stripeTex, buildingFacadeTex, windowTex, rustTex
let buildingPositions = []

// ---- 性能优化缓存 ----
let cachedPuddles = []   // 缓存水洼 mesh，避免每帧 scene.traverse
let cachedPonds = []     // 缓存池塘 mesh
let cachedLeds = []      // 缓存传感器 LED mesh
let frameCount = 0       // 帧计数器，用于节流重负载操作

// ==================== 常量 ====================
const roadDepth = -5.5
const roadWidth = 8
const roadLength = 30
const bridgeWidth = 6
const bridgeHeight = 0.6

// ==================== 演示 / 暴雨状态 ====================
let overflowLevel = 1.0
let pitLevel = 1.0
let stormLevel = 0
let stormRising = false
let pumpVibration = 0

const minLevel = 0.02
const flowSpeed = 0.12
const pumpSpeed = 0.025
const pitRiseAmount = 0.25

// ==================== Toast ====================
let toastTimer = null
function showToast(msg) {
  toastMsg.value = msg
  if (toastEl.value) {
    toastEl.value.classList.add('show')
  }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    if (toastEl.value) toastEl.value.classList.remove('show')
  }, 1200)
}

// ==================== 涟漪点击动效 ====================
function addRipple(e) {
  const btn = e.currentTarget
  const rect = btn.getBoundingClientRect()
  const ripple = document.createElement('span')
  ripple.className = 'ripple'
  const size = Math.max(rect.width, rect.height)
  ripple.style.width = ripple.style.height = size + 'px'
  ripple.style.left = (e.clientX - rect.left - size / 2) + 'px'
  ripple.style.top = (e.clientY - rect.top - size / 2) + 'px'
  btn.appendChild(ripple)
  setTimeout(() => ripple.remove(), 600)
}

// ==================== CANVAS TEXTURES ====================
function createStripeTexture() {
  const c = document.createElement('canvas'); c.width = 128; c.height = 256
  const ctx = c.getContext('2d')
  const stripeH = 32
  for (let y = 0; y < 256; y += stripeH * 2) {
    ctx.fillStyle = '#FFD700'; ctx.fillRect(0, y, 128, stripeH)
    ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, y + stripeH, 128, stripeH)
  }
  const tex = new THREE.CanvasTexture(c); tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createBuildingFacadeTexture() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 512
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#c4b5a5'; ctx.fillRect(0, 0, 512, 512)
  for (let i = 0; i < 30; i++) {
    const g = ctx.createRadialGradient(200 + Math.random() * 112, 100 + Math.random() * 312, 5, 200 + Math.random() * 112, 100 + Math.random() * 312, 15 + Math.random() * 40)
    g.addColorStop(0, 'rgba(80,70,60,0.6)'); g.addColorStop(.5, 'rgba(100,90,80,0.3)'); g.addColorStop(1, 'rgba(180,160,140,0)')
    ctx.fillStyle = g; ctx.fillRect(0, 0, 512, 512)
  }
  for (let i = 0; i < 8; i++) {
    const x = Math.random() * 460, y = Math.random() * 460
    ctx.fillStyle = '#d4c8b8'; ctx.beginPath()
    ctx.moveTo(x, y); ctx.lineTo(x + 20 + Math.random() * 30, y + 5)
    ctx.lineTo(x + 15 + Math.random() * 35, y + 20 + Math.random() * 30)
    ctx.lineTo(x - 5, y + 15); ctx.closePath(); ctx.fill()
  }
  ctx.strokeStyle = 'rgba(100,90,80,0.5)'; ctx.lineWidth = 1
  for (let i = 1; i < 6; i++) { ctx.beginPath(); ctx.moveTo(0, i * 85); ctx.lineTo(512, i * 85); ctx.stroke() }
  ctx.lineWidth = .5
  for (let i = 0; i < 20; i++) { ctx.beginPath(); ctx.moveTo(Math.random() * 512, Math.random() * 512)
    ctx.lineTo(Math.random() * 512, Math.random() * 512); ctx.stroke() }
  const tex = new THREE.CanvasTexture(c); tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createRoadTexture() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 512
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#3a3a3a'; ctx.fillRect(0, 0, 512, 512)
  for (let i = 0; i < 2000; i++) {
    ctx.fillStyle = `rgba(${50 + Math.random() * 30},${50 + Math.random() * 30},${50 + Math.random() * 30},0.3)`
    ctx.fillRect(Math.random() * 512, Math.random() * 512, 3 + Math.random() * 5, 3 + Math.random() * 5)
  }
  ctx.strokeStyle = '#1a1a1a'; ctx.lineWidth = 2
  for (let i = 0; i < 8; i++) {
    ctx.beginPath(); const sx = Math.random() * 512, sy = Math.random() * 512
    ctx.moveTo(sx, sy)
    let cx = sx, cy = sy
    for (let j = 0; j < 6; j++) { cx += (Math.random() - .5) * 60; cy += (Math.random() - .5) * 60; ctx.lineTo(cx, cy) }
    ctx.stroke()
  }
  for (let i = 0; i < 5; i++) {
    ctx.fillStyle = '#252525'; ctx.fillRect(Math.random() * 450, Math.random() * 450, 30 + Math.random() * 50, 20 + Math.random() * 40)
  }
  ctx.setLineDash([30, 20]); ctx.strokeStyle = '#dddddd'
  ctx.beginPath(); ctx.moveTo(256, 0); ctx.lineTo(256, 512); ctx.stroke()
  ctx.setLineDash([])
  const tex = new THREE.CanvasTexture(c); tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createWarningSignTexture() {
  const c = document.createElement('canvas'); c.width = 256; c.height = 320
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#cc0000'; ctx.fillRect(0, 0, 256, 320)
  ctx.fillStyle = '#ffffff'; ctx.fillRect(10, 10, 236, 300)
  ctx.fillStyle = '#cc0000'; ctx.fillRect(20, 20, 216, 280)
  ctx.fillStyle = '#FFD700'
  ctx.beginPath(); ctx.moveTo(128, 45); ctx.lineTo(40, 190); ctx.lineTo(216, 190); ctx.closePath(); ctx.fill()
  ctx.fillStyle = '#1a1a1a'
  ctx.beginPath(); ctx.moveTo(128, 65); ctx.lineTo(55, 180); ctx.lineTo(201, 180); ctx.closePath(); ctx.fill()
  ctx.fillStyle = '#FFD700'; ctx.font = 'bold 28px "Microsoft YaHei"'; ctx.textAlign = 'center'
  ctx.fillText('!', 128, 160)
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 24px "Microsoft YaHei"'
  ctx.fillText('水深危险', 128, 240)
  ctx.fillText('禁止通行', 128, 275)
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createWindowTexture() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 80
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#1a2a3a'; ctx.fillRect(0, 0, 64, 80)
  ctx.fillStyle = '#334455'; ctx.fillRect(4, 4, 56, 72)
  ctx.strokeStyle = '#555'; ctx.lineWidth = 2
  ctx.strokeRect(4, 4, 56, 72)
  ctx.beginPath(); ctx.moveTo(32, 4); ctx.lineTo(32, 76); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(4, 40); ctx.lineTo(60, 40); ctx.stroke()
  ctx.fillStyle = 'rgba(100,150,200,0.3)'
  ctx.fillRect(6, 6, 24, 32); ctx.fillRect(34, 44, 24, 30)
  ctx.strokeStyle = '#667788'; ctx.lineWidth = 1.5
  for (let y = 10; y < 75; y += 16) { ctx.beginPath(); ctx.moveTo(4, y); ctx.lineTo(60, y); ctx.stroke() }
  for (let x = 16; x < 55; x += 16) { ctx.beginPath(); ctx.moveTo(x, 4); ctx.lineTo(x, 76); ctx.stroke() }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createRustTexture() {
  const c = document.createElement('canvas'); c.width = 128; c.height = 128
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#5a3a2a'; ctx.fillRect(0, 0, 128, 128)
  for (let i = 0; i < 300; i++) {
    const r = 80 + Math.random() * 60, g = 40 + Math.random() * 30, b = 10 + Math.random() * 20
    ctx.fillStyle = `rgba(${r},${g},${b},0.6)`
    ctx.fillRect(Math.random() * 128, Math.random() * 128, 2 + Math.random() * 5, 2 + Math.random() * 5)
  }
  ctx.strokeStyle = 'rgba(180,80,40,0.5)'; ctx.lineWidth = 1
  for (let i = 0; i < 15; i++) { ctx.beginPath(); ctx.moveTo(Math.random() * 128, Math.random() * 128)
    ctx.lineTo(Math.random() * 128, Math.random() * 128); ctx.stroke() }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; return tex
}

function createNeonSignTexture(text, color) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#111'; ctx.fillRect(0, 0, 256, 64)
  ctx.shadowColor = color; ctx.shadowBlur = 15
  ctx.fillStyle = color; ctx.font = 'bold 28px "Microsoft YaHei"'; ctx.textAlign = 'center'
  ctx.fillText(text, 128, 42)
  ctx.shadowBlur = 0
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; return tex
}

// ==================== 光标状态管理器 ====================
const CursorState = { IDLE: 'grab', ROTATING: 'grabbing', PANNING: 'move', ZOOMING: 'ns-resize' }
let currentCursor = ''
let activeButton = -1
let wheelRAF = null
let touchPinchActive = false

function setCursor(state) {
  if (currentCursor === state) return
  currentCursor = state
  if (canvasEl) canvasEl.style.cursor = state
}

function resetCursor() {
  activeButton = -1
  setCursor(CursorState.IDLE)
}

// ==================== 初始化场景 ====================
function initScene() {
  const w = container.value.clientWidth
  const h = container.value.clientHeight

  // 渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.9
  container.value.appendChild(renderer.domElement)
  canvasEl = renderer.domElement
  canvasEl.style.touchAction = 'none'

  // 场景
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x3a3a4e, 0.00001)
  scene.background = new THREE.Color(0x3a3a4e)

  // 相机
  camera = new THREE.PerspectiveCamera(55, w / h, 0.5, 300)
  camera.position.set(35, 28, 38)
  camera.lookAt(0, -3, 0)

  // OrbitControls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, -2, 0)
  controls.rotateSpeed = 1.2
  controls.zoomSpeed = 1.5
  controls.panSpeed = 2.0
  controls.screenSpacePanning = true
  controls.minDistance = 5; controls.maxDistance = 100
  controls.maxPolarAngle = Math.PI * 0.48; controls.minPolarAngle = 0.2
  controls.update()

  clock = new THREE.Clock()

  // ---- 光标交互 ----
  setCursor(CursorState.IDLE)
  canvasEl.addEventListener('pointerdown', (e) => {
    activeButton = e.button
    if (e.button === 0) setCursor(CursorState.ROTATING)
    else if (e.button === 1) setCursor(CursorState.ZOOMING)
    else if (e.button === 2) setCursor(CursorState.PANNING)
  })
  canvasEl.addEventListener('pointerup', resetCursor)
  canvasEl.addEventListener('pointercancel', resetCursor)
  canvasEl.addEventListener('contextmenu', (e) => e.preventDefault())
  canvasEl.addEventListener('wheel', () => {
    if (wheelRAF) return
    setCursor(CursorState.ZOOMING)
    wheelRAF = requestAnimationFrame(() => {
      wheelRAF = null
      if (activeButton === -1) setCursor(CursorState.IDLE)
    })
  }, { passive: true })
  canvasEl.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) { touchPinchActive = true; showToast('双指缩放中') }
  }, { passive: true })
  canvasEl.addEventListener('touchend', () => {
    if (touchPinchActive) { touchPinchActive = false; showToast('触控结束') }
  }, { passive: true })

  // ---- Sky dome ----
  const skyGeo = new THREE.SphereGeometry(100, 32, 32)
  const skyCanvas = document.createElement('canvas'); skyCanvas.width = 512; skyCanvas.height = 512
  const skyCtx = skyCanvas.getContext('2d')
  const skyGrad = skyCtx.createLinearGradient(0, 0, 0, 512)
  skyGrad.addColorStop(0, '#111122'); skyGrad.addColorStop(0.3, '#1a1a30')
  skyGrad.addColorStop(0.5, '#2a2a3a'); skyGrad.addColorStop(0.7, '#3a3a40')
  skyGrad.addColorStop(1, '#4a4a4a')
  skyCtx.fillStyle = skyGrad; skyCtx.fillRect(0, 0, 512, 512)
  skyCtx.fillStyle = 'rgba(40,40,50,0.3)'
  for (let i = 0; i < 60; i++) { skyCtx.fillRect(Math.random() * 512, Math.random() * 200, 40 + Math.random() * 100, 3 + Math.random() * 8) }
  skyTex = new THREE.CanvasTexture(skyCanvas); skyTex.colorSpace = THREE.SRGBColorSpace
  skyMat = new THREE.MeshBasicMaterial({ map: skyTex, side: THREE.BackSide })
  skyDome = new THREE.Mesh(skyGeo, skyMat); scene.add(skyDome)

  // ---- Lights ----
  ambientLight = new THREE.AmbientLight(0x8899bb, 2.0); scene.add(ambientLight)
  dirLight = new THREE.DirectionalLight(0xdddddd, 2.2)
  dirLight.position.set(20, 30, 10); dirLight.castShadow = true
  dirLight.shadow.mapSize.width = 2048; dirLight.shadow.mapSize.height = 2048
  dirLight.shadow.camera.near = 0.5; dirLight.shadow.camera.far = 100
  dirLight.shadow.camera.left = -50; dirLight.shadow.camera.right = 50
  dirLight.shadow.camera.top = 50; dirLight.shadow.camera.bottom = -50
  dirLight.shadow.bias = -0.0001; scene.add(dirLight)
  fillLight = new THREE.DirectionalLight(0xaabbdd, 1.0); fillLight.position.set(-15, 20, -10); scene.add(fillLight)
  hemiLight = new THREE.HemisphereLight(0x8899bb, 0x667755, 1.5); scene.add(hemiLight)

  buildTerrain()
  buildInterchange()
  buildWater()
  buildCars()
  buildRoadSystem()
  buildBuildings()
  buildCommunityFacilities()
  buildVillas()
  buildPavilions()
  buildPonds()
  buildLandscape()
  buildStreetFurniture()
  buildSensors()
  buildWaterPump()
  buildRain()
  buildMist()
  buildInletSplash()

  // 缓存需要每帧更新的对象引用，避免 animate 中 scene.traverse
  cacheSceneObjects()
}

// ==================== 缓存场景对象（性能优化） ====================
function cacheSceneObjects() {
  cachedPuddles = []
  cachedPonds = []
  cachedLeds = []
  scene.traverse(obj => {
    if (obj.name === 'puddle') cachedPuddles.push(obj)
    else if (obj.name === 'pond') cachedPonds.push(obj)
    else if (obj.name && obj.name.startsWith('led_')) cachedLeds.push(obj)
  })
}

// ==================== 地形 ====================
function buildTerrain() {
  const hillTexCanvas = document.createElement('canvas'); hillTexCanvas.width = 256; hillTexCanvas.height = 256
  const hCtx = hillTexCanvas.getContext('2d')
  hCtx.fillStyle = '#b8965a'; hCtx.fillRect(0, 0, 256, 256)
  for (let i = 0; i < 1500; i++) {
    const r = 150 + Math.random() * 60, g = 120 + Math.random() * 50, b = 60 + Math.random() * 40
    hCtx.fillStyle = `rgba(${r},${g},${b},0.5)`
    hCtx.fillRect(Math.random() * 256, Math.random() * 256, 2 + Math.random() * 6, 2 + Math.random() * 6)
  }
  for (let i = 0; i < 200; i++) {
    hCtx.fillStyle = `rgba(${80+Math.random()*40},${100+Math.random()*40},${50+Math.random()*30},0.3)`
    hCtx.fillRect(Math.random() * 256, Math.random() * 256, 3 + Math.random() * 8, 3 + Math.random() * 8)
  }
  for (let i = 0; i < 50; i++) {
    hCtx.fillStyle = `rgba(${100+Math.random()*40},${95+Math.random()*30},${85+Math.random()*30},0.6)`
    hCtx.beginPath()
    hCtx.arc(Math.random() * 256, Math.random() * 256, 1 + Math.random() * 3, 0, Math.PI * 2)
    hCtx.fill()
  }
  const hillTex = new THREE.CanvasTexture(hillTexCanvas)
  hillTex.wrapS = hillTex.wrapT = THREE.RepeatWrapping; hillTex.repeat.set(6, 6)
  hillTex.colorSpace = THREE.SRGBColorSpace

  const terrainSize = 80; const terrainSeg = 120
  terrainGeo = new THREE.PlaneGeometry(terrainSize, terrainSize, terrainSeg, terrainSeg)
  terrainGeo.rotateX(-Math.PI / 2)
  const posArr = terrainGeo.attributes.position.array
  const colorArr = new Float32Array(posArr.length)

  for (let i = 0; i < posArr.length; i += 3) {
    const x = posArr[i], z = posArr[i + 2]
    const dist = Math.sqrt(x * x + z * z)
    const depression = Math.max(0, 1 - dist / 20) * 9
    let hillHeight = 0
    if (dist > 24) {
      const hillFactor = Math.min(1, (dist - 24) / 10)
      hillHeight = (Math.sin(x * 0.25) * Math.cos(z * 0.2) * 2.5
        + Math.sin(x * 0.15 + z * 0.18) * 2.0
        + Math.sin(x * 0.4 - z * 0.35) * 1.2
        + Math.cos(z * 0.3) * 1.5) * hillFactor
      hillHeight = Math.max(0, hillHeight)
    }
    const noise = Math.sin(x * 0.8) * Math.cos(z * 0.7) * 0.3 + Math.sin(x * 1.5 + z * 1.3) * 0.2
    posArr[i + 1] = -depression + hillHeight + noise
    let concreteMix, hillMix
    if (dist < 24) { concreteMix = 1.0; hillMix = 0.0 }
    else if (dist < 30) { const t = (dist - 24) / 6; concreteMix = 1.0 - t; hillMix = t }
    else { concreteMix = 0.0; hillMix = 1.0 }
    colorArr[i] = 0.6 * concreteMix + 0.72 * hillMix
    colorArr[i + 1] = 0.6 * concreteMix + 0.58 * hillMix
    colorArr[i + 2] = 0.6 * concreteMix + 0.35 * hillMix
  }
  terrainGeo.setAttribute('color', new THREE.BufferAttribute(colorArr, 3))
  terrainGeo.computeVertexNormals()
  terrainMat = new THREE.MeshStandardMaterial({ vertexColors: true, map: hillTex, roughness: 0.6, metalness: 0.05 })
  terrain = new THREE.Mesh(terrainGeo, terrainMat)
  terrain.receiveShadow = true; scene.add(terrain)
}

// ==================== 立交结构 ====================
function buildInterchange() {
  const depRoadGeo = new THREE.PlaneGeometry(roadWidth, roadLength)
  depRoadGeo.rotateX(-Math.PI / 2)
  const depRoadTex = createRoadTexture(); depRoadTex.repeat.set(1, 4)
  const depRoadMat = new THREE.MeshStandardMaterial({ map: depRoadTex, roughness: 0.25, metalness: 0.2, color: 0x333333 })
  const depRoad = new THREE.Mesh(depRoadGeo, depRoadMat)
  depRoad.position.y = roadDepth; depRoad.receiveShadow = true; scene.add(depRoad)

  depYellowMat = new THREE.MeshStandardMaterial({ color: 0xffee00, roughness: 0.3, emissive: 0xffaa00, emissiveIntensity: 0.8 })
  for (let s = -1; s <= 1; s += 2) {
    const dlGeo = new THREE.PlaneGeometry(0.35, roadLength); dlGeo.rotateX(-Math.PI / 2)
    const dl = new THREE.Mesh(dlGeo, depYellowMat); dl.position.set(s * 0.25, roadDepth + 0.2, 0); scene.add(dl)
  }

  const upperRoadGeo = new THREE.PlaneGeometry(roadWidth, roadLength); upperRoadGeo.rotateX(-Math.PI / 2)
  const upperRoad = new THREE.Mesh(upperRoadGeo, depRoadMat.clone())
  upperRoad.position.y = roadDepth + 0.1; upperRoad.rotation.y = Math.PI / 2
  upperRoad.receiveShadow = true; scene.add(upperRoad)
  for (let s = -1; s <= 1; s += 2) {
    const elGeo = new THREE.PlaneGeometry(0.35, roadLength); elGeo.rotateX(-Math.PI / 2)
    const el = new THREE.Mesh(elGeo, depYellowMat); el.position.set(0, roadDepth + 0.3, s * 0.25); el.rotation.y = Math.PI / 2; scene.add(el)
  }

  const pitFloorGeo = new THREE.PlaneGeometry(roadWidth, roadLength); pitFloorGeo.rotateX(-Math.PI / 2)
  const pitFloorTex = createRoadTexture(); pitFloorTex.repeat.set(2, 6)
  const pitFloorMat = new THREE.MeshStandardMaterial({ map: pitFloorTex, roughness: 0.3, metalness: 0.15, color: 0x2a2a2a })
  const pitFloor = new THREE.Mesh(pitFloorGeo, pitFloorMat)
  pitFloor.position.y = roadDepth - 0.02; pitFloor.receiveShadow = true; scene.add(pitFloor)

  const slopeMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.4, metalness: 0.1 })
  for (let s = -1; s <= 1; s += 2) {
    const slGeo = new THREE.PlaneGeometry(roadWidth + 0.5, 1.5); slGeo.rotateX(-Math.PI / 2)
    const sl = new THREE.Mesh(slGeo, slopeMat); sl.position.set(0, roadDepth + 0.03, s * (roadLength / 2 - 0.5)); sl.rotation.x = s * 0.15; sl.receiveShadow = true; scene.add(sl)
  }
  for (let s = -1; s <= 1; s += 2) {
    const slGeo = new THREE.PlaneGeometry(1.5, roadLength + 0.5); slGeo.rotateX(-Math.PI / 2)
    const sl = new THREE.Mesh(slGeo, slopeMat); sl.position.set(s * (roadWidth / 2 - 0.5), roadDepth + 0.03, 0); sl.rotation.z = -s * 0.15; sl.receiveShadow = true; scene.add(sl)
  }

  stripeTex = createStripeTexture(); stripeTex.repeat.set(1, 2)
  function createRetainingWall(x, z, rotY, w, h, d) {
    const geo = new THREE.BoxGeometry(w, h, d)
    const mat = new THREE.MeshStandardMaterial({ map: stripeTex, roughness: 0.4, metalness: 0.1 })
    const wall = new THREE.Mesh(geo, mat); wall.position.set(x, roadDepth + h / 2, z); wall.rotation.y = rotY
    wall.castShadow = true; wall.receiveShadow = true; scene.add(wall); return wall
  }
  const wallGap = bridgeWidth / 2 + 0.3
  const wallTotalW = roadWidth + 0.5
  const wallSegW = (wallTotalW / 2) - wallGap
  createRetainingWall(-(wallGap + wallSegW / 2), -roadLength / 2, 0, wallSegW, 6, 0.4)
  createRetainingWall( (wallGap + wallSegW / 2), -roadLength / 2, 0, wallSegW, 6, 0.4)
  createRetainingWall(-(wallGap + wallSegW / 2), roadLength / 2, 0, wallSegW, 6, 0.4)
  createRetainingWall( (wallGap + wallSegW / 2), roadLength / 2, 0, wallSegW, 6, 0.4)
  const wallTotalL = roadLength
  const wallSegL = (wallTotalL / 2) - wallGap
  createRetainingWall(-roadWidth / 2, -(wallGap + wallSegL / 2), 0, 0.4, 6, wallSegL)
  createRetainingWall(-roadWidth / 2,  (wallGap + wallSegL / 2), 0, 0.4, 6, wallSegL)
  createRetainingWall(roadWidth / 2, -(wallGap + wallSegL / 2), 0, 0.4, 6, wallSegL)
  createRetainingWall(roadWidth / 2,  (wallGap + wallSegL / 2), 0, 0.4, 6, wallSegL)

  function createSlopeWall(x, z, rotY, w, h, d) {
    const geo = new THREE.BoxGeometry(w, h, d)
    const mat = new THREE.MeshStandardMaterial({ color: 0x666655, roughness: 0.3, metalness: 0.1 })
    const slope = new THREE.Mesh(geo, mat); slope.position.set(x, -3, z); slope.rotation.y = rotY
    slope.castShadow = true; slope.receiveShadow = true; scene.add(slope); return slope
  }
  createSlopeWall(0, -roadLength / 2 - 2, 0, roadWidth + 0.5, 2.5, 4)
  createSlopeWall(0, roadLength / 2 + 2, 0, roadWidth + 0.5, 2.5, 4)
  createSlopeWall(-roadWidth / 2 - 2, 0, 0, 4, 2.5, roadLength)
  createSlopeWall(roadWidth / 2 + 2, 0, 0, 4, 2.5, roadLength)

  const rampMat = new THREE.MeshStandardMaterial({ map: (function() { const t = createRoadTexture(); t.repeat.set(1, 2); return t; })(), roughness: 0.3, metalness: 0.15, color: 0x383838 })
  function createRoadRamp(x, z, rotY, w, l, startY, endY) {
    const segs = 16
    const geo = new THREE.PlaneGeometry(w, l, 1, segs); geo.rotateX(-Math.PI / 2)
    const pos = geo.attributes.position.array
    for (let i = 0; i < pos.length; i += 3) {
      const lz = pos[i + 2]; const t = (lz + l / 2) / l; pos[i + 1] = startY + (endY - startY) * t
    }
    geo.computeVertexNormals()
    const ramp = new THREE.Mesh(geo, rampMat); ramp.position.set(x, 0, z); ramp.rotation.y = rotY
    ramp.receiveShadow = true; ramp.castShadow = true; scene.add(ramp)
    for (let s = -1; s <= 1; s += 2) {
      const lineSegs = 12
      for (let seg = 0; seg < lineSegs; seg++) {
        const t1 = seg / lineSegs; const t2 = (seg + 1) / lineSegs
        const z1 = -l / 2 + t1 * l; const z2 = -l / 2 + t2 * l
        const y1 = startY + (endY - startY) * t1; const y2 = startY + (endY - startY) * t2
        const len = Math.sqrt((z2 - z1) ** 2 + (y2 - y1) ** 2)
        const midZ = (z1 + z2) / 2; const midY = (y1 + y2) / 2
        const angle = Math.atan2(y2 - y1, z2 - z1)
        const lineGeo = new THREE.PlaneGeometry(0.35, len); lineGeo.rotateX(-Math.PI / 2)
        const line = new THREE.Mesh(lineGeo, depYellowMat)
        line.position.set(s * 0.25, midY + 0.05, midZ); line.rotation.x = -angle; ramp.add(line)
      }
    }
    return ramp
  }
  const rampLen = 4
  createRoadRamp(0, roadLength / 2 + rampLen / 2, 0, roadWidth, rampLen, 0.05, roadDepth + 0.05)
  createRoadRamp(0, -(roadLength / 2 + rampLen / 2), Math.PI, roadWidth, rampLen, 0.05, roadDepth + 0.05)
  createRoadRamp(roadWidth / 2 + rampLen / 2, 0, -Math.PI / 2, roadWidth, rampLen, 0.05, roadDepth + 0.05)
  createRoadRamp(-(roadWidth / 2 + rampLen / 2), 0, Math.PI / 2, roadWidth, rampLen, 0.05, roadDepth + 0.05)

  // Twin bridges
  const bridge1RoadTex = createRoadTexture(); bridge1RoadTex.repeat.set(2, 1)
  const bridge1DeckMat = new THREE.MeshStandardMaterial({ map: bridge1RoadTex, roughness: 0.3, metalness: 0.2, color: 0x555555 })
  const bridge1DeckLen = 22
  const bridge1Geo = new THREE.BoxGeometry(bridge1DeckLen, bridgeHeight, bridgeWidth)
  const bridge1 = new THREE.Mesh(bridge1Geo, bridge1DeckMat)
  bridge1.position.set(0, roadDepth + 5.5, 0); bridge1.castShadow = true; bridge1.receiveShadow = true; scene.add(bridge1)
  for (let s = -1; s <= 1; s += 2) {
    const supGeo = new THREE.BoxGeometry(0.5, 5.5, 0.5)
    const sup = new THREE.Mesh(supGeo, new THREE.MeshStandardMaterial({ color: 0x777777, roughness: 0.3, metalness: 0.3 }))
    sup.position.set(s * 3, roadDepth + 2.75, 0); sup.castShadow = true; scene.add(sup)
  }
  for (let s = -1; s <= 1; s += 2) {
    const railGeo = new THREE.BoxGeometry(bridge1DeckLen, 1, 0.15)
    const rail = new THREE.Mesh(railGeo, new THREE.MeshStandardMaterial({ color: 0x999999, roughness: 0.2, metalness: 0.5 }))
    rail.position.set(0, roadDepth + 5.5 + 0.7, s * (bridgeWidth / 2)); rail.castShadow = true; scene.add(rail)
  }
  const bridge1LineY = roadDepth + 5.5 + bridgeHeight / 2 + 0.02
  for (let s = -1; s <= 1; s += 2) {
    const blGeo = new THREE.PlaneGeometry(bridge1DeckLen, 0.35); blGeo.rotateX(-Math.PI / 2)
    const bl = new THREE.Mesh(blGeo, depYellowMat); bl.position.set(0, bridge1LineY, s * 0.25); scene.add(bl)
  }
  for (let q = -1; q <= 1; q += 2) {
    const dashCount = Math.floor(bridge1DeckLen / 1.5)
    for (let d = 0; d < dashCount; d++) {
      if (d % 2 === 0) {
        const bdGeo = new THREE.PlaneGeometry(0.8, 0.15); bdGeo.rotateX(-Math.PI / 2)
        const bd = new THREE.Mesh(bdGeo, new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.6 }))
        bd.position.set(-bridge1DeckLen / 2 + d * 1.5 + 0.75, bridge1LineY, q * bridgeWidth * 0.25); bd.rotation.y = Math.PI / 2; scene.add(bd)
      }
    }
  }

  const bridge2RoadTex = createRoadTexture(); bridge2RoadTex.repeat.set(1, 2)
  const bridge2DeckMat = new THREE.MeshStandardMaterial({ map: bridge2RoadTex, roughness: 0.3, metalness: 0.2, color: 0x555555 })
  const bridge2Geo = new THREE.BoxGeometry(bridgeWidth, bridgeHeight, 22)
  const bridge2 = new THREE.Mesh(bridge2Geo, bridge2DeckMat)
  bridge2.position.set(0, roadDepth + 8.5, 0); bridge2.castShadow = true; bridge2.receiveShadow = true; scene.add(bridge2)
  for (let s = -1; s <= 1; s += 2) {
    const supGeo = new THREE.BoxGeometry(0.5, 8.5, 0.5)
    const sup = new THREE.Mesh(supGeo, new THREE.MeshStandardMaterial({ color: 0x777777, roughness: 0.3, metalness: 0.3 }))
    sup.position.set(0, roadDepth + 4.25, s * 3); sup.castShadow = true; scene.add(sup)
  }
  for (let s = -1; s <= 1; s += 2) {
    const railGeo = new THREE.BoxGeometry(0.15, 1, 22)
    const rail = new THREE.Mesh(railGeo, new THREE.MeshStandardMaterial({ color: 0x999999, roughness: 0.2, metalness: 0.5 }))
    rail.position.set(s * (bridgeWidth / 2), roadDepth + 8.5 + 0.7, 0); rail.castShadow = true; scene.add(rail)
  }
  const bridge2LineY = roadDepth + 8.5 + bridgeHeight / 2 + 0.02
  for (let s = -1; s <= 1; s += 2) {
    const bl2Geo = new THREE.PlaneGeometry(0.35, 22); bl2Geo.rotateX(-Math.PI / 2)
    const bl2 = new THREE.Mesh(bl2Geo, depYellowMat); bl2.position.set(s * 0.25, bridge2LineY, 0); scene.add(bl2)
  }
  for (let q = -1; q <= 1; q += 2) {
    const dashCount = Math.floor(22 / 1.5)
    for (let d = 0; d < dashCount; d++) {
      if (d % 2 === 0) {
        const bd2Geo = new THREE.PlaneGeometry(0.15, 0.8); bd2Geo.rotateX(-Math.PI / 2)
        const bd2 = new THREE.Mesh(bd2Geo, new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.6 }))
        bd2.position.set(q * bridgeWidth * 0.25, bridge2LineY, -11 + d * 1.5 + 0.75); scene.add(bd2)
      }
    }
  }
}

// ==================== 水体与洪水 ====================
function buildWater() {
  const waterSegments = 60; const waterSize = roadWidth - 0.2
  waterGeo = new THREE.PlaneGeometry(waterSize, roadLength - 2, waterSegments, Math.floor(waterSegments * (roadLength - 2) / waterSize))
  waterGeo.rotateX(-Math.PI / 2)
  const waterCanvas = document.createElement('canvas'); waterCanvas.width = 256; waterCanvas.height = 256
  const wCtx = waterCanvas.getContext('2d')
  wCtx.fillStyle = '#8B7355'; wCtx.fillRect(0, 0, 256, 256)
  for (let i = 0; i < 1000; i++) {
    wCtx.fillStyle = `rgba(${120+Math.random()*40},${90+Math.random()*30},${40+Math.random()*20},0.4)`
    wCtx.fillRect(Math.random() * 256, Math.random() * 256, 2 + Math.random() * 6, 2 + Math.random() * 6)
  }
  const waterTex = new THREE.CanvasTexture(waterCanvas); waterTex.wrapS = waterTex.wrapT = THREE.RepeatWrapping
  waterTex.repeat.set(2, 6); waterTex.colorSpace = THREE.SRGBColorSpace
  waterMat = new THREE.MeshStandardMaterial({ map: waterTex, roughness: 0.08, metalness: 0.05, color: new THREE.Color('#8B6914'), opacity: 0.85, transparent: true })
  water = new THREE.Mesh(waterGeo, waterMat)
  water.position.y = roadDepth + 0.15; water.receiveShadow = true; scene.add(water)

  const drainGeo = new THREE.TorusGeometry(0.25, 0.08, 8, 16)
  const drainMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.1, metalness: 0.8 })
  drain = new THREE.Mesh(drainGeo, drainMat)
  drain.position.set(0, roadDepth + 0.05, roadLength / 2 - 2); drain.rotation.x = Math.PI / 2; scene.add(drain)
  const drainHoleGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.3, 16)
  drainHole = new THREE.Mesh(drainHoleGeo, new THREE.MeshStandardMaterial({ color: 0x000000 }))
  drainHole.position.set(0, roadDepth - 0.1, roadLength / 2 - 2); scene.add(drainHole)

  // Overflow water texture
  const overflowWaterCanvas = document.createElement('canvas'); overflowWaterCanvas.width = 256; overflowWaterCanvas.height = 256
  const owCtx = overflowWaterCanvas.getContext('2d')
  owCtx.fillStyle = '#0a2a5a'; owCtx.fillRect(0, 0, 256, 256)
  for (let i = 0; i < 800; i++) {
    const r = 5 + Math.random() * 25, g = 25 + Math.random() * 40, b = 80 + Math.random() * 50
    owCtx.fillStyle = `rgba(${r},${g},${b},0.5)`
    owCtx.fillRect(Math.random() * 256, Math.random() * 256, 2 + Math.random() * 8, 1 + Math.random() * 4)
  }
  owCtx.strokeStyle = 'rgba(120,160,220,0.15)'; owCtx.lineWidth = 1
  for (let i = 0; i < 40; i++) {
    owCtx.beginPath(); owCtx.moveTo(Math.random() * 256, Math.random() * 256)
    owCtx.lineTo(Math.random() * 256, Math.random() * 256 + 20); owCtx.stroke()
  }
  overflowWaterTex = new THREE.CanvasTexture(overflowWaterCanvas)
  overflowWaterTex.wrapS = overflowWaterTex.wrapT = THREE.RepeatWrapping
  overflowWaterTex.repeat.set(2, 6); overflowWaterTex.colorSpace = THREE.SRGBColorSpace

  function createOverflowWater(x, z, rotY, w, l, startY, endY, segs) {
    const geo = new THREE.PlaneGeometry(w, l, Math.max(8, segs), Math.max(16, Math.floor(segs * l / w)))
    geo.rotateX(-Math.PI / 2)
    const owTex = overflowWaterTex.clone(); owTex.needsUpdate = true
    owTex.wrapS = owTex.wrapT = THREE.RepeatWrapping; owTex.repeat.set(1, 4)
    const mat = new THREE.MeshStandardMaterial({ map: owTex, roughness: 0.06, metalness: 0.1, color: new THREE.Color('#0d3a7a'), opacity: 0.82, transparent: true })
    const mesh = new THREE.Mesh(geo, mat); mesh.position.set(x, 0.08, z); mesh.rotation.y = rotY
    mesh.receiveShadow = true; scene.add(mesh)
    const flowParticleCount = 40
    const fpGeo = new THREE.BufferGeometry()
    const fpPos = new Float32Array(flowParticleCount * 3)
    const fpProgress = []
    for (let i = 0; i < flowParticleCount; i++) {
      fpProgress.push(Math.random()); fpPos[i * 3] = (Math.random() - 0.5) * w * 0.8; fpPos[i * 3 + 1] = 0.09; fpPos[i * 3 + 2] = (Math.random() - 0.5) * l
    }
    fpGeo.setAttribute('position', new THREE.BufferAttribute(fpPos, 3))
    const fpMat = new THREE.PointsMaterial({ color: 0xaaeeff, size: 0.15, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false })
    const flowParticles = new THREE.Points(fpGeo, fpMat); flowParticles.position.set(x, 0, z); flowParticles.rotation.y = rotY; scene.add(flowParticles)
    overflowWaters.push({ mesh, geo, startY, endY, w, l, rotY, x, z, tex: owTex, flowParticles, fpGeo, fpProgress, fpMat })
    return mesh
  }
  createOverflowWater(0, roadLength / 2 + 9, 0, roadWidth - 0.3, 18, roadDepth + 3.8, 0.05, 16)
  createOverflowWater(0, -(roadLength / 2 + 9), 0, roadWidth - 0.3, 18, roadDepth + 3.8, 0.05, 16)
  createOverflowWater(roadLength / 2 + 9, 0, Math.PI / 2, roadWidth - 0.3, 18, roadDepth + 3.8, 0.05, 16)
  createOverflowWater(-(roadLength / 2 + 9), 0, Math.PI / 2, roadWidth - 0.3, 18, roadDepth + 3.8, 0.05, 16)

  // Flood water plane
  const floodSize = 75; const floodSegs = 80
  floodGeo = new THREE.PlaneGeometry(floodSize, floodSize, floodSegs, floodSegs); floodGeo.rotateX(-Math.PI / 2)
  floodTex = overflowWaterTex.clone(); floodTex.needsUpdate = true
  floodTex.wrapS = floodTex.wrapT = THREE.RepeatWrapping; floodTex.repeat.set(6, 6)
  const floodMat = new THREE.MeshStandardMaterial({ map: floodTex, roughness: 0.08, metalness: 0.1, color: new THREE.Color('#0d3a7a'), opacity: 0, transparent: true })
  floodWater = new THREE.Mesh(floodGeo, floodMat); floodWater.position.y = 0.3; floodWater.visible = false
  floodWater.receiveShadow = true; scene.add(floodWater)

  // Submerged cars
  function createLowPolyCar(x, z, rotY, colorHex) {
    const carGroup = new THREE.Group()
    const bodyGeo = new THREE.BoxGeometry(1.2, 0.5, 2.5)
    const bodyMat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.2, metalness: 0.5 })
    const body = new THREE.Mesh(bodyGeo, bodyMat); body.position.y = 0.35; carGroup.add(body)
    const cabinGeo = new THREE.BoxGeometry(1, 0.3, 1.2)
    const cabinMat = new THREE.MeshStandardMaterial({ color: 0x334455, roughness: 0.1, metalness: 0.3, opacity: 0.7, transparent: true })
    const cabin = new THREE.Mesh(cabinGeo, cabinMat); cabin.position.set(0, 0.65, -0.2); carGroup.add(cabin)
    for (let wx = -1; wx <= 1; wx += 2) {
      for (let wz = -1; wz <= 1; wz += 2) {
        const wheelGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.15, 8)
        const wheel = new THREE.Mesh(wheelGeo, new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.8 }))
        wheel.rotation.z = Math.PI / 2; wheel.position.set(wx * 0.55, 0.15, wz * 0.8); carGroup.add(wheel)
      }
    }
    const lightGeo = new THREE.BoxGeometry(0.1, 0.08, 0.05)
    const lightMat = new THREE.MeshStandardMaterial({ color: 0xff0000, roughness: 0.1, emissive: 0xff0000, emissiveIntensity: 0.5 })
    for (let wx = -1; wx <= 1; wx += 2) {
      const light = new THREE.Mesh(lightGeo, lightMat); light.position.set(wx * 0.4, 0.35, -1.27); carGroup.add(light)
    }
    carGroup.position.set(x, roadDepth + 0.25, z); carGroup.rotation.y = rotY
    carGroup.traverse(c => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } })
    scene.add(carGroup); return carGroup
  }
  createLowPolyCar(-1.2, -6, 0.3, '#cc3333')
  createLowPolyCar(1.0, -3, -0.2, '#3366aa')
  createLowPolyCar(-0.8, 4, 2.8, '#dddddd')
}

// ==================== 桥上行驶车辆 ====================
function buildCars() {
  function createDrivingCar(colorHex, hasHeadlights) {
    const carGroup = new THREE.Group()
    const bodyGeo = new THREE.BoxGeometry(1.1, 0.45, 2.3)
    const bodyMat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.15, metalness: 0.6 })
    const body = new THREE.Mesh(bodyGeo, bodyMat); body.position.y = 0.35; carGroup.add(body)
    const cabinGeo = new THREE.BoxGeometry(0.95, 0.32, 1.1)
    const cabinMat = new THREE.MeshStandardMaterial({ color: 0x223344, roughness: 0.05, metalness: 0.4, opacity: 0.65, transparent: true })
    const cabin = new THREE.Mesh(cabinGeo, cabinMat); cabin.position.set(0, 0.65, -0.1); carGroup.add(cabin)
    const wheels = []
    for (let wx = -1; wx <= 1; wx += 2) {
      for (let wz = -1; wz <= 1; wz += 2) {
        const wheelGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.15, 8)
        const wheel = new THREE.Mesh(wheelGeo, new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.8 }))
        wheel.rotation.z = Math.PI / 2; wheel.position.set(wx * 0.55, 0.15, wz * 0.8); carGroup.add(wheel); wheels.push(wheel)
      }
    }
    const tailLightMat = new THREE.MeshStandardMaterial({ color: 0xff0000, roughness: 0.1, emissive: 0xff0000, emissiveIntensity: 0.6 })
    for (let wx = -1; wx <= 1; wx += 2) {
      const light = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 0.05), tailLightMat)
      light.position.set(wx * 0.4, 0.35, -1.17); carGroup.add(light)
    }
    if (hasHeadlights) {
      const headLightMat = new THREE.MeshStandardMaterial({ color: 0xffffee, roughness: 0.1, emissive: 0xffffcc, emissiveIntensity: 0.8 })
      for (let wx = -1; wx <= 1; wx += 2) {
        const hl = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 0.05), headLightMat)
        hl.position.set(wx * 0.4, 0.35, 1.17); carGroup.add(hl)
      }
      const fwdLight = new THREE.PointLight(0xffffcc, 1.5, 6); fwdLight.position.set(0, 0.4, 1.5); carGroup.add(fwdLight)
    }
    carGroup.traverse(c => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } })
    scene.add(carGroup); return { group: carGroup, wheels }
  }

  const bridge1Y = roadDepth + 5.5 + 0.3
  const bridge2Y = roadDepth + 8.5 + 0.3
  const laneOffset = 1.2
  bridge1Cars = [
    { ...createDrivingCar('#cc4444', true),  speed: 2.5, x: -8,  dir: 1,  lane: -laneOffset },
    { ...createDrivingCar('#4488cc', false), speed: 3.0, x: 4,   dir: -1, lane:  laneOffset },
    { ...createDrivingCar('#ddaa22', true),  speed: 2.0, x: -2,  dir: 1,  lane: -laneOffset },
    { ...createDrivingCar('#ee8844', false), speed: 2.8, x: -5,  dir: -1, lane:  laneOffset },
  ]
  bridge1Cars.forEach(c => { c.group.position.set(c.x, bridge1Y, c.lane); c.group.rotation.y = c.dir > 0 ? -Math.PI / 2 : Math.PI / 2 })
  bridge2Cars = [
    { ...createDrivingCar('#44aa66', true),  speed: 2.8, z: -6,  dir: 1,  lane:  laneOffset },
    { ...createDrivingCar('#aa6644', false), speed: 2.2, z: 3,   dir: -1, lane: -laneOffset },
    { ...createDrivingCar('#6688dd', true),  speed: 3.2, z: -2,  dir: 1,  lane:  laneOffset },
  ]
  bridge2Cars.forEach(c => { c.group.position.set(c.lane, bridge2Y, c.z); c.group.rotation.y = c.dir > 0 ? 0 : Math.PI })
}

// ==================== 道路系统 ====================
function buildRoadSystem() {
  function createRoadSegment(x, z, rotY, w, l) {
    const geo = new THREE.PlaneGeometry(w, l); geo.rotateX(-Math.PI / 2)
    const rTex = createRoadTexture(); rTex.repeat.set(1, Math.floor(l / 4))
    const mat = new THREE.MeshStandardMaterial({ map: rTex, roughness: 0.3, metalness: 0.2, color: 0x3a3a3a })
    const road = new THREE.Mesh(geo, mat); road.position.set(x, 0.05, z); road.rotation.y = rotY
    road.receiveShadow = true; scene.add(road); return road
  }
  const rampLen = 4
  createRoadSegment(0, roadLength / 2 + rampLen + 14, 0, roadWidth, 28)
  createRoadSegment(0, -(roadLength / 2 + rampLen + 14), 0, roadWidth, 28)
  createRoadSegment(roadWidth / 2 + rampLen + 14, 0, Math.PI / 2, roadWidth, 28)
  createRoadSegment(-(roadWidth / 2 + rampLen + 14), 0, Math.PI / 2, roadWidth, 28)

  const markingMat = new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.6, metalness: 0.1 })
  function addLaneLines(x, z, rotY, roadW, roadL) {
    const group = new THREE.Group()
    const brightYellowMat = new THREE.MeshStandardMaterial({ color: 0xffee00, roughness: 0.3, metalness: 0.1, emissive: 0xffaa00, emissiveIntensity: 0.8 })
    for (let s = -1; s <= 1; s += 2) {
      const lineGeo = new THREE.PlaneGeometry(0.25, roadL); lineGeo.rotateX(-Math.PI / 2)
      const line = new THREE.Mesh(lineGeo, brightYellowMat); line.position.set(s * 0.2, 0.07, 0); group.add(line)
    }
    for (let q = -1; q <= 1; q += 2) {
      const dashCount = Math.floor(roadL / 1.5)
      for (let d = 0; d < dashCount; d++) {
        if (d % 2 === 0) {
          const dashGeo = new THREE.PlaneGeometry(0.15, 0.8); dashGeo.rotateX(-Math.PI / 2)
          const dash = new THREE.Mesh(dashGeo, markingMat)
          dash.position.set(q * roadW * 0.25, 0.07, -roadL / 2 + d * 1.5 + 0.75); group.add(dash)
        }
      }
    }
    for (let s = -1; s <= 1; s += 2) {
      const edgeGeo = new THREE.PlaneGeometry(0.1, roadL); edgeGeo.rotateX(-Math.PI / 2)
      const edge = new THREE.Mesh(edgeGeo, markingMat); edge.position.set(s * (roadW / 2 - 0.15), 0.06, 0); group.add(edge)
    }
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }
  addLaneLines(0, roadLength / 2 + rampLen + 14, 0, roadWidth, 28)
  addLaneLines(0, -(roadLength / 2 + rampLen + 14), 0, roadWidth, 28)
  addLaneLines(roadWidth / 2 + rampLen + 14, 0, Math.PI / 2, roadWidth, 28)
  addLaneLines(-(roadWidth / 2 + rampLen + 14), 0, Math.PI / 2, roadWidth, 28)
}

// ==================== 建筑生成 ====================
function buildBuildings() {
  buildingFacadeTex = createBuildingFacadeTexture()
  windowTex = createWindowTexture()
  rustTex = createRustTexture()
  buildingPositions = [
    { x: -13, z: -21, ry: 0.08, w: 3.2, d: 1.8, floors: 6 },
    { x: -9, z: -23.5, ry: -0.06, w: 3.6, d: 1.6, floors: 8 },
    { x: -5.5, z: -22, ry: 0.04, w: 2.8, d: 1.5, floors: 5 },
    { x: 5.5, z: -22.5, ry: 0.07, w: 3, d: 1.6, floors: 4 },
    { x: 9, z: -24, ry: -0.05, w: 3.8, d: 1.8, floors: 6 },
    { x: 13, z: -21.5, ry: 0.03, w: 3.2, d: 1.5, floors: 8 },
    { x: 17, z: -23.5, ry: -0.08, w: 3.5, d: 1.7, floors: 5 },
    { x: -14, z: 21, ry: Math.PI + 0.05, w: 3.4, d: 1.7, floors: 6 },
    { x: -9.5, z: 23.5, ry: Math.PI - 0.04, w: 3, d: 1.5, floors: 4 },
    { x: -5.5, z: 22, ry: Math.PI + 0.06, w: 3.8, d: 1.8, floors: 7 },
    { x: 5.5, z: 22.5, ry: Math.PI + 0.07, w: 3.5, d: 1.7, floors: 8 },
    { x: 9, z: 24, ry: Math.PI - 0.05, w: 2.8, d: 1.5, floors: 6 },
    { x: 13.5, z: 21.5, ry: Math.PI + 0.04, w: 4, d: 1.8, floors: 7 },
    { x: 18, z: 23.5, ry: Math.PI - 0.06, w: 3.3, d: 1.6, floors: 5 },
    { x: -21.5, z: -12, ry: Math.PI / 2 + 0.05, w: 4.2, d: 1.8, floors: 5 },
    { x: -23.5, z: -7, ry: Math.PI / 2 - 0.04, w: 3.5, d: 1.6, floors: 8 },
    { x: -21, z: 6, ry: Math.PI / 2 + 0.06, w: 3.8, d: 1.7, floors: 6 },
    { x: -24, z: 11, ry: Math.PI / 2 - 0.03, w: 3.2, d: 1.5, floors: 4 },
    { x: 21.5, z: -12, ry: -Math.PI / 2 - 0.05, w: 4, d: 1.8, floors: 7 },
    { x: 23.5, z: -7, ry: -Math.PI / 2 + 0.04, w: 3.4, d: 1.6, floors: 5 },
    { x: 21, z: 6, ry: -Math.PI / 2 - 0.06, w: 3.6, d: 1.7, floors: 8 },
    { x: 24, z: 11, ry: -Math.PI / 2 + 0.03, w: 3, d: 1.5, floors: 6 },
  ]
  function createBuilding(pos) {
    const group = new THREE.Group()
    const floors = pos.floors || 6; const floorHeight = 1.4; const totalH = floors * floorHeight
    const bw = pos.w, bd = pos.d
    const bodyGeo = new THREE.BoxGeometry(bw, totalH, bd)
    const bodyTex = buildingFacadeTex.clone(); bodyTex.repeat.set(bw, totalH / 2)
    const bodyMat = new THREE.MeshStandardMaterial({ map: bodyTex, roughness: 0.45, metalness: 0.08, color: 0xb8a890 })
    const body = new THREE.Mesh(bodyGeo, bodyMat); body.position.y = totalH / 2; body.castShadow = true; body.receiveShadow = true; group.add(body)
    const winTex = windowTex
    for (let f = 0; f < floors; f++) {
      const fy = 0.8 + f * floorHeight
      const winCount = Math.max(1, Math.floor(bw / 1.2)); const spacing = bw / (winCount + 1)
      for (let wi = 1; wi <= winCount; wi++) {
        const wGeo = new THREE.PlaneGeometry(0.45, 0.6)
        const wMat = new THREE.MeshStandardMaterial({ map: winTex, roughness: 0.3, metalness: 0.3 })
        const winFront = new THREE.Mesh(wGeo, wMat); winFront.position.set(-bw / 2 + wi * spacing, fy, bd / 2 + 0.01); winFront.castShadow = true; group.add(winFront)
        const winBack = new THREE.Mesh(wGeo.clone(), wMat); winBack.position.set(-bw / 2 + wi * spacing, fy, -bd / 2 - 0.01); winBack.rotation.y = Math.PI; winBack.castShadow = true; group.add(winBack)
      }
      const sideWinGeo = new THREE.PlaneGeometry(0.4, 0.55)
      const sideWinMat = new THREE.MeshStandardMaterial({ map: winTex, roughness: 0.3, metalness: 0.3 })
      for (let s = -1; s <= 1; s += 2) {
        const sWin = new THREE.Mesh(sideWinGeo, sideWinMat); sWin.position.set(s * (bw / 2 + 0.01), fy, 0); sWin.rotation.y = s > 0 ? Math.PI / 2 : -Math.PI / 2; sWin.castShadow = true; group.add(sWin)
      }
    }
    for (let f = 0; f < floors; f++) {
      const fy = 0.8 + f * floorHeight
      const winCount = Math.max(1, Math.floor(bw / 1.2)); const spacing = bw / (winCount + 1)
      for (let wi = 1; wi <= winCount; wi += 1 + Math.floor(Math.random() * 2)) {
        const barGeo = new THREE.TorusGeometry(0.28, 0.02, 4, 4)
        const bar = new THREE.Mesh(barGeo, new THREE.MeshStandardMaterial({ color: 0x8899aa, roughness: 0.3, metalness: 0.7 }))
        bar.position.set(-bw / 2 + wi * spacing, fy, bd / 2 + 0.05); bar.castShadow = true; group.add(bar)
      }
    }
    const signNames = ['五金建材', '快餐小吃', '便民超市', '修车铺', '药房', '理发店', '棋牌室', '水果店']
    const signColors = ['#ff4444', '#44ff44', '#4488ff', '#ffaa00', '#ff44ff', '#00ffcc', '#ff6644', '#ffdd00']
    for (let si = 0; si < Math.min(3, Math.floor(bw / 1.5)); si++) {
      const signName = signNames[Math.floor(Math.random() * signNames.length)]
      const signColor = signColors[Math.floor(Math.random() * signColors.length)]
      const signTex = createNeonSignTexture(signName, signColor)
      const signGeo = new THREE.PlaneGeometry(1.2, 0.35)
      const signMat = new THREE.MeshStandardMaterial({ map: signTex, roughness: 0.1, emissive: new THREE.Color(signColor), emissiveIntensity: 0.8 + Math.random() * 0.5, side: THREE.DoubleSide })
      const sign = new THREE.Mesh(signGeo, signMat); sign.position.set(-bw / 2 + 1 + si * 1.5, 1.2 + Math.random() * 0.3, bd / 2 + 0.15); group.add(sign)
      const signLight = new THREE.PointLight(new THREE.Color(signColor), 0.5, 3); signLight.position.copy(sign.position); signLight.position.z += 0.5; group.add(signLight)
      if (!group.userData.signLights) group.userData.signLights = []
      group.userData.signLights.push({ light: signLight, phase: Math.random() * Math.PI * 2, baseIntensity: 0.5 })
    }
    group.position.set(pos.x, 0, pos.z); group.rotation.y = pos.ry
    group.userData.signLights = group.userData.signLights || []
    scene.add(group); return group
  }
  buildings = buildingPositions.map(p => createBuilding(p))
}

// ==================== 社区设施 ====================
function buildCommunityFacilities() {
  function createShop(x, z, rotY, signText, signColor) {
    const group = new THREE.Group()
    const body = new THREE.Mesh(new THREE.BoxGeometry(3, 2.2, 2.5), new THREE.MeshStandardMaterial({ color: 0xdddddd, roughness: 0.4 }))
    body.position.y = 1.1; body.castShadow = true; body.receiveShadow = true; group.add(body)
    const roof = new THREE.Mesh(new THREE.BoxGeometry(3.3, 0.15, 2.8), new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.4 }))
    roof.position.y = 2.25; roof.castShadow = true; group.add(roof)
    const awning = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.08, 0.8), new THREE.MeshStandardMaterial({ color: 0xcc4422, roughness: 0.5 }))
    awning.position.set(0, 1.8, 1.5); awning.rotation.x = -0.2; group.add(awning)
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.7, 1.5, 0.05), new THREE.MeshStandardMaterial({ color: 0x336699, roughness: 0.3 }))
    door.position.set(0, 0.75, 1.28); group.add(door)
    const winMat = new THREE.MeshStandardMaterial({ color: 0x88ccdd, roughness: 0.1, emissive: 0x224455, emissiveIntensity: 0.3 })
    for (let wx = -1; wx <= 1; wx += 2) { const win = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.05), winMat); win.position.set(wx * 1.0, 1.1, 1.28); group.add(win) }
    const sc = document.createElement('canvas'); sc.width = 256; sc.height = 64
    const sctx = sc.getContext('2d')
    sctx.fillStyle = '#111'; sctx.fillRect(0, 0, 256, 64)
    sctx.shadowColor = signColor; sctx.shadowBlur = 12
    sctx.fillStyle = signColor; sctx.font = 'bold 28px "Microsoft YaHei"'; sctx.textAlign = 'center'
    sctx.fillText(signText, 128, 42)
    const stex = new THREE.CanvasTexture(sc); stex.colorSpace = THREE.SRGBColorSpace
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 0.6), new THREE.MeshStandardMaterial({ map: stex, emissive: new THREE.Color(signColor), emissiveIntensity: 0.7 }))
    sign.position.set(0, 2.4, 1.3); group.add(sign)
    const sLight = new THREE.PointLight(new THREE.Color(signColor), 0.8, 4); sLight.position.set(0, 2.4, 1.8); group.add(sLight)
    group.position.set(x, 0, z); group.rotation.y = rotY
    group.traverse(c => { if (c.isMesh) c.castShadow = true })
    scene.add(group); return group
  }
  function createClinic(x, z, rotY) {
    const group = new THREE.Group()
    const body = new THREE.Mesh(new THREE.BoxGeometry(3.5, 2.8, 3), new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.3 }))
    body.position.y = 1.4; body.castShadow = true; body.receiveShadow = true; group.add(body)
    const roof = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.2, 3.3), new THREE.MeshStandardMaterial({ color: 0xcc3333, roughness: 0.4 }))
    roof.position.y = 2.9; roof.castShadow = true; group.add(roof)
    const cc = document.createElement('canvas'); cc.width = 128; cc.height = 128
    const cctx = cc.getContext('2d')
    cctx.fillStyle = '#ffffff'; cctx.fillRect(0, 0, 128, 128)
    cctx.fillStyle = '#cc0000'; cctx.fillRect(48, 16, 32, 96); cctx.fillRect(16, 48, 96, 32)
    const ctex = new THREE.CanvasTexture(cc); ctex.colorSpace = THREE.SRGBColorSpace
    const cross = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.8), new THREE.MeshStandardMaterial({ map: ctex, emissive: 0x660000, emissiveIntensity: 0.3 }))
    cross.position.set(0, 2.5, 1.55); group.add(cross)
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.6, 0.05), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.3 }))
    door.position.set(0, 0.8, 1.53); group.add(door)
    const winMat = new THREE.MeshStandardMaterial({ color: 0xaaddff, roughness: 0.1, emissive: 0x446688, emissiveIntensity: 0.3 })
    for (let wx = -1; wx <= 1; wx += 2) { const win = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.9, 0.05), winMat); win.position.set(wx * 1.2, 1.3, 1.53); group.add(win) }
    const tc = document.createElement('canvas'); tc.width = 256; tc.height = 48
    const tctx = tc.getContext('2d')
    tctx.fillStyle = '#cc0000'; tctx.fillRect(0, 0, 256, 48)
    tctx.fillStyle = '#ffffff'; tctx.font = 'bold 28px "Microsoft YaHei"'; tctx.textAlign = 'center'
    tctx.fillText('社区卫生站', 128, 34)
    const ttex = new THREE.CanvasTexture(tc); ttex.colorSpace = THREE.SRGBColorSpace
    const tSign = new THREE.Mesh(new THREE.PlaneGeometry(2, 0.4), new THREE.MeshStandardMaterial({ map: ttex, emissive: 0x440000, emissiveIntensity: 0.3 }))
    tSign.position.set(0, 2.1, 1.56); group.add(tSign)
    group.position.set(x, 0, z); group.rotation.y = rotY
    group.traverse(c => { if (c.isMesh) c.castShadow = true })
    scene.add(group); return group
  }
  function createPlayground(x, z, rotY) {
    const group = new THREE.Group()
    const slideMat = new THREE.MeshStandardMaterial({ color: 0xff6600, roughness: 0.3, metalness: 0.4 })
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x4488cc, roughness: 0.3, metalness: 0.5 })
    const plat = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.1, 0.8), slideMat); plat.position.set(0, 1.2, 0); group.add(plat)
    const ramp = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.05, 1.5), slideMat); ramp.position.set(0, 0.6, 0.8); ramp.rotation.x = 0.5; group.add(ramp)
    for (let i = 0; i < 3; i++) { const rung = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.7, 6), frameMat); rung.position.set(0, 0.3 + i * 0.4, -0.4 - i * 0.1); rung.rotation.z = Math.PI / 2; group.add(rung) }
    for (let s = -1; s <= 1; s += 2) { const side = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.5, 0.05), frameMat); side.position.set(s * 0.35, 0.75, -0.5); group.add(side) }
    const swingMat = new THREE.MeshStandardMaterial({ color: 0x44aa44, roughness: 0.3, metalness: 0.4 })
    for (let sx = -1; sx <= 1; sx += 2) { for (let sz = -1; sz <= 1; sz += 2) { const post = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2, 0.06), swingMat); post.position.set(sx * 0.8, 1, sz * 0.4); post.rotation.z = sx * 0.15; group.add(post) } }
    const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.8, 8), swingMat); bar.rotation.z = Math.PI / 2; bar.position.set(0, 2, 0); group.add(bar)
    for (let sx = -1; sx <= 1; sx += 2) { const seat = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.04, 0.15), new THREE.MeshStandardMaterial({ color: 0x222222 })); seat.position.set(sx * 0.4, 0.8, 0); group.add(seat) }
    const benchMat = new THREE.MeshStandardMaterial({ color: 0x8a6a4a, roughness: 0.6 })
    const bSeat = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.08, 0.35), benchMat); bSeat.position.set(1.8, 0.4, 0); group.add(bSeat)
    const bBack = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.4, 0.06), benchMat); bBack.position.set(1.8, 0.6, -0.15); bBack.rotation.x = 0.1; group.add(bBack)
    for (let bx = -1; bx <= 1; bx += 2) { const leg = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.4, 0.3), benchMat); leg.position.set(1.8 + bx * 0.5, 0.2, 0); group.add(leg) }
    group.traverse(c => { if (c.isMesh) c.castShadow = true })
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }
  createShop(-7, 18, 0, '便民小卖部', '#44ff44')
  createShop(7, -18, Math.PI, '社区超市', '#ffdd44')
  createClinic(-18, -7, 0.3)
  createPlayground(10, 18, 0)
  createPlayground(-10, -18, Math.PI)
}

// ==================== 郊区别墅 ====================
function buildVillas() {
  function createVilla(x, z, rotY, wallColor, roofColor) {
    const group = new THREE.Group()
    const found = new THREE.Mesh(new THREE.BoxGeometry(3.3, 0.2, 2.8), new THREE.MeshStandardMaterial({ color: 0x888877, roughness: 0.8 }))
    found.position.y = 0.1; found.castShadow = true; found.receiveShadow = true; group.add(found)
    const body = new THREE.Mesh(new THREE.BoxGeometry(3, 2.5, 2.5), new THREE.MeshStandardMaterial({ color: wallColor, roughness: 0.5, metalness: 0.05 }))
    body.position.y = 1.35; body.castShadow = true; body.receiveShadow = true; group.add(body)
    const trim = new THREE.Mesh(new THREE.BoxGeometry(3.05, 0.3, 2.55), new THREE.MeshStandardMaterial({ color: 0xaaaaaa, roughness: 0.5 })); trim.position.y = 0.35; group.add(trim)
    const roof = new THREE.Mesh(new THREE.ConeGeometry(2.4, 1.6, 4), new THREE.MeshStandardMaterial({ color: roofColor, roughness: 0.6, metalness: 0.05 }))
    roof.position.y = 3.45; roof.rotation.y = Math.PI / 4; roof.scale.set(1.3, 1, 1.0); roof.castShadow = true; group.add(roof)
    const eave = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.15, 2.9), new THREE.MeshStandardMaterial({ color: roofColor, roughness: 0.5 })); eave.position.y = 2.65; eave.castShadow = true; group.add(eave)
    const doorFrameMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4 })
    const doorFrame = new THREE.Mesh(new THREE.BoxGeometry(0.65, 1.15, 0.06), doorFrameMat); doorFrame.position.set(0, 0.85, 1.27); group.add(doorFrame)
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.0, 0.05), new THREE.MeshStandardMaterial({ color: 0x5a3a1a, roughness: 0.5 })); door.position.set(0, 0.8, 1.29); group.add(door)
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 6), new THREE.MeshStandardMaterial({ color: 0xddaa00, metalness: 0.7, roughness: 0.3 })); knob.position.set(0.12, 0.8, 1.32); group.add(knob)
    const canopy = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.08, 0.3), new THREE.MeshStandardMaterial({ color: roofColor, roughness: 0.5 })); canopy.position.set(0, 1.4, 1.4); canopy.rotation.x = -0.2; group.add(canopy)
    const winMat = new THREE.MeshStandardMaterial({ color: 0x88ccdd, roughness: 0.1, metalness: 0.3, emissive: 0x224455, emissiveIntensity: 0.15 })
    const shutterMat = new THREE.MeshStandardMaterial({ color: 0x5a3a1a, roughness: 0.5 })
    for (let wx = -1; wx <= 1; wx += 2) {
      const win = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.6, 0.05), winMat); win.position.set(wx * 0.9, 1.5, 1.28); group.add(win)
      const frame = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.67, 0.03), doorFrameMat); frame.position.set(wx * 0.9, 1.5, 1.26); group.add(frame)
      for (let s = -1; s <= 1; s += 2) { const shutter = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.6, 0.04), shutterMat); shutter.position.set(wx * 0.9 + s * 0.36, 1.5, 1.28); group.add(shutter) }
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.1, 0.12), shutterMat); box.position.set(wx * 0.9, 1.18, 1.35); group.add(box)
      const bColors = [0xff4444, 0xffdd00, 0xff66aa]
      for (let fb = 0; fb < 3; fb++) { const bFlower = new THREE.Mesh(new THREE.IcosahedronGeometry(0.05, 0), new THREE.MeshStandardMaterial({ color: bColors[fb], emissive: bColors[fb], emissiveIntensity: 0.15 })); bFlower.position.set(wx * 0.9 - 0.15 + fb * 0.15, 1.25, 1.38); group.add(bFlower) }
    }
    for (let s = -1; s <= 1; s += 2) { const sw = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.5, 0.5), winMat); sw.position.set(s * 1.52, 1.5, 0); group.add(sw) }
    const atticWin = new THREE.Mesh(new THREE.CircleGeometry(0.25, 16), winMat); atticWin.position.set(0, 2.4, 1.26); group.add(atticWin)
    const chimney = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.0, 0.3), new THREE.MeshStandardMaterial({ color: 0x8a4a2a, roughness: 0.7 })); chimney.position.set(0.8, 3.6, 0); chimney.castShadow = true; group.add(chimney)
    const cap = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.08, 0.4), new THREE.MeshStandardMaterial({ color: 0x5a3a1a, roughness: 0.6 })); cap.position.set(0.8, 4.1, 0); group.add(cap)
    const fenceMat = new THREE.MeshStandardMaterial({ color: 0xddccaa, roughness: 0.5 })
    for (let fx = -1.8; fx <= 1.8; fx += 0.45) { const postH = Math.abs(fx) < 0.3 ? 0 : 0.55; if (postH > 0) { const post = new THREE.Mesh(new THREE.BoxGeometry(0.06, postH, 0.06), fenceMat); post.position.set(fx, 0.2 + postH / 2, 1.7); group.add(post) } }
    for (let gx = -1; gx <= 1; gx += 2) { const gatePost = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.8, 0.1), fenceMat); gatePost.position.set(gx * 0.3, 0.4, 1.7); group.add(gatePost) }
    const lawnGeo = new THREE.PlaneGeometry(3.5, 0.8); lawnGeo.rotateX(-Math.PI / 2)
    const lawn = new THREE.Mesh(lawnGeo, new THREE.MeshStandardMaterial({ color: 0x4a7a3a, roughness: 0.8 })); lawn.position.set(0, 0.02, 2.2); group.add(lawn)
    const bushMat = new THREE.MeshStandardMaterial({ color: 0x3a6a2a, roughness: 0.8 })
    for (let bx = -1.5; bx <= 1.5; bx += 0.7) { const bush = new THREE.Mesh(new THREE.IcosahedronGeometry(0.2, 0), bushMat); bush.position.set(bx, 0.2, 2.3); bush.scale.set(1, 0.7, 1); group.add(bush) }
    const gColors = [0xff4444, 0xffdd00, 0xff66aa, 0xaa66ff]
    for (let fx = -1.2; fx <= 1.2; fx += 0.3) { const fc = gColors[Math.floor(Math.random() * 4)]; const f = new THREE.Mesh(new THREE.IcosahedronGeometry(0.05, 0), new THREE.MeshStandardMaterial({ color: fc, emissive: fc, emissiveIntensity: 0.15, roughness: 0.4 })); f.position.set(fx + (Math.random() - 0.5) * 0.2, 0.12, 2.0 + Math.random() * 0.4); group.add(f) }
    const stepMat = new THREE.MeshStandardMaterial({ color: 0xbbbbaa, roughness: 0.7 })
    for (let i = 0; i < 3; i++) { const step = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.04, 0.3), stepMat); step.position.set((i - 1) * 0.3, 0.02, 1.9 + i * 0.4); group.add(step) }
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }
  createVilla(-28, -8, 0.3, 0xeeddbb, 0x884422)
  createVilla(28, 10, -0.5, 0xddeeee, 0x445566)
  createVilla(-10, 28, Math.PI + 0.2, 0xffe8cc, 0xcc6633)
  createVilla(12, -28, 0.1, 0xe8d8c8, 0x556633)
  createVilla(-30, 12, Math.PI / 2 - 0.2, 0xd8e8d8, 0x664422)
}

// ==================== 凉亭 ====================
function buildPavilions() {
  function createPavilion(x, z, rotY, pillarColor, roofColor) {
    const group = new THREE.Group()
    const base = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.3, 3.5), new THREE.MeshStandardMaterial({ color: 0x999988, roughness: 0.7, metalness: 0.05 }))
    base.position.y = 0.15; base.castShadow = true; base.receiveShadow = true; group.add(base)
    const pillarMat = new THREE.MeshStandardMaterial({ color: pillarColor, roughness: 0.4, metalness: 0.1 })
    for (let px = -1; px <= 1; px += 2) { for (let pz = -1; pz <= 1; pz += 2) { const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 2.5, 8), pillarMat); pillar.position.set(px * 1.3, 1.55, pz * 1.3); pillar.castShadow = true; group.add(pillar) } }
    const beamGeo = new THREE.BoxGeometry(3.2, 0.15, 0.15)
    const beamMat = new THREE.MeshStandardMaterial({ color: pillarColor, roughness: 0.4 })
    for (let s = -1; s <= 1; s += 2) { const beam1 = new THREE.Mesh(beamGeo, beamMat); beam1.position.set(0, 2.75, s * 1.5); group.add(beam1); const beam2 = new THREE.Mesh(beamGeo.clone(), beamMat); beam2.position.set(s * 1.5, 2.75, 0); beam2.rotation.y = Math.PI / 2; group.add(beam2) }
    const roofMat = new THREE.MeshStandardMaterial({ color: roofColor, roughness: 0.5, metalness: 0.05, side: THREE.DoubleSide })
    const eave = new THREE.Mesh(new THREE.ConeGeometry(2.8, 0.6, 8), roofMat); eave.position.y = 3.1; eave.rotation.y = Math.PI / 8; eave.scale.set(1, 0.6, 1); eave.castShadow = true; group.add(eave)
    const mid = new THREE.Mesh(new THREE.ConeGeometry(2.0, 0.5, 8), roofMat); mid.position.y = 3.5; mid.rotation.y = Math.PI / 8; mid.scale.set(1, 0.7, 1); mid.castShadow = true; group.add(mid)
    const top = new THREE.Mesh(new THREE.ConeGeometry(1.0, 0.8, 8), roofMat); top.position.y = 3.9; top.rotation.y = Math.PI / 8; top.castShadow = true; group.add(top)
    const finial = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), new THREE.MeshStandardMaterial({ color: 0xddaa00, metalness: 0.6, roughness: 0.3 })); finial.position.y = 4.4; group.add(finial)
    const seatMat = new THREE.MeshStandardMaterial({ color: 0xaaaabb, roughness: 0.6 })
    for (let s = -1; s <= 1; s += 2) { const seat = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.12, 0.3), seatMat); seat.position.set(0, 0.45, s * 1.0); seat.castShadow = true; group.add(seat) }
    const stepMat = new THREE.MeshStandardMaterial({ color: 0xbbbbaa, roughness: 0.7 })
    for (let i = 0; i < 3; i++) { const step = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.08, 0.3), stepMat); step.position.set(0, 0.04, 2.0 + i * 0.5); group.add(step) }
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }
  createPavilion(-31, -25, 0.5, 0x8a4a2a, 0x665544)
  createPavilion(31, 25, Math.PI - 0.3, 0x4a5a4a, 0x445566)
  createPavilion(-33, 12, 0.3, 0x6a4a3a, 0x884422)
}

// ==================== 池塘 ====================
function buildPonds() {
  function createPond(x, z, radius) {
    const group = new THREE.Group()
    const pondGeo = new THREE.CircleGeometry(radius, 32); pondGeo.rotateX(-Math.PI / 2)
    const pondMat = new THREE.MeshStandardMaterial({ color: 0x2a6699, roughness: 0.03, metalness: 0.3, transparent: true, opacity: 0.8 })
    const pondWater = new THREE.Mesh(pondGeo, pondMat); pondWater.position.y = 0.05; pondWater.name = 'pond'; group.add(pondWater)
    const stoneEdge = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.15, 8, 32), new THREE.MeshStandardMaterial({ color: 0x778877, roughness: 0.8 }))
    stoneEdge.position.y = 0.06; stoneEdge.rotation.x = Math.PI / 2; stoneEdge.castShadow = true; group.add(stoneEdge)
    const stoneMat = new THREE.MeshStandardMaterial({ color: 0x778877, roughness: 0.8 })
    for (let i = 0; i < 12; i++) { const ang = (i / 12) * Math.PI * 2; const sr = radius + 0.1 + Math.random() * 0.15; const stone = new THREE.Mesh(new THREE.IcosahedronGeometry(0.12 + Math.random() * 0.08, 0), stoneMat); stone.position.set(Math.cos(ang) * sr, 0.08, Math.sin(ang) * sr); stone.scale.set(1, 0.6, 1); stone.castShadow = true; group.add(stone) }
    const lilyMat = new THREE.MeshStandardMaterial({ color: 0x3a7a2a, roughness: 0.6 })
    for (let i = 0; i < 5; i++) { const ang = Math.random() * Math.PI * 2; const r = Math.random() * radius * 0.6; const lilyGeo = new THREE.CircleGeometry(0.15 + Math.random() * 0.1, 8); lilyGeo.rotateX(-Math.PI / 2); const lily = new THREE.Mesh(lilyGeo, lilyMat); lily.position.set(Math.cos(ang) * r, 0.06, Math.sin(ang) * r); group.add(lily); if (Math.random() > 0.5) { const lilyFlower = new THREE.Mesh(new THREE.IcosahedronGeometry(0.05, 0), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xff8888, emissiveIntensity: 0.2 })); lilyFlower.position.set(Math.cos(ang) * r, 0.1, Math.sin(ang) * r); group.add(lilyFlower) } }
    const reedMat = new THREE.MeshStandardMaterial({ color: 0x5a8a3a, roughness: 0.7 })
    for (let i = 0; i < 15; i++) { const ang = Math.random() * Math.PI * 2; const r = radius + 0.2 + Math.random() * 0.3; const reed = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.02, 0.5 + Math.random() * 0.4, 4), reedMat); reed.position.set(Math.cos(ang) * r, 0.25 + Math.random() * 0.1, Math.sin(ang) * r); reed.rotation.z = (Math.random() - 0.5) * 0.2; group.add(reed); const cattail = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.12, 6), new THREE.MeshStandardMaterial({ color: 0x6a4a2a })); cattail.position.set(Math.cos(ang) * r, 0.5 + Math.random() * 0.2, Math.sin(ang) * r); group.add(cattail) }
    const pondGrassMat = new THREE.MeshStandardMaterial({ color: 0x4a8a3a, roughness: 0.9 })
    for (let i = 0; i < 20; i++) { const ang = Math.random() * Math.PI * 2; const r = radius + 0.4 + Math.random() * 0.5; const g = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.15 + Math.random() * 0.1, 4), pondGrassMat); g.position.set(Math.cos(ang) * r, 0.08, Math.sin(ang) * r); g.rotation.z = (Math.random() - 0.5) * 0.3; group.add(g) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  createPond(-33, -28, 2.0)
  createPond(33, 28, 2.2)
}

// ==================== 自然景观 ====================
function buildLandscape() {
  function createTree(x, z, scale, type) {
    const group = new THREE.Group()
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5a3a2a, roughness: 0.8 })
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08 * scale, 0.15 * scale, 1.2 * scale, 6), trunkMat); trunk.position.y = 0.6 * scale; trunk.castShadow = true; group.add(trunk)
    if (type === 0) {
      const canopyColors = [0x2d6a2d, 0x3a7a3a, 0x4a8a3a, 0x356a35]
      const canopyMat = new THREE.MeshStandardMaterial({ color: canopyColors[Math.floor(Math.random() * 4)], roughness: 0.7 })
      for (let i = 0; i < 3; i++) { const ball = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5 * scale, 0), canopyMat); ball.position.set((Math.random() - 0.5) * 0.4 * scale, (1.2 + i * 0.3) * scale, (Math.random() - 0.5) * 0.4 * scale); ball.castShadow = true; group.add(ball) }
    } else if (type === 1) {
      const pineMat = new THREE.MeshStandardMaterial({ color: 0x2a5a2a, roughness: 0.7 })
      for (let i = 0; i < 3; i++) { const cone = new THREE.Mesh(new THREE.ConeGeometry((0.6 - i * 0.12) * scale, 0.7 * scale, 7), pineMat); cone.position.y = (1.0 + i * 0.4) * scale; cone.castShadow = true; group.add(cone) }
    } else if (type === 2) {
      const bushMat = new THREE.MeshStandardMaterial({ color: 0x4a7a3a, roughness: 0.8 })
      const bush = new THREE.Mesh(new THREE.IcosahedronGeometry(0.6 * scale, 0), bushMat); bush.position.y = 1.0 * scale; bush.castShadow = true; group.add(bush)
      const bush2 = new THREE.Mesh(new THREE.IcosahedronGeometry(0.6 * scale, 0), bushMat); bush2.position.set(0.3 * scale, 0.9 * scale, 0.2 * scale); bush2.scale.set(0.7, 0.7, 0.7); group.add(bush2)
    }
    if (type === 3) {
      const bigCanopyMat = new THREE.MeshStandardMaterial({ color: 0x1a4a1a, roughness: 0.6 })
      const tallTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12 * scale, 0.2 * scale, 2.0 * scale, 7), trunkMat); tallTrunk.position.y = 1.0 * scale; tallTrunk.castShadow = true; group.add(tallTrunk)
      for (let i = 0; i < 5; i++) { const ball = new THREE.Mesh(new THREE.IcosahedronGeometry((0.7 - i * 0.08) * scale, 0), bigCanopyMat); ball.position.set((Math.random() - 0.5) * 0.6 * scale, (1.8 + i * 0.35) * scale, (Math.random() - 0.5) * 0.6 * scale); ball.castShadow = true; group.add(ball) }
      const flowerColors = [0xff66aa, 0xffdd44, 0xff8844]
      for (let f = 0; f < 8; f++) { const fc = flowerColors[f % 3]; const flower = new THREE.Mesh(new THREE.IcosahedronGeometry(0.06 * scale, 0), new THREE.MeshStandardMaterial({ color: fc, emissive: fc, emissiveIntensity: 0.15, roughness: 0.5 })); const ang = (f / 8) * Math.PI * 2; flower.position.set(Math.cos(ang) * 0.5 * scale, 1.8 * scale + Math.random() * 0.5 * scale, Math.sin(ang) * 0.5 * scale); group.add(flower) }
    }
    if (type === 4) {
      const greenCanopyMat = new THREE.MeshStandardMaterial({ color: 0x2a6a2a, roughness: 0.6 })
      const tallTrunk2 = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * scale, 0.18 * scale, 1.8 * scale, 7), trunkMat); tallTrunk2.position.y = 0.9 * scale; tallTrunk2.castShadow = true; group.add(tallTrunk2)
      for (let i = 0; i < 5; i++) { const ball = new THREE.Mesh(new THREE.IcosahedronGeometry((0.65 - i * 0.06) * scale, 0), greenCanopyMat); ball.position.set((Math.random() - 0.5) * 0.5 * scale, (1.6 + i * 0.3) * scale, (Math.random() - 0.5) * 0.5 * scale); ball.castShadow = true; group.add(ball) }
      const treeFlowerColors = [0xff4444, 0xffffff, 0xffdd44, 0xff8844, 0xff66aa]
      for (let f = 0; f < 20; f++) { const fc = treeFlowerColors[f % 5]; const flower = new THREE.Mesh(new THREE.IcosahedronGeometry(0.07 * scale, 0), new THREE.MeshStandardMaterial({ color: fc, emissive: fc, emissiveIntensity: 0.25, roughness: 0.4 })); const ang = (f / 20) * Math.PI * 2; const r = 0.3 + Math.random() * 0.3; flower.position.set(Math.cos(ang) * r * scale, (1.5 + Math.random() * 1.2) * scale, Math.sin(ang) * r * scale); group.add(flower) }
    }
    group.position.set(x, 0, z); group.rotation.y = Math.random() * Math.PI; scene.add(group); return group
  }
  function createBush(x, z, scale) {
    const group = new THREE.Group()
    const bushMat = new THREE.MeshStandardMaterial({ color: 0x3a6a2a, roughness: 0.8 })
    for (let i = 0; i < 3; i++) { const b = new THREE.Mesh(new THREE.IcosahedronGeometry(0.3 * scale, 0), bushMat); b.position.set((Math.random() - 0.5) * 0.4, 0.2 * scale + Math.random() * 0.1, (Math.random() - 0.5) * 0.4); b.scale.set(0.8 + Math.random() * 0.4, 0.6 + Math.random() * 0.3, 0.8 + Math.random() * 0.4); b.castShadow = true; group.add(b) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  function createFlowerPatch(x, z, radius) {
    const group = new THREE.Group()
    const flowerColors = [0xff4444, 0xffdd00, 0xff66aa, 0xaa66ff, 0xffffff, 0xff8844]
    const count = Math.floor(8 + Math.random() * 12)
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2; const r = Math.random() * radius
      const fx = Math.cos(angle) * r, fz = Math.sin(angle) * r
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.12, 4), new THREE.MeshStandardMaterial({ color: 0x3a6a2a })); stem.position.set(fx, 0.06, fz); group.add(stem)
      const headColor = flowerColors[Math.floor(Math.random() * flowerColors.length)]
      const head = new THREE.Mesh(new THREE.IcosahedronGeometry(0.04, 0), new THREE.MeshStandardMaterial({ color: headColor, emissive: headColor, emissiveIntensity: 0.2 })); head.position.set(fx, 0.14, fz); group.add(head)
    }
    const grassMat = new THREE.MeshStandardMaterial({ color: 0x4a7a3a, roughness: 0.9 })
    for (let i = 0; i < 15; i++) { const angle = Math.random() * Math.PI * 2; const r = Math.random() * radius * 1.3; const grass = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.1 + Math.random() * 0.08, 4), grassMat); grass.position.set(Math.cos(angle) * r, 0.05, Math.sin(angle) * r); grass.rotation.z = (Math.random() - 0.5) * 0.3; group.add(grass) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  function createGrassTuft(x, z) {
    const group = new THREE.Group()
    const grassMat = new THREE.MeshStandardMaterial({ color: 0x5a8a3a, roughness: 0.9 })
    for (let i = 0; i < 5; i++) { const g = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.15 + Math.random() * 0.1, 4), grassMat); g.position.set((Math.random() - 0.5) * 0.2, 0.07, (Math.random() - 0.5) * 0.2); g.rotation.z = (Math.random() - 0.5) * 0.4; group.add(g) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  function createPuddle(x, z, radius) {
    const group = new THREE.Group()
    const puddleGeo = new THREE.CircleGeometry(radius, 24); puddleGeo.rotateX(-Math.PI / 2)
    const puddleMat = new THREE.MeshStandardMaterial({ color: 0x1a5599, roughness: 0.03, metalness: 0.3, transparent: true, opacity: 0.8 })
    const puddle = new THREE.Mesh(puddleGeo, puddleMat); puddle.position.y = 0.04; puddle.name = 'puddle'; group.add(puddle)
    const mudGeo = new THREE.RingGeometry(radius, radius + 0.25, 24); mudGeo.rotateX(-Math.PI / 2)
    const mud = new THREE.Mesh(mudGeo, new THREE.MeshStandardMaterial({ color: 0x5a4a2a, roughness: 0.9 })); mud.position.y = 0.035; group.add(mud)
    const dirtGeo = new THREE.RingGeometry(radius * 0.95, radius, 24); dirtGeo.rotateX(-Math.PI / 2)
    const dirt = new THREE.Mesh(dirtGeo, new THREE.MeshStandardMaterial({ color: 0x3a2a1a, roughness: 0.8 })); dirt.position.y = 0.038; group.add(dirt)
    const grassMat = new THREE.MeshStandardMaterial({ color: 0x4a8a3a, roughness: 0.9 })
    const grassCount = Math.floor(12 + radius * 15)
    for (let i = 0; i < grassCount; i++) { const ang = Math.random() * Math.PI * 2; const r = radius + 0.15 + Math.random() * 0.5; const blade = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.15 + Math.random() * 0.12, 4), grassMat); blade.position.set(Math.cos(ang) * r, 0.08, Math.sin(ang) * r); blade.rotation.z = (Math.random() - 0.5) * 0.4; blade.rotation.x = (Math.random() - 0.5) * 0.3; group.add(blade) }
    const pebbleMat = new THREE.MeshStandardMaterial({ color: 0x888877, roughness: 0.7 })
    for (let i = 0; i < 6; i++) { const ang = Math.random() * Math.PI * 2; const r = radius + 0.08; const pebble = new THREE.Mesh(new THREE.IcosahedronGeometry(0.05 + Math.random() * 0.04, 0), pebbleMat); pebble.position.set(Math.cos(ang) * r, 0.04, Math.sin(ang) * r); group.add(pebble) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  function createGrassLawn(x, z, size) {
    const geo = new THREE.PlaneGeometry(size, size); geo.rotateX(-Math.PI / 2)
    const lawnCanvas = document.createElement('canvas'); lawnCanvas.width = 128; lawnCanvas.height = 128
    const lCtx = lawnCanvas.getContext('2d')
    lCtx.fillStyle = '#4a7a3a'; lCtx.fillRect(0, 0, 128, 128)
    for (let i = 0; i < 300; i++) { lCtx.fillStyle = `rgba(${60+Math.random()*40},${100+Math.random()*50},${40+Math.random()*30},0.6)`; lCtx.fillRect(Math.random() * 128, Math.random() * 128, 2 + Math.random() * 4, 1 + Math.random() * 3) }
    const lawnTex = new THREE.CanvasTexture(lawnCanvas); lawnTex.wrapS = lawnTex.wrapT = THREE.RepeatWrapping; lawnTex.repeat.set(2, 2)
    const lawn = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: lawnTex, roughness: 0.8, metalness: 0, color: 0x5a8a3a, transparent: true, opacity: 0.75 }))
    lawn.position.set(x, 0.02, z); lawn.rotation.y = Math.random() * Math.PI; lawn.receiveShadow = true; scene.add(lawn); return lawn
  }

  const treePositions = []
  let treeAttempts = 0
  while (treePositions.length < 120 && treeAttempts < 800) {
    treeAttempts++
    const x = (Math.random() - 0.5) * 78; const z = (Math.random() - 0.5) * 78
    const dist = Math.sqrt(x * x + z * z)
    if (dist < 22 || dist > 38) continue
    if (Math.abs(x) < 5 && Math.abs(z) > 15) continue
    if (Math.abs(z) < 5 && Math.abs(x) > 15) continue
    let tooClose = false
    for (const bp of buildingPositions) { if (Math.sqrt((x - bp.x) ** 2 + (z - bp.z) ** 2) < 3.5) { tooClose = true; break } }
    if (tooClose) continue
    for (const tp of treePositions) { if (Math.sqrt((x - tp.x) ** 2 + (z - tp.z) ** 2) < 1.5) { tooClose = true; break } }
    if (tooClose) continue
    treePositions.push({ x, z })
  }
  treePositions.forEach(p => { const r = Math.random(); let type; if (r < 0.45) type = Math.floor(Math.random() * 3); else if (r < 0.75) type = 3; else type = 4; createTree(p.x, p.z, type === 3 ? 1.2 + Math.random() * 0.8 : 0.6 + Math.random() * 1.2, type) })

  for (let i = 0; i < 70; i++) { const angle = Math.random() * Math.PI * 2; const r = 22 + Math.random() * 16; const x = Math.cos(angle) * r; const z = Math.sin(angle) * r; if (Math.abs(x) < 5 && Math.abs(z) > 15) continue; if (Math.abs(z) < 5 && Math.abs(x) > 15) continue; createBush(x, z, 0.4 + Math.random() * 0.7) }

  const flowerPatches = [
    { x: -20, z: -20 }, { x: 20, z: -20 }, { x: -20, z: 20 }, { x: 20, z: 20 },
    { x: -28, z: 0 }, { x: 28, z: 0 }, { x: 0, z: -28 }, { x: 0, z: 28 },
    { x: -25, z: -10 }, { x: 25, z: 10 }, { x: -15, z: 25 }, { x: 15, z: -25 },
    { x: -30, z: -15 }, { x: 30, z: 15 }, { x: -10, z: -30 }, { x: 10, z: 30 },
    { x: -32, z: 10 }, { x: 32, z: -10 }, { x: -18, z: 30 }, { x: 18, z: -30 },
    { x: -35, z: -5 }, { x: 35, z: 5 }, { x: 5, z: -35 }, { x: -5, z: 35 },
  ]
  flowerPatches.forEach(p => createFlowerPatch(p.x, p.z, 1.0 + Math.random() * 1.0))

  for (let i = 0; i < 80; i++) { const angle = Math.random() * Math.PI * 2; const r = 22 + Math.random() * 15; const x = Math.cos(angle) * r; const z = Math.sin(angle) * r; if (Math.abs(x) < 5 && Math.abs(z) > 15) continue; if (Math.abs(z) < 5 && Math.abs(x) > 15) continue; createGrassLawn(x, z, 6 + Math.random() * 5) }
  for (let i = 0; i < 120; i++) { const angle = Math.random() * Math.PI * 2; const r = 16 + Math.random() * 22; const x = Math.cos(angle) * r; const z = Math.sin(angle) * r; if (Math.abs(x) < 5 && Math.abs(z) > 15) continue; if (Math.abs(z) < 5 && Math.abs(x) > 15) continue; createGrassTuft(x, z) }

  const puddlePositions = []
  let puddleAttempts = 0
  while (puddlePositions.length < 15 && puddleAttempts < 200) {
    puddleAttempts++
    const angle = Math.random() * Math.PI * 2; const r = 18 + Math.random() * 18
    const x = Math.cos(angle) * r; const z = Math.sin(angle) * r
    if (Math.abs(x) < 5 && Math.abs(z) > 15) continue; if (Math.abs(z) < 5 && Math.abs(x) > 15) continue
    let tooClose = false
    for (const bp of buildingPositions) { if (Math.sqrt((x - bp.x) ** 2 + (z - bp.z) ** 2) < 4) { tooClose = true; break } }
    if (tooClose) continue
    puddlePositions.push({ x, z })
  }
  puddlePositions.forEach(p => createPuddle(p.x, p.z, 0.6 + Math.random() * 0.8))

  for (let i = 0; i < 30; i++) { const angle = Math.random() * Math.PI * 2; const r = 22 + Math.random() * 14; const x = Math.cos(angle) * r; const z = Math.sin(angle) * r; if (Math.abs(x) < 5 && Math.abs(z) > 15) continue; if (Math.abs(z) < 5 && Math.abs(x) > 15) continue; createFlowerPatch(x, z, 0.6 + Math.random() * 0.8) }
}

// ==================== 街道设施 ====================
function buildStreetFurniture() {
  function createUtilityPole(x, z, leanAngle) {
    const group = new THREE.Group()
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.4, metalness: 0.3 })
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 8, 8), poleMat); pole.position.y = 4; pole.castShadow = true; group.add(pole)
    for (let a = 0; a < 2; a++) { const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.06, 0.06), poleMat); arm.position.y = 7 - a * 0.6; arm.castShadow = true; group.add(arm) }
    const transformer = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.5), new THREE.MeshStandardMaterial({ map: rustTex, roughness: 0.7, metalness: 0.4, color: 0x6a4a3a })); transformer.position.set(0.6, 2.5, 0); transformer.castShadow = true; group.add(transformer)
    for (let w = -1; w <= 1; w += 2) { const wire = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 15, 4), new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.5 })); wire.rotation.z = Math.PI / 2; wire.position.set(0, 7.5, w * 0.6); group.add(wire) }
    group.position.set(x, 0, z); group.rotation.z = leanAngle || (Math.random() - 0.5) * 0.3; group.rotation.y = Math.random() * Math.PI; scene.add(group); return group
  }
  createUtilityPole(-15, -18, 0.15); createUtilityPole(15, -18, -0.1); createUtilityPole(-18, 10, 0.12); createUtilityPole(18, 10, -0.08)

  function createTrafficLight(x, z, rotY) {
    const group = new THREE.Group()
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 5, 8), new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.3, metalness: 0.4 })); pole.position.y = 2.5; pole.castShadow = true; group.add(pole)
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.9, 0.2), new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.2 })); box.position.y = 5.2; group.add(box)
    const colors = [0xff0000, 0xffaa00, 0x00ff00]
    for (let i = 0; i < 3; i++) { const lMat = new THREE.MeshStandardMaterial({ color: colors[i], roughness: 0.1, emissive: colors[i], emissiveIntensity: 0.3 }); const light = new THREE.Mesh(new THREE.CircleGeometry(0.1, 8), lMat); light.position.set(0.12, 5.55 - i * 0.25, 0); light.name = 'trafficLight_' + i; group.add(light) }
    group.position.set(x, 0, z); group.rotation.y = rotY || 0; scene.add(group); return group
  }
  trafficLight = createTrafficLight(-5, -20, 0)
  trafficLight2 = createTrafficLight(5, 20, Math.PI)

  function createStreetLamp(x, z) {
    const group = new THREE.Group()
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.1, 7, 8), new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.3, metalness: 0.5 })); pole.position.y = 3.5; pole.castShadow = true; group.add(pole)
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.05, 0.05), new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.3, metalness: 0.4 })); arm.position.set(0.6, 6.8, 0); arm.castShadow = true; group.add(arm)
    const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.25, 0.4, 8), new THREE.MeshStandardMaterial({ color: 0xffdd88, roughness: 0.1, emissive: 0xffaa44, emissiveIntensity: 0.6 })); lamp.position.set(1.3, 6.6, 0); group.add(lamp)
    const lampLight = new THREE.PointLight(0xffcc66, 3, 12); lampLight.position.set(1.3, 6.4, 0); group.add(lampLight)
    group.position.set(x, 0, z); scene.add(group); return group
  }
  createStreetLamp(-10, -17); createStreetLamp(10, -17); createStreetLamp(-10, 17); createStreetLamp(10, 17)

  function createDeadTree(x, z) {
    const group = new THREE.Group()
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a3a2a, roughness: 0.8 })
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.2, 4, 8), trunkMat); trunk.position.y = 2; trunk.castShadow = true; group.add(trunk)
    for (let i = 0; i < 6; i++) { const branch = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.06, 1.5 + Math.random() * 1.5, 6), trunkMat); branch.position.y = 2.5 + Math.random() * 1.5; branch.rotation.z = (Math.random() - 0.5) * 2; branch.rotation.x = (Math.random() - 0.5) * 2; branch.castShadow = true; group.add(branch); for (let j = 0; j < 2; j++) { const sub = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.03, 0.8 + Math.random(), 5), trunkMat); sub.position.set((Math.random() - 0.5) * 0.8, branch.position.y + 0.5, (Math.random() - 0.5) * 0.8); sub.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI); sub.castShadow = true; group.add(sub) } }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  createDeadTree(-23, -17)

  function createTrashPile(x, z) {
    const group = new THREE.Group()
    const sofa = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.5, 0.8), new THREE.MeshStandardMaterial({ color: 0x5a4a3a, roughness: 0.9 })); sofa.position.y = 0.25; sofa.castShadow = true; group.add(sofa)
    for (let i = 0; i < 2; i++) { const cush = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.25, 0.6), new THREE.MeshStandardMaterial({ color: 0x4a6a3a, roughness: 0.9 })); cush.position.set((i - 0.5) * 0.5, 0.6, 0); cush.rotation.z = 0.3; cush.castShadow = true; group.add(cush) }
    for (let i = 0; i < 8; i++) { const brick = new THREE.Mesh(new THREE.BoxGeometry(0.2 + Math.random() * 0.15, 0.08 + Math.random() * 0.05, 0.1 + Math.random() * 0.1), new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(0.05 + Math.random() * 0.05, 0.5 + Math.random() * 0.3, 0.3 + Math.random() * 0.2), roughness: 0.9 })); brick.position.set((Math.random() - 0.5) * 1.5, 0.05 + Math.random() * 0.1, (Math.random() - 0.5)); brick.rotation.set(Math.random() * 0.5, Math.random() * Math.PI, Math.random() * 0.5); brick.castShadow = true; group.add(brick) }
    group.position.set(x, 0, z); scene.add(group); return group
  }
  createTrashPile(-23, -15)

  function createWarningWall(x, z, rotY) {
    const group = new THREE.Group()
    const wall = new THREE.Mesh(new THREE.BoxGeometry(3, 2.5, 0.3), new THREE.MeshStandardMaterial({ color: 0x999999, roughness: 0.5 })); wall.position.y = 1.25; wall.castShadow = true; wall.receiveShadow = true; group.add(wall)
    const signTex = createWarningSignTexture()
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 2.2), new THREE.MeshStandardMaterial({ map: signTex, roughness: 0.3, side: THREE.DoubleSide })); sign.position.set(0, 1.3, 0.16); group.add(sign)
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }
  createWarningWall(-20, -22.5, Math.PI / 4)
  createWarningWall(20, 21.5, -Math.PI * 3 / 4)
}

// ==================== 传感器设备 ====================
function buildSensors() {
  function createSensorBox(x, y, z, rotY, rotX) {
    const group = new THREE.Group()
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.2, 0.15), new THREE.MeshStandardMaterial({ color: 0xff6622, roughness: 0.2, metalness: 0.6, emissive: 0x331100, emissiveIntensity: 0.2 })); box.castShadow = true; group.add(box)
    const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.3, 6), new THREE.MeshStandardMaterial({ color: 0xcccccc, roughness: 0.2, metalness: 0.8 })); ant.position.y = 0.25; group.add(ant)
    for (let led = -1; led <= 1; led += 2) { const ledColor = led > 0 ? 0x0044ff : 0xff0000; const ledMesh = new THREE.Mesh(new THREE.SphereGeometry(0.02, 6, 6), new THREE.MeshStandardMaterial({ color: ledColor, roughness: 0.1, emissive: ledColor, emissiveIntensity: 1.5 })); ledMesh.position.set(led * 0.08, 0.06, 0.08); ledMesh.name = 'led_' + (led > 0 ? 'blue' : 'red'); group.add(ledMesh) }
    const ledLight = new THREE.PointLight(0x0044ff, 0.2, 0.5); ledLight.position.set(0.08, 0.06, 0.08); group.add(ledLight)
    group.position.set(x, y, z); group.rotation.set(rotX || 0, rotY || 0, 0); scene.add(group); return group
  }
  createSensorBox(-2.1, -3.5, roadLength / 2 + 0.3, 0, 0)
  createSensorBox(2.1, -3.5, roadLength / 2 + 0.3, 0, 0)
  createSensorBox(-roadWidth / 2 - 0.3, -3.5, 3, Math.PI / 2, 0)
  createSensorBox(roadWidth / 2 + 0.3, -3.5, -3, -Math.PI / 2, 0)
  createSensorBox(-8, 2, -23, 0.1, 0.05)
  createSensorBox(8, 2.5, -22.5, -0.1, -0.03)
  createSensorBox(-21.5, 1.5, 2, Math.PI / 2, 0.1)
  createSensorBox(21, 3, -4, -Math.PI / 2, -0.05)

  // Weather sensor
  function createWeatherSensor(x, z) {
    const group = new THREE.Group()
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.3, metalness: 0.6 })
    const deviceMat = new THREE.MeshStandardMaterial({ color: 0xff6622, roughness: 0.2, metalness: 0.6 })
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 4, 8), poleMat); pole.position.y = 2; pole.castShadow = true; group.add(pole)
    const vaneMat = new THREE.MeshStandardMaterial({ color: 0xcc2222, roughness: 0.2, metalness: 0.5 })
    const vaneBody = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.04, 0.1), vaneMat); vaneBody.position.y = 4.1; group.add(vaneBody)
    const vaneTail = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.04), vaneMat); vaneTail.position.set(-0.5, 4.1, 0); group.add(vaneTail)
    const vaneTip = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.2, 6), vaneMat); vaneTip.position.set(0.6, 4.1, 0); vaneTip.rotation.z = -Math.PI / 2; group.add(vaneTip)
    const cupMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.3 })
    const cupArmMat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.3, metalness: 0.5 })
    const anemoGroup = new THREE.Group(); anemoGroup.position.y = 3.7
    for (let i = 0; i < 3; i++) { const ang = (i / 3) * Math.PI * 2; const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.4, 4), cupArmMat); arm.position.set(Math.cos(ang) * 0.2, 0, Math.sin(ang) * 0.2); arm.rotation.z = Math.PI / 2; arm.rotation.y = -ang; anemoGroup.add(arm); const cup = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6, 0, Math.PI), cupMat); cup.position.set(Math.cos(ang) * 0.4, 0, Math.sin(ang) * 0.4); anemoGroup.add(cup) }
    group.add(anemoGroup)
    const tempBox = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.25, 0.2), deviceMat); tempBox.position.set(0, 3.2, 0.15); tempBox.castShadow = true; group.add(tempBox)
    const finMat = new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.4 })
    for (let f = 0; f < 5; f++) { const fin = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.03, 12), finMat); fin.position.set(0, 2.5 + f * 0.12, 0); group.add(fin) }
    const panelMat = new THREE.MeshStandardMaterial({ color: 0x223366, roughness: 0.2, metalness: 0.7 })
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.03, 0.35), panelMat); panel.position.set(0, 3.5, 0); panel.rotation.x = -0.3; group.add(panel)
    const ledBlue = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 8), new THREE.MeshStandardMaterial({ color: 0x00aaff, emissive: 0x00aaff, emissiveIntensity: 1.5 })); ledBlue.position.set(0.1, 3.2, 0.26); ledBlue.name = 'weatherLed_blue'; group.add(ledBlue)
    const ledRed = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 8), new THREE.MeshStandardMaterial({ color: 0xff0000, emissive: 0xff0000, emissiveIntensity: 1.5 })); ledRed.position.set(-0.1, 3.2, 0.26); ledRed.name = 'weatherLed_red'; group.add(ledRed)
    const lc = document.createElement('canvas'); lc.width = 128; lc.height = 48
    const lctx = lc.getContext('2d')
    lctx.fillStyle = '#ff6622'; lctx.fillRect(0, 0, 128, 48)
    lctx.fillStyle = '#fff'; lctx.font = 'bold 18px "Microsoft YaHei"'; lctx.textAlign = 'center'; lctx.fillText('气象站', 64, 30)
    const ltex = new THREE.CanvasTexture(lc); ltex.colorSpace = THREE.SRGBColorSpace
    const label = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.15), new THREE.MeshStandardMaterial({ map: ltex, emissive: 0x331100, emissiveIntensity: 0.3 })); label.position.set(0, 3.05, 0.27); group.add(label)
    group.userData.anemoGroup = anemoGroup; group.userData.vaneBody = vaneBody; group.userData.ledBlue = ledBlue; group.userData.ledRed = ledRed
    group.position.set(x, 0, z); scene.add(group); return group
  }

  // Soil sensor
  function createSoilSensor(x, z) {
    const group = new THREE.Group()
    const S = 0.6
    const deviceMat = new THREE.MeshStandardMaterial({ color: 0xff6622, roughness: 0.2, metalness: 0.6 })
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.35 * S, 0.2 * S, 0.25 * S), deviceMat); box.position.y = 0.1 * S; box.castShadow = true; group.add(box)
    const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.01 * S, 0.01 * S, 0.4 * S, 6), new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.8 })); ant.position.y = 0.4 * S; group.add(ant)
    const probeMat = new THREE.MeshStandardMaterial({ color: 0xaa8800, roughness: 0.3, metalness: 0.7 })
    for (let p = -1; p <= 1; p += 2) { const probe = new THREE.Mesh(new THREE.CylinderGeometry(0.015 * S, 0.015 * S, 0.6 * S, 6), probeMat); probe.position.set(p * 0.08 * S, -0.2 * S, 0.1 * S); group.add(probe) }
    const panelMat = new THREE.MeshStandardMaterial({ color: 0x223366, roughness: 0.2, metalness: 0.7 })
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.3 * S, 0.02 * S, 0.2 * S), panelMat); panel.position.set(0, 0.25 * S, -0.05 * S); panel.rotation.x = -0.3; group.add(panel)
    const led = new THREE.Mesh(new THREE.SphereGeometry(0.025 * S, 8, 8), new THREE.MeshStandardMaterial({ color: 0x00ff00, emissive: 0x00ff00, emissiveIntensity: 1.5 })); led.position.set(0.12 * S, 0.1 * S, 0.13 * S); led.name = 'soilLed'; group.add(led)
    const lc = document.createElement('canvas'); lc.width = 128; lc.height = 48
    const lctx = lc.getContext('2d')
    lctx.fillStyle = '#ff6622'; lctx.fillRect(0, 0, 128, 48)
    lctx.fillStyle = '#fff'; lctx.font = 'bold 16px "Microsoft YaHei"'; lctx.textAlign = 'center'; lctx.fillText('土壤监测', 64, 30)
    const ltex = new THREE.CanvasTexture(lc); ltex.colorSpace = THREE.SRGBColorSpace
    const label = new THREE.Mesh(new THREE.PlaneGeometry(0.35 * S, 0.13 * S), new THREE.MeshStandardMaterial({ map: ltex, emissive: 0x331100, emissiveIntensity: 0.3 })); label.position.set(0, 0.1 * S, 0.14 * S); group.add(label)
    const mound = new THREE.Mesh(new THREE.SphereGeometry(0.3 * S, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x6a4a2a, roughness: 0.9 })); mound.position.y = 0; mound.scale.set(1.2, 0.3, 1.2); group.add(mound)
    group.userData.led = led; group.position.set(x, 0, z); scene.add(group); return group
  }

  // Sensor signpost
  function createSensorSign(x, z, rotY, title, subtitle, accentColor) {
    const group = new THREE.Group()
    const postMat = new THREE.MeshStandardMaterial({ color: 0x666666, roughness: 0.4, metalness: 0.5 })
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 3.0, 8), postMat); post.position.y = 1.5; post.castShadow = true; group.add(post)
    const sc = document.createElement('canvas'); sc.width = 256; sc.height = 192
    const sctx = sc.getContext('2d')
    const bgGrad = sctx.createLinearGradient(0, 0, 0, 192); bgGrad.addColorStop(0, '#1a1a2a'); bgGrad.addColorStop(1, '#0d0d18')
    sctx.fillStyle = bgGrad; sctx.fillRect(0, 0, 256, 192)
    sctx.strokeStyle = accentColor; sctx.lineWidth = 6; sctx.strokeRect(4, 4, 248, 184)
    sctx.fillStyle = accentColor; sctx.fillRect(4, 4, 248, 8)
    sctx.fillStyle = accentColor; sctx.beginPath(); sctx.arc(128, 52, 24, 0, Math.PI * 2); sctx.fill()
    sctx.fillStyle = '#fff'; sctx.font = 'bold 28px "Microsoft YaHei"'; sctx.textAlign = 'center'; sctx.textBaseline = 'middle'; sctx.fillText('◉', 128, 54)
    sctx.fillStyle = '#fff'; sctx.font = 'bold 26px "Microsoft YaHei"'; sctx.textAlign = 'center'; sctx.textBaseline = 'middle'; sctx.fillText(title, 128, 110)
    sctx.fillStyle = '#aabbcc'; sctx.font = '16px "Microsoft YaHei"'; sctx.fillText(subtitle, 128, 150)
    sctx.fillStyle = accentColor; sctx.fillRect(60, 174, 136, 3)
    const stex = new THREE.CanvasTexture(sc); stex.colorSpace = THREE.SRGBColorSpace
    const boardMat = new THREE.MeshStandardMaterial({ map: stex, roughness: 0.4, metalness: 0.2, emissive: 0x110800, emissiveIntensity: 0.5, side: THREE.DoubleSide })
    const board = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.05), boardMat); board.position.set(0, 2.4, 0.06); board.castShadow = true; group.add(board)
    const back = new THREE.Mesh(new THREE.BoxGeometry(1.46, 1.1, 0.04), new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.5, metalness: 0.3 })); back.position.set(0, 2.4, 0.03); group.add(back)
    const led = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), new THREE.MeshStandardMaterial({ color: 0xffaa00, emissive: 0xff6600, emissiveIntensity: 1.5 })); led.position.set(0, 3.0, 0); led.name = 'signLed'; group.add(led)
    group.userData.signLed = led
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.3, 0.1, 8), new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.6, metalness: 0.3 })); base.position.y = 0.05; group.add(base)
    group.position.set(x, 0, z); group.rotation.y = rotY; scene.add(group); return group
  }

  weatherSensor = createWeatherSensor(6, 40)
  soilSensor = createSoilSensor(-6, -40)
  weatherSign = createSensorSign(5.5, 43, -0.8, '气象站', '风速·风向·温湿度', '#22aaff')
  soilSign = createSensorSign(-5.5, -43, 0.8 + Math.PI, '土壤监测', '含水率·位移·温度', '#ff6622')
}

// ==================== 应急排水泵 ====================
function buildWaterPump() {
  function createWaterPump(x, y, z, rotY) {
    const group = new THREE.Group()
    const S = 2.5
    const steelMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.4, metalness: 0.6 })
    const base = new THREE.Mesh(new THREE.BoxGeometry(2.2 * S, 0.2 * S, 1.6 * S), steelMat); base.position.y = 0.1 * S; base.castShadow = true; base.receiveShadow = true; group.add(base)
    const pump = new THREE.Mesh(new THREE.CylinderGeometry(0.55 * S, 0.65 * S, 1.2 * S, 16), new THREE.MeshStandardMaterial({ color: 0xffcc00, roughness: 0.3, metalness: 0.4 })); pump.position.set(-0.3 * S, 0.8 * S, 0); pump.castShadow = true; pump.receiveShadow = true; group.add(pump)
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.6 * S, 0.55 * S, 0.2 * S, 16), new THREE.MeshStandardMaterial({ color: 0xddaa00, roughness: 0.3, metalness: 0.5 })); cap.position.set(-0.3 * S, 1.5 * S, 0); cap.castShadow = true; group.add(cap)
    const motor = new THREE.Mesh(new THREE.BoxGeometry(0.8 * S, 0.7 * S, 0.9 * S), new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.5, metalness: 0.5 })); motor.position.set(0.5 * S, 0.8 * S, 0); motor.castShadow = true; group.add(motor)
    for (let f = 0; f < 5; f++) { const fin = new THREE.Mesh(new THREE.BoxGeometry(0.85 * S, 0.04 * S, 0.04 * S), new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.5, metalness: 0.5 })); fin.position.set(0.5 * S, 0.55 * S + f * 0.13 * S, 0); group.add(fin) }
    const intakeCurve = new THREE.CatmullRomCurve3([ new THREE.Vector3(-0.3 * S, 0.8 * S, 0.6 * S), new THREE.Vector3(-0.5 * S, 0.4 * S, 0.9 * S), new THREE.Vector3(-0.6 * S, 0.0 * S, 1.2 * S), new THREE.Vector3(-0.7 * S, -1.0 * S, 1.8 * S) ])
    const intakeHose = new THREE.Mesh(new THREE.TubeGeometry(intakeCurve, 20, 0.15 * S, 12, false), new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.6, metalness: 0.2 })); intakeHose.castShadow = true; group.add(intakeHose)
    const dischargeCurve = new THREE.CatmullRomCurve3([ new THREE.Vector3(0.5 * S, 0.8 * S, 0), new THREE.Vector3(0.9 * S, 0.5 * S, 0), new THREE.Vector3(1.2 * S, 0.2 * S, 0.3 * S), new THREE.Vector3(1.4 * S, -0.3 * S, 0.5 * S) ])
    const dischargePipe = new THREE.Mesh(new THREE.TubeGeometry(dischargeCurve, 20, 0.15 * S, 12, false), new THREE.MeshStandardMaterial({ color: 0xffcc00, roughness: 0.3, metalness: 0.4 })); dischargePipe.castShadow = true; group.add(dischargePipe)
    const manhole = new THREE.Mesh(new THREE.CylinderGeometry(0.5 * S, 0.5 * S, 0.3 * S, 16), new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.5, metalness: 0.4 })); manhole.position.set(1.4 * S, -0.15 * S, 0.5 * S); manhole.castShadow = true; manhole.receiveShadow = true; group.add(manhole)
    const cover = new THREE.Mesh(new THREE.CylinderGeometry(0.45 * S, 0.45 * S, 0.08 * S, 16), new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.4, metalness: 0.5 })); cover.position.set(1.4 * S + 0.2 * S, 0.04 * S, 0.5 * S); cover.rotation.z = 0.15; cover.castShadow = true; group.add(cover)
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.4 * S, 0.35 * S, 0.12 * S), new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.3, metalness: 0.5 })); panel.position.set(0.5 * S, 1.3 * S, 0.55 * S); group.add(panel)
    const ledColors = [0x00ff00, 0xff8800, 0xff0000]
    const pumpLeds = []
    for (let l = 0; l < 3; l++) { const led = new THREE.Mesh(new THREE.SphereGeometry(0.04 * S, 8, 8), new THREE.MeshStandardMaterial({ color: ledColors[l], roughness: 0.1, emissive: ledColors[l], emissiveIntensity: 2.0 })); led.position.set(0.38 * S + l * 0.06 * S, 1.38 * S, 0.62 * S); led.name = 'pumpLed_' + l; group.add(led); pumpLeds.push(led) }
    for (let s = 0; s < 3; s++) { const stripe = new THREE.Mesh(new THREE.TorusGeometry(0.57 * S, 0.04 * S, 6, 16), new THREE.MeshStandardMaterial({ color: s % 2 === 0 ? 0xff0000 : 0xffffff, roughness: 0.3 })); stripe.position.set(-0.3 * S, 0.5 * S + s * 0.35 * S, 0); stripe.rotation.x = Math.PI / 2; group.add(stripe) }
    const labelCanvas = document.createElement('canvas'); labelCanvas.width = 256; labelCanvas.height = 128
    const lCtx = labelCanvas.getContext('2d')
    lCtx.fillStyle = '#ffcc00'; lCtx.fillRect(0, 0, 256, 128)
    lCtx.strokeStyle = '#000000'; lCtx.lineWidth = 4; lCtx.strokeRect(4, 4, 248, 120)
    lCtx.fillStyle = '#000000'; lCtx.font = 'bold 32px "Microsoft YaHei"'; lCtx.textAlign = 'center'; lCtx.fillText('应急排水泵', 128, 48)
    lCtx.font = 'bold 20px "Microsoft YaHei"'; lCtx.fillText('路面积水 → 水库', 128, 80)
    lCtx.font = 'bold 16px Arial'; lCtx.fillText('DRAINAGE  PUMP', 128, 108)
    const labelTex = new THREE.CanvasTexture(labelCanvas); labelTex.colorSpace = THREE.SRGBColorSpace
    const label = new THREE.Mesh(new THREE.PlaneGeometry(1.0 * S, 0.5 * S), new THREE.MeshStandardMaterial({ map: labelTex, roughness: 0.4, emissive: 0x441111, emissiveIntensity: 0.3 })); label.position.set(0.5 * S, 0.8 * S, -0.48 * S); label.rotation.y = Math.PI; group.add(label)
    const workLight = new THREE.PointLight(0xffaa44, 3.0, 12); workLight.position.set(0, 2 * S, 0); group.add(workLight)
    group.position.set(x, y, z); group.rotation.y = rotY; scene.add(group)
    return { group, pumpLeds, workLight, pump, motor, scale: S }
  }
  waterPump = createWaterPump(2.5, roadDepth + 0.5, 8, -0.6)

  // Flow particles
  flowCount = 80
  flowGeo = new THREE.BufferGeometry()
  const flowPos = new Float32Array(flowCount * 3)
  for (let i = 0; i < flowCount; i++) {
    const t = i / flowCount
    flowPos[i * 3] = -0.7 * waterPump.scale + (0.7 - (-0.3)) * waterPump.scale * t
    flowPos[i * 3 + 1] = (-1.0 + (0.8 - (-1.0)) * t) * waterPump.scale
    flowPos[i * 3 + 2] = (1.8 - (1.8 - 0.6) * t) * waterPump.scale
  }
  flowGeo.setAttribute('position', new THREE.BufferAttribute(flowPos, 3))
  flowMat = new THREE.PointsMaterial({ color: 0x44aaff, size: 0.25, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false })
  flowParticles = new THREE.Points(flowGeo, flowMat); waterPump.group.add(flowParticles)
}

// ==================== 雨粒子 ====================
function buildRain() {
  const rainCount = 12000
  rainGeo = new THREE.BufferGeometry()
  const rainPositions = new Float32Array(rainCount * 6)
  const rainArea = 50; const rainHeight = 35
  for (let i = 0; i < rainCount; i++) {
    const i6 = i * 6
    const x = (Math.random() - 0.5) * rainArea; const y = Math.random() * rainHeight; const z = (Math.random() - 0.5) * rainArea
    const dropLen = 0.25 + Math.random() * 0.5; const angle = -0.15
    rainPositions[i6] = x; rainPositions[i6 + 1] = y; rainPositions[i6 + 2] = z
    rainPositions[i6 + 3] = x + Math.sin(angle) * dropLen; rainPositions[i6 + 4] = y - dropLen; rainPositions[i6 + 5] = z
  }
  rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3))
  rainMat = new THREE.LineBasicMaterial({ color: 0x99aadd, transparent: true, opacity: 0.22 })
  rain = new THREE.LineSegments(rainGeo, rainMat); rain.position.y = 5; scene.add(rain)
}

// ==================== 雾气 ====================
function buildMist() {
  const mistCount = 2000
  mistGeo = new THREE.BufferGeometry()
  const mistPositions = new Float32Array(mistCount * 3)
  for (let i = 0; i < mistCount * 3; i += 3) {
    mistPositions[i] = (Math.random() - 0.5) * 18
    mistPositions[i + 1] = roadDepth + Math.random() * 2
    mistPositions[i + 2] = (Math.random() - 0.5) * 30
  }
  mistGeo.setAttribute('position', new THREE.BufferAttribute(mistPositions, 3))
  const mistSpriteTex = (() => {
    const c = document.createElement('canvas'); c.width = 32; c.height = 32
    const ctx = c.getContext('2d')
    const g = ctx.createRadialGradient(16, 16, 0, 16, 16, 16)
    g.addColorStop(0, 'rgba(200,200,220,0.4)'); g.addColorStop(0.5, 'rgba(150,150,180,0.15)'); g.addColorStop(1, 'rgba(100,100,120,0)')
    ctx.fillStyle = g; ctx.fillRect(0, 0, 32, 32)
    return new THREE.CanvasTexture(c)
  })()
  mistMat = new THREE.PointsMaterial({ map: mistSpriteTex, size: 2, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false })
  mist = new THREE.Points(mistGeo, mistMat); scene.add(mist)
}

// ==================== 入口水花 ====================
function buildInletSplash() {
  inletSplashCount = 60
  inletSplashGeo = new THREE.BufferGeometry()
  const inletSplashPos = new Float32Array(inletSplashCount * 3)
  inletSplashVel = []
  inletPositions = [
    { x: 0, z: roadLength / 2, dir: 'north' },
    { x: 0, z: -roadLength / 2, dir: 'south' },
    { x: roadWidth / 2, z: 0, dir: 'east' },
    { x: -roadWidth / 2, z: 0, dir: 'west' },
  ]
  for (let i = 0; i < inletSplashCount; i++) {
    const inlet = inletPositions[i % 4]
    inletSplashPos[i * 3] = inlet.x + (Math.random() - 0.5) * 0.5
    inletSplashPos[i * 3 + 1] = roadDepth + 0.5 + Math.random() * 0.5
    inletSplashPos[i * 3 + 2] = inlet.z + (Math.random() - 0.5) * 0.5
    inletSplashVel.push({ vx: (inlet.x === 0 ? (Math.random() - 0.5) * 0.3 : -Math.sign(inlet.x) * (0.5 + Math.random() * 0.5)), vy: 0.5 + Math.random() * 1.0, vz: (inlet.z === 0 ? (Math.random() - 0.5) * 0.3 : -Math.sign(inlet.z) * (0.5 + Math.random() * 0.5)), inletIdx: i % 4 })
  }
  inletSplashGeo.setAttribute('position', new THREE.BufferAttribute(inletSplashPos, 3))
  inletSplashMat = new THREE.PointsMaterial({ color: 0x66bbff, size: 0.12, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false })
  inletSplash = new THREE.Points(inletSplashGeo, inletSplashMat); scene.add(inletSplash)
}

// ==================== 演示排水控制 ====================
function setDemoStatus(text) {
  // 3D场景内部状态追踪（不再有独立DOM显示，由App.vue进度条展示）
}
function setWaterDepth(text, cls) {
  store.water_depth_text = text
  store.water_depth_cls = cls || ''
}

function startDemo(fastPump) {
  if (demoActive.value) return
  overflowLevel = 1.0; pitLevel = 1.0
  // fastPump=true → 跳过积水流入阶段，直接开始抽水
  _demoPhase = fastPump ? 2 : 1
  water.visible = true; drain.visible = true; drainHole.visible = true; mist.visible = true
  mist.material.opacity = 0.3; water.position.y = roadDepth + 0.15; water.material.opacity = 0.85
  overflowWaters.forEach(ow => { ow.mesh.visible = true; ow.mesh.material.opacity = 0.82; ow.mesh.position.y = 0.08; ow.flowParticles.visible = true; ow.fpMat.opacity = 0.7 })
  demoActive.value = true
  setDemoStatus(fastPump ? '应急排水泵启动 · 正在抽排积水' : '阶段1: 路面积水正流入立交桥深坑')
}

// ==================== 动画循环 ====================
function animate() {
  animationId = requestAnimationFrame(animate)
  if (!scene) return
  const dt = Math.min(clock.getDelta(), 0.1)
  const time = performance.now() * 0.001
  frameCount++
  const evenFrame = (frameCount & 1) === 0  // 隔帧执行重负载操作
  controls.update()

  // 水面顶点动画（仅可见时计算，隔帧重算法线）
  if (water.visible) {
    const wPos = waterGeo.attributes.position.array
    const drainX = 0, drainZ = roadLength / 2 - 2
    for (let i = 0; i < wPos.length; i += 3) {
      const wx = wPos[i], wy = wPos[i + 2]
      const distToDrain = Math.sqrt((wx - drainX) ** 2 + (wy - drainZ) ** 2)
      const ripple = Math.sin(wx * 2 + time * 3) * Math.cos(wy * 2.5 + time * 2.5) * 0.08
      const ripple2 = Math.sin(wx * 4.5 - time * 5) * Math.cos(wy * 3.5 + time * 4) * 0.05
      let vortex = 0
      if (distToDrain < 3) {
        vortex = -Math.max(0, 1 - distToDrain / 3) * 0.4 * (1 + Math.sin(time * 4) * 0.3)
        const angle = Math.atan2(wy - drainZ, wx - drainX)
        vortex += Math.sin(angle * 3 + time * 6) * Math.max(0, 1 - distToDrain / 3) * 0.06
      }
      wPos[i + 1] = ripple + ripple2 + vortex
    }
    waterGeo.attributes.position.needsUpdate = true
    if (evenFrame) waterGeo.computeVertexNormals()
  }

  // 演示排水动画
  if (demoActive.value) {
    if (_demoPhase === 1) {
      overflowLevel -= flowSpeed * dt
      pitLevel = 1.0 + (1.0 - overflowLevel) * pitRiseAmount
      if (overflowLevel < minLevel) { overflowLevel = minLevel; _demoPhase = 2; setDemoStatus('阶段2: 应急排水泵启动 · 正在抽排积水') }
    } else if (_demoPhase === 2) {
      pitLevel -= pumpSpeed * dt
      overflowLevel -= pumpSpeed * 0.5 * dt
      if (overflowLevel < 0) overflowLevel = 0
      if (pitLevel < minLevel) {
        pitLevel = 0; overflowLevel = 0; demoActive.value = false; _demoPhase = 3
        setDemoStatus('✅ 抽水完成 · 路面积水已全部排空')
        store.device.relay_on = false
      }
    }
    const owY = 0.01 + 0.07 * overflowLevel
    const owOpacity = 0.82 * Math.pow(overflowLevel, 1.8)
    overflowWaters.forEach(ow => {
      ow.mesh.material.opacity = owOpacity; ow.mesh.visible = overflowLevel > 0.01; ow.mesh.position.y = owY
      ow.flowParticles.visible = overflowLevel > 0.05; ow.fpMat.opacity = 0.7 * overflowLevel
    })
    if (pitLevel <= 0) { water.visible = false; drain.visible = false; drainHole.visible = false; mist.visible = false }
    else {
      water.visible = true; water.position.y = roadDepth + 0.15 * pitLevel; water.material.opacity = Math.min(0.92, 0.85 * pitLevel)
      mist.material.opacity = 0.3 * pitLevel; mist.visible = pitLevel > 0.05; drain.visible = pitLevel > 0.03
    }
    const totalDepth = (2.83 * Math.max(pitLevel, 0)).toFixed(2)
    setWaterDepth(totalDepth + ' m', pitLevel < 0.3 ? 'ok' : pitLevel < 0.6 ? 'warn' : '')
    waterPump.workLight.intensity = _demoPhase === 2 ? 3.0 + Math.sin(time * 8) * 0.8 : 1.5 + Math.sin(time * 3) * 0.3
    const splashIntensity = _demoPhase === 1 ? overflowLevel : (_demoPhase === 2 ? overflowLevel * 0.5 : 0)
    inletSplash.visible = splashIntensity > 0.02; inletSplashMat.opacity = 0.6 * splashIntensity
    if (splashIntensity > 0.02) {
      const spPos = inletSplashGeo.attributes.position.array
      for (let i = 0; i < inletSplashCount; i++) {
        const v = inletSplashVel[i]
        spPos[i * 3] += v.vx * dt; spPos[i * 3 + 1] += v.vy * dt; spPos[i * 3 + 2] += v.vz * dt
        v.vy -= dt * 4
        if (spPos[i * 3 + 1] < roadDepth + 0.1) {
          const inlet = inletPositions[v.inletIdx]
          spPos[i * 3] = inlet.x + (Math.random() - 0.5) * 0.5; spPos[i * 3 + 1] = roadDepth + 0.3 + Math.random() * 0.3; spPos[i * 3 + 2] = inlet.z + (Math.random() - 0.5) * 0.5
          v.vx = (inlet.x === 0 ? (Math.random() - 0.5) * 0.3 : -Math.sign(inlet.x) * (0.5 + Math.random() * 0.5)); v.vy = 0.5 + Math.random() * 1.0; v.vz = (inlet.z === 0 ? (Math.random() - 0.5) * 0.3 : -Math.sign(inlet.z) * (0.5 + Math.random() * 0.5))
        }
      }
      inletSplashGeo.attributes.position.needsUpdate = true
    }
  } else if (_demoPhase === 3) {
    water.visible = false; drain.visible = false; drainHole.visible = false; mist.visible = false; inletSplash.visible = false
    overflowWaters.forEach(ow => { ow.mesh.visible = false; ow.flowParticles.visible = false })
    setWaterDepth('0.00 m', 'ok')
  } else if (overflowLevel > 0.99 && pitLevel > 0.99 && !stormActive.value) {
    water.visible = true; drain.visible = true; drainHole.visible = true; mist.visible = true; mist.material.opacity = 0.3; inletSplash.visible = false
    water.position.y = roadDepth + 0.15; water.material.opacity = 0.85
    overflowWaters.forEach(ow => { ow.mesh.visible = true; ow.mesh.material.opacity = 0.82; ow.mesh.position.y = 0.08; ow.flowParticles.visible = true; ow.fpMat.opacity = 0.7 })
  }

  // 暴雨模式
  // 排水演示进行中时，水位由排水动画控制，暴雨块只处理洪泛面消退
  if (stormActive.value || stormLevel > 0.01) {
    if (stormRising) {
      stormLevel += dt * 0.15
      if (stormLevel > 1.0) { stormLevel = 1.0; if (!demoActive.value) setDemoStatus('⚠ 路面已被完全淹没 · 积水深重') }
    } else if (!stormActive.value) {
      stormLevel -= dt * 0.04
      if (stormLevel < 0.01) { stormLevel = 0; if (!demoActive.value) setDemoStatus('☀ 积水已退去 · 路面恢复') }
    }
    // 排水演示中不覆盖溢流水/深坑水的水位控制（由排水动画接管）
    if (!demoActive.value) {
      const stormY = 0.02 + 0.8 * stormLevel; const stormOpacity = 0.9 * stormLevel
      overflowWaters.forEach(ow => { ow.mesh.visible = stormLevel > 0.01; ow.mesh.material.opacity = stormOpacity; ow.mesh.position.y = stormY; ow.flowParticles.visible = stormLevel > 0.1; ow.fpMat.opacity = 0.8 * stormLevel })
      water.visible = stormLevel > 0.01; water.position.y = roadDepth + 0.15 + 0.3 * stormLevel; water.material.opacity = Math.min(0.95, 0.85 + 0.1 * stormLevel)
      mist.visible = stormLevel > 0.1; mist.material.opacity = 0.4 * stormLevel; drain.visible = stormLevel > 0.05; drainHole.visible = stormLevel > 0.05
      const stormDepth = (3.5 * stormLevel).toFixed(2)
      setWaterDepth(stormDepth + ' m', stormLevel > 0.7 ? '' : stormLevel > 0.4 ? 'warn' : 'ok')
    }
    // 洪泛面始终由暴雨控制（排水不影响山坡洪水）
    floodWater.visible = stormLevel > 0.01; floodWater.position.y = 0.1 + 2.5 * stormLevel; floodWater.material.opacity = 0.75 * stormLevel
  } else {
    floodWater.visible = false
  }

  // 溢流水波动画（演示完成态跳过顶点计算，隔帧重算法线）
  const owActive = _demoPhase !== 3 || stormActive.value || stormLevel > 0.01
  overflowWaters.forEach(ow => {
    if (!ow.mesh.visible && !owActive) return
    const oPos = ow.geo.attributes.position.array
    let owAmp
    if (_demoPhase === 3) owAmp = 0
    else if (demoActive.value) owAmp = Math.max(overflowLevel, 0.05)
    else owAmp = 1.0
    if (ow.tex && owAmp > 0.01) { ow.tex.offset.y -= dt * 0.15 * owAmp; ow.tex.offset.x = Math.sin(time * 0.3) * 0.02 }
    if (owAmp > 0.01) {
      for (let i = 0; i < oPos.length; i += 3) {
        const lx = oPos[i], lz = oPos[i + 2]
        const flowProg = (lz + ow.l / 2) / ow.l
        const edgeFactor = 1 - Math.pow(Math.abs(lx) / (ow.w / 2), 2) * 0.4
        const baseHeight = _demoPhase === 3 ? 0 : (ow.startY + (ow.endY - ow.startY) * flowProg) * edgeFactor
        const flowWave1 = Math.sin(lz * 1.2 - time * 3.5) * 0.06 * (1 - flowProg * 0.7) * owAmp
        const flowWave2 = Math.sin(lz * 2.8 - time * 6 + lx * 0.5) * 0.035 * (1 - flowProg * 0.6) * owAmp
        const turb = Math.sin(lx * 4 + time * 2.5) * Math.cos(lz * 3 - time * 3) * 0.03 * owAmp
        const capillary = Math.sin(lx * 9 + time * 8) * Math.sin(lz * 7 - time * 7) * 0.012 * owAmp
        oPos[i + 1] = baseHeight + (flowWave1 + flowWave2 + turb + capillary) * edgeFactor
      }
      ow.geo.attributes.position.needsUpdate = true
      if (evenFrame) ow.geo.computeVertexNormals()
    }
    const fpPos = ow.fpGeo.attributes.position.array
    const flowSpd = demoActive.value ? (2.0 + (1.0 - overflowLevel) * 3.0) : 0.8
    for (let i = 0; i < ow.fpProgress.length; i++) {
      ow.fpProgress[i] += dt * flowSpd / ow.l
      if (ow.fpProgress[i] > 1) ow.fpProgress[i] = 0
      const p = ow.fpProgress[i]; fpPos[i * 3 + 2] = ow.l / 2 - p * ow.l
      fpPos[i * 3] += (Math.random() - 0.5) * 0.02
      if (Math.abs(fpPos[i * 3]) > ow.w * 0.4) fpPos[i * 3] *= 0.9
      fpPos[i * 3 + 1] = 0.02 + (1 - p) * 0.06
    }
    ow.fpGeo.attributes.position.needsUpdate = true
  })

  // 洪水波动画（隔帧重算法线）
  if (floodWater.visible) {
    const fPos = floodGeo.attributes.position.array
    const fAmp = stormActive.value ? stormLevel : Math.max(stormLevel, 0.1)
    for (let i = 0; i < fPos.length; i += 3) {
      const fx = fPos[i], fz = fPos[i + 2]
      const wave1 = Math.sin(fx * 0.3 + time * 2) * Math.cos(fz * 0.25 + time * 1.5) * 0.15 * fAmp
      const wave2 = Math.sin(fx * 0.6 - time * 3) * Math.cos(fz * 0.5 + time * 2) * 0.08 * fAmp
      const wave3 = Math.sin(fx * 1.2 + fz * 0.8 - time * 4) * 0.04 * fAmp
      fPos[i + 1] = wave1 + wave2 + wave3
    }
    floodGeo.attributes.position.needsUpdate = true
    if (evenFrame) floodGeo.computeVertexNormals()
    floodTex.offset.y -= dt * 0.2 * fAmp; floodTex.offset.x = Math.sin(time * 0.4) * 0.03
  }

  // 水洼/池塘涟漪（使用缓存数组，避免 scene.traverse）
  for (let i = 0; i < cachedPuddles.length; i++) {
    const obj = cachedPuddles[i]
    obj.material.opacity = 0.6 + Math.sin(time * 2 + obj.position.x * 5) * 0.15
  }
  for (let i = 0; i < cachedPonds.length; i++) {
    const obj = cachedPonds[i]
    obj.material.opacity = 0.7 + Math.sin(time * 1.5 + obj.position.x * 3) * 0.1
  }

  // 雨下落
  const rainSpeed = stormActive.value ? 14 : 7
  rain.position.y -= dt * rainSpeed
  rain.material.opacity = stormActive.value ? 0.5 : 0.22
  if (rain.position.y < -2) rain.position.y = 2

  // 雾气（仅可见时计算）
  if (mist.visible) {
    const mistArr = mistGeo.attributes.position.array
    for (let i = 0; i < mistArr.length; i += 3) {
      mistArr[i + 1] += (Math.random() - 0.45) * dt * 1.5
      if (mistArr[i + 1] > roadDepth + 2) mistArr[i + 1] = roadDepth
      if (mistArr[i + 1] < roadDepth) mistArr[i + 1] = roadDepth + 0.1
    }
    mistGeo.attributes.position.needsUpdate = true
  }

  // 交通灯
  ;[trafficLight, trafficLight2].forEach(tl => {
    if (!tl) return
    tl.children.forEach(child => {
      if (child.name && child.name.startsWith('trafficLight_')) {
        const idx = parseInt(child.name.split('_')[1])
        if (idx === 1) child.material.emissiveIntensity = Math.sin(time * 6) > 0 ? 1.5 : 0.1
      }
    })
  })

  // 建筑霓虹灯闪烁
  buildings.forEach(b => {
    if (b.userData.signLights) {
      b.userData.signLights.forEach(sl => {
        const flicker = 0.6 + 0.4 * Math.sin(time * (3 + sl.phase) + sl.phase)
        sl.light.intensity = sl.baseIntensity * flicker * (0.7 + 0.3 * Math.random())
      })
    }
  })

  // 传感器 LED 闪烁（使用缓存数组，避免 scene.traverse）
  for (let i = 0; i < cachedLeds.length; i++) {
    const obj = cachedLeds[i]
    const isBlue = obj.name.includes('blue')
    const blinkRate = isBlue ? 2 : 3.5
    const blink = Math.sin(time * blinkRate + (obj.position.x || 0) * 10) > 0 ? 1.5 : 0.15
    obj.material.emissiveIntensity = blink
  }

  // 排水口旋转
  drain.rotation.z += dt * 2; drainHole.rotation.y += dt * 1.5

  // 气象传感器
  if (weatherSensor.userData.anemoGroup) {
    weatherSensor.userData.anemoGroup.rotation.y += dt * 6
    weatherSensor.userData.vaneBody.rotation.y = Math.sin(time * 0.5) * 0.3
    weatherSensor.userData.ledBlue.material.emissiveIntensity = Math.sin(time * 2) > 0 ? 1.5 : 0.1
    weatherSensor.userData.ledRed.material.emissiveIntensity = Math.sin(time * 5) > 0.5 ? 1.5 : 0.1
  }
  if (soilSensor.userData.led) soilSensor.userData.led.material.emissiveIntensity = Math.sin(time * 1.5) > 0 ? 1.5 : 0.2
  if (weatherSign.userData.signLed) weatherSign.userData.signLed.material.emissiveIntensity = Math.sin(time * 3) > 0 ? 1.5 : 0.2
  if (soilSign.userData.signLed) soilSign.userData.signLed.material.emissiveIntensity = Math.sin(time * 3 + Math.PI) > 0 ? 1.5 : 0.2

  // 排水泵 — 根据继电器/演示状态切换待机/抽水
  const pumpActive = store.device.relay_on || (demoActive.value && _demoPhase === 2)
  pumpVibration += dt
  if (pumpActive) {
    // 抽水模式：全灯闪烁 + 泵体振动 + 强光
    waterPump.pumpLeds[0].material.emissiveIntensity = 1.5 + Math.sin(time * 20) * 0.5   // 绿灯快速闪
    waterPump.pumpLeds[1].material.emissiveIntensity = Math.sin(time * 12) > 0 ? 2.0 : 0.1 // 黄灯交替闪
    waterPump.pumpLeds[2].material.emissiveIntensity = Math.sin(time * 15) > 0.3 ? 2.0 : 0.1 // 红灯快速闪
    waterPump.pump.position.y = 0.8 + Math.sin(pumpVibration * 60) * 0.03         // 大振动
    waterPump.motor.position.y = 0.8 + Math.sin(pumpVibration * 65 + 1) * 0.02
    waterPump.workLight.intensity = 4.0 + Math.sin(time * 15) * 1.5                // 强光闪
    // 排水粒子可见
    if (flowParticles) { flowParticles.visible = true; flowMat.opacity = 0.9 }
  } else {
    // 待机模式：仅绿灯微亮 + 无振动 + 暗灯
    waterPump.pumpLeds[0].material.emissiveIntensity = 0.4 + Math.sin(time * 1.5) * 0.15
    waterPump.pumpLeds[1].material.emissiveIntensity = 0.05
    waterPump.pumpLeds[2].material.emissiveIntensity = 0.05
    waterPump.pump.position.y = 0.8 + Math.sin(time * 2) * 0.003
    waterPump.motor.position.y = 0.8 + Math.sin(time * 2.5 + 1) * 0.002
    waterPump.workLight.intensity = 0.6 + Math.sin(time * 2) * 0.2
    // 排水粒子不可见
    if (flowParticles) { flowParticles.visible = false; flowMat.opacity = 0 }
  }
  const fPos2 = flowGeo.attributes.position.array
  const S = waterPump.scale
  for (let i = 0; i < flowCount; i++) {
    fPos2[i * 3 + 1] += dt * 2.5
    if (fPos2[i * 3 + 1] > 0.8 * S) { fPos2[i * 3] = -0.7 * S + (Math.random() - 0.5) * 0.1; fPos2[i * 3 + 1] = -1.0 * S; fPos2[i * 3 + 2] = 1.8 * S + (Math.random() - 0.5) * 0.1 }
  }
  flowGeo.attributes.position.needsUpdate = true

  // 桥上车辆
  bridge1Cars.forEach(c => {
    c.x += c.dir * c.speed * dt
    if (c.x > 10) c.x = -10; if (c.x < -10) c.x = 10
    c.group.position.x = c.x; c.group.position.z = c.lane
    c.wheels.forEach(w => { w.rotation.x += c.dir * c.speed * dt * 4 })
  })
  bridge2Cars.forEach(c => {
    c.z += c.dir * c.speed * dt
    if (c.z > 10) c.z = -10; if (c.z < -10) c.z = 10
    c.group.position.z = c.z; c.group.position.x = c.lane
    c.wheels.forEach(w => { w.rotation.x += c.dir * c.speed * dt * 4 })
  })

  renderer.render(scene, camera)
}

// ==================== 窗口大小变化 ====================
function onResize() {
  if (!container.value || !camera || !renderer) return
  const w = container.value.clientWidth; const h = container.value.clientHeight
  camera.aspect = w / h; camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

// ==================== 数据对接：dataStore 联动 ====================
// 雨强度 → 雨粒子
watch(rainIntensity, (v) => {
  if (!rainMat) return
  if (v > 0.02) { rain.visible = true; rainMat.opacity = 0.22 + v * 0.28 }
  else { rainMat.opacity = 0.22 }
}, { immediate: false })

// 风险等级 → 暴雨模式（外部触发时联动）
watch(() => store.ai.risk_level, (level) => {
  if (!scene) return
  if ((level === 'CRITICAL' || level === 'WARNING') && !demoActive.value && !stormActive.value) {
    // 外部（如一键演示/MQTT）触发暴雨
    stormActive.value = true; stormRising = true; stormLevel = Math.max(stormLevel, level === 'CRITICAL' ? 0.6 : 0.3)
    setDemoStatus('🌧 风险升级 · 路面积水正在暴涨')
  } else if (level === 'NORMAL' || level === 'WATCH') {
    // 风险解除 → 暴雨停止（积水自然消退）
    if (stormActive.value) { stormActive.value = false; stormRising = false; setDemoStatus('☀ 风险解除 · 积水缓慢消退') }
  }
})

// 排水继电器联动：
// - App一键演示触发 relay_on 时，启动3D排水动画（但不清除暴雨，让水位自然降）
// - MQTT真实指令触发时同样响应
watch(() => store.device.relay_on, (on) => {
  if (!scene) return
  if (on && !demoActive.value) {
    startDemo(true)  // fastPump: 跳过积水阶段，直接抽水
  }
  // relay_on变false时不立即重置demo，让动画自然结束
})

// ==================== 生命周期 ====================
onMounted(() => {
  initScene()
  animate()
  loading.value = false
  window.addEventListener('resize', onResize)
  // 初始化积水深度显示
  setWaterDepth('2.83 m', '')
  console.log('🛡️ 深渊哨盾 ABYSS SENTINEL | 3D城市数字孪生场景已加载')
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  if (canvasEl) {
    canvasEl.removeEventListener('pointerup', resetCursor)
    canvasEl.removeEventListener('pointercancel', resetCursor)
  }
  if (renderer) { renderer.dispose(); if (canvasEl && canvasEl.parentNode) canvasEl.parentNode.removeChild(canvasEl) }
})

// 暴露方法：复位相机视角（兼容 App.vue 的 flyToLNU 调用）
function resetCamera() {
  if (!camera || !controls) return
  camera.position.set(35, 28, 38)
  controls.target.set(0, -2, 0)
  controls.update()
}
defineExpose({ flyToLNU: resetCamera, resetCamera })
</script>

<style scoped>
.abyss-scene {
  width: 100%; height: 100%;
  position: relative;
  overflow: hidden;
  cursor: grab;
  contain: layout style paint;
}
.abyss-scene :deep(canvas) { display: block; }

/* 触控 Toast */
.touch-toast {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%) scale(0.8);
  background: rgba(0,0,0,0.8); color: #ffaa44;
  padding: 10px 24px; border-radius: 8px;
  border: 1px solid rgba(255,170,68,0.5);
  font-size: 14px; font-family: 'Microsoft YaHei', sans-serif;
  z-index: 100; opacity: 0; pointer-events: none; white-space: nowrap;
  transition: opacity .3s ease, transform .3s cubic-bezier(.34,1.56,.64,1);
  box-shadow: 0 0 20px rgba(255,170,68,0.3);
}
.touch-toast.show { opacity: 1; transform: translate(-50%, -50%) scale(1); }

/* 加载提示 */
.scene-loading {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(10,20,50,0.9);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  z-index: 100; color: #c8d6ec; font-size: 16px;
}
.loading-spinner {
  width: 48px; height: 48px;
  border: 3px solid rgba(153,192,254,0.2);
  border-top-color: #4786d4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
