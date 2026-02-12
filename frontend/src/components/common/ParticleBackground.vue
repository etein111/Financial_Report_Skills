<template>
  <canvas ref="canvas" class="particle-canvas"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref<HTMLCanvasElement | null>(null)

// 粒子配置
const PARTICLE_COUNT = 120
const CONNECTION_DISTANCE = 140
const PULSE_SPEED = 0.15

// 粒子类
class Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  baseOpacity: number
  opacity: number
  pulseOffset: number
  hue: number

  constructor(canvasWidth: number, canvasHeight: number) {
    this.x = Math.random() * canvasWidth
    this.y = Math.random() * canvasHeight
    this.vx = (Math.random() - 0.5) * 1
    this.vy = (Math.random() - 0.5) * 1
    this.size = Math.random() * 2 + 1
    this.baseOpacity = Math.random() * 0.4 + 0.3
    this.opacity = this.baseOpacity
    this.pulseOffset = Math.random() * Math.PI * 2
    this.hue = Math.random() * 60 + 200 // 200-260: 蓝色到青色
  }

  update(canvasWidth: number, canvasHeight: number, time: number) {
    // 移动
    this.x += this.vx
    this.y += this.vy

    // 边界反弹
    if (this.x < 0 || this.x > canvasWidth) this.vx *= -1
    if (this.y < 0 || this.y > canvasHeight) this.vy *= -1

    // 脉冲闪烁
    this.opacity = this.baseOpacity + Math.sin(time * PULSE_SPEED + this.pulseOffset) * 0.2
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${this.hue}, 70%, 60%, ${this.opacity})`
    ctx.fill()
  }
}

let animationId: number | null = null
let particles: Particle[] = []
let canvasWidth = 0
let canvasHeight = 0
let time = 0

function animate(ctx: CanvasRenderingContext2D) {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)

  time += 1

  // 更新和绘制粒子
  for (let i = 0; i < particles.length; i++) {
    particles[i].update(canvasWidth, canvasHeight, time)
    particles[i].draw(ctx)

    // 绘制连线
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < CONNECTION_DISTANCE) {
        const opacity = (1 - distance / CONNECTION_DISTANCE) * 0.3
        ctx.beginPath()
        ctx.strokeStyle = `rgba(100, 150, 255, ${opacity})`
        ctx.lineWidth = 1
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.stroke()
      }
    }
  }

  animationId = requestAnimationFrame(() => animate(ctx))
}

function handleResize() {
  if (!canvas.value) return

  canvasWidth = window.innerWidth
  canvasHeight = window.innerHeight

  canvas.value.width = canvasWidth
  canvas.value.height = canvasHeight

  // 重新初始化粒子
  particles = []
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle(canvasWidth, canvasHeight))
  }
}

onMounted(() => {
  if (!canvas.value) return

  // 初始化画布大小
  handleResize()

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)

  // 启动动画
  const ctx = canvas.value.getContext('2d')
  if (ctx) {
    animate(ctx)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (animationId !== null) {
    cancelAnimationFrame(animationId)
  }
})
</script>

<style scoped>
.particle-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
</style>
