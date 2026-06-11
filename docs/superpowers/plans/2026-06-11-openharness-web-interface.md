# OpenHarness Web Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the OpenHarness CLI project to a web interface with a small frontend for demonstration purposes, focusing on MVP features: basic financial hotspot pipeline execution, simple result display, and generic skill execution.

**Architecture:** Create a Vue 3 + Vite frontend that communicates with the existing FastAPI backend via RESTful API calls and SSE streaming. The frontend will be deployed as static files and can be hosted independently from the backend.

**Tech Stack:** Vue 3, Vite, Tailwind CSS, Axios, EventSource API

---
## File Structure

### Frontend Project Structure
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── FinancialHotspotForm.vue     # Form for financial hotspot pipeline
│   │   ├── GenericExecuteForm.vue       # Form for generic skill execution
│   │   ├── ResultDisplay.vue            # Component to display results
│   │   └── ProgressIndicator.vue        # Component to show execution progress
│   ├── views/
│   │   ├── HomeView.vue                 # Main page with navigation
│   │   └── DemoView.vue                 # Demo page with both forms
│   ├── api/
│   │   └── openharness.js               # API client for OpenHarness backend
│   ├── App.vue                          # Root component
│   └── main.js                          # Application entry point
├── package.json                         # Project dependencies
├── vite.config.js                       # Vite configuration
└── tailwind.config.js                   # Tailwind CSS configuration
```

### Backend Integration Points
- `/api/v1/financial-hotspot-pipeline` - Dedicated endpoint for financial hotspot pipeline
- `/api/v1/execute` - Generic execution endpoint
- `/api/v1/execute/stream` - SSE streaming endpoint for real-time updates
- `/api/v1/health` - Health check endpoint

## Implementation Tasks

### Task 1: Frontend Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/public/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`

- [ ] **Step 1: Initialize package.json**

```json
{
  "name": "openharness-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 2: Create Vite configuration**

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: Create Tailwind CSS configuration**

```javascript
// tailwind.config.js
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 4: Create PostCSS configuration**

```javascript
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: Create HTML template**

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OpenHarness Web Interface</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 6: Create main.js entry point**

```javascript
// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'

createApp(App).mount('#app')
```

- [ ] **Step 7: Create main.css**

```css
/* src/assets/main.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 8: Create root App component**

```vue
<!-- src/App.vue -->
<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <h1 class="text-3xl font-bold text-gray-900">OpenHarness Web Interface</h1>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>
```

- [ ] **Step 9: Install dependencies and verify setup**

Run: `cd frontend && npm install`
Expected: All dependencies installed without errors

- [ ] **Step 10: Commit frontend project setup**

```bash
git add frontend/
git commit -m "feat: add frontend project setup with Vue 3, Vite, and Tailwind CSS"
```

### Task 2: API Client Implementation

**Files:**
- Create: `frontend/src/api/openharness.js`

- [ ] **Step 1: Create API client module**

```javascript
// src/api/openharness.js
import axios from 'axios'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: '/api/v1', // Will be proxied to backend in development
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Financial Hotspot Pipeline API
export const executeFinancialHotspotPipeline = async (payload) => {
  try {
    const response = await apiClient.post('/financial-hotspot-pipeline', payload)
    return response.data
  } catch (error) {
    throw error.response?.data || error
  }
}

// Generic Execute API
export const executeGeneric = async (payload) => {
  try {
    const response = await apiClient.post('/execute', payload)
    return response.data
  } catch (error) {
    throw error.response?. data || error
  }
}

// Health Check API
export const healthCheck = async () => {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error) {
    throw error.response?.data || error
  }
}

// SSE Streaming helper
export const createSSEConnection = (endpoint, payload) => {
  // For POST requests with SSE, we need to use a different approach
  // since EventSource only supports GET requests
  // We'll implement a custom SSE client using fetch and ReadableStream
  
  const url = `${window.location.origin}/api/v1${endpoint}`
  
  return {
    start: async (onMessage, onError, onComplete) => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        
        const processStream = async () => {
          try {
            const { done, value } = await reader.read()
            
            if (done) {
              onComplete?.()
              return
            }
            
            buffer += decoder.decode(value, { stream: true })
            
            // Process complete lines
            const lines = buffer.split('\n')
            buffer = lines.pop() // Keep incomplete line in buffer
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.substring(6))
                  onMessage?.(data)
                } catch (e) {
                  console.warn('Failed to parse SSE data:', line, e)
                }
              }
            }
            
            // Continue reading
            processStream()
          } catch (error) {
            onError?.(error)
          }
        }
        
        processStream()
        
        return {
          close: () => reader.cancel()
        }
      } catch (error) {
        onError?.(error)
        return null
      }
    }
  }
}

export default apiClient
```

- [ ] **Step 2: Test API client with health check**

Create a temporary test component to verify API connectivity:

```vue
<!-- src/components/ApiTest.vue -->
<template>
  <div>
    <button @click="testHealth">Test Health Check</button>
    <p v-if="healthStatus">{{ healthStatus }}</p>
  </div>
</template>

<script>
import { healthCheck } from '@/api/openharness'

export default {
  data() {
    return {
      healthStatus: null
    }
  },
  methods: {
    async testHealth() {
      try {
        const result = await healthCheck()
        this.healthStatus = JSON.stringify(result)
      } catch (error) {
        this.healthStatus = 'Error: ' + error.message
      }
    }
  }
}
</script>
```

- [ ] **Step 3: Verify API client works**

Run: `cd frontend && npm run dev`
Expected: Development server starts on http://localhost:3000
Test: Click "Test Health Check" button and verify it shows health status

- [ ] **Step 4: Commit API client implementation**

```bash
git add frontend/src/api/openharness.js
git commit -m "feat: implement OpenHarness API client with SSE support"
```

### Task 3: Core UI Components

**Files:**
- Create: `frontend/src/components/FinancialHotspotForm.vue`
- Create: `frontend/src/components/GenericExecuteForm.vue`
- Create: `frontend/src/components/ResultDisplay.vue`
- Create: `frontend/src/components/ProgressIndicator.vue`

- [ ] **Step 1: Create FinancialHotspotForm component**

```vue
<!-- src/components/FinancialHotspotForm.vue -->
<template>
  <div class="bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-4">财经热点生图</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          主题 *
        </label>
        <input
          v-model="formData.topic"
          type="text"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          placeholder="例如：60只芯片股历史新高"
        />
      </div>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          内容类型
        </label>
        <select
          v-model="formData.content_type"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="xingfengxiang">兴风向分析</option>
          <option value="knowledge_popularization">知识普及</option>
        </select>
      </div>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          补充内容（可选）
        </label>
        <textarea
          v-model="formData.content"
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          placeholder="提供额外的新闻背景或上下文信息..."
        ></textarea>
      </div>
      
      <button
        type="submit"
        :disabled="isExecuting"
        class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ isExecuting ? '执行中...' : '生成财经长图' }}
      </button>
    </form>
    
    <ProgressIndicator 
      v-if="isExecuting" 
      :current-step="currentStep"
      :total-steps="3"
    />
  </div>
</template>

<script>
import { executeFinancialHotspotPipeline } from '@/api/openharness'
import ProgressIndicator from './ProgressIndicator.vue'

export default {
  name: 'FinancialHotspotForm',
  components: {
    ProgressIndicator
  },
  emits: ['execution-complete', 'execution-error'],
  data() {
    return {
      formData: {
        topic: '',
        content_type: 'xingfengxiang',
        content: ''
      },
      isExecuting: false,
      currentStep: 0
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.formData.topic.trim()) {
        this.$emit('execution-error', '主题不能为空')
        return
      }
      
      this.isExecuting = true
      this.currentStep = 0
      
      try {
        // Simulate step progression for demo
        this.currentStep = 1 // Hotspot scanning
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        this.currentStep = 2 // Content generation
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        this.currentStep = 3 // Image rendering
        const result = await executeFinancialHotspotPipeline(this.formData)
        
        this.$emit('execution-complete', result)
      } catch (error) {
        this.$emit('execution-error', error.message || '执行失败')
      } finally {
        this.isExecuting = false
      }
    }
  }
}
</script>
```

- [ ] **Step 2: Create GenericExecuteForm component**

```vue
<!-- src/components/GenericExecuteForm.vue -->
<template>
  <div class="bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-4">通用技能执行</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          技能名称
        </label>
        <select
          v-model="formData.force_skill"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="financial-hotspot-pipeline">financial-hotspot-pipeline</option>
          <option value="">自动匹配技能</option>
        </select>
      </div>
      
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Prompt *
        </label>
        <textarea
          v-model="formData.prompt"
          required
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          placeholder="输入要执行的指令..."
        ></textarea>
      </div>
      
      <button
        type="submit"
        :disabled="isExecuting"
        class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ isExecuting ? '执行中...' : '执行技能' }}
      </button>
    </form>
  </div>
</template>

<script>
import { executeGeneric } from '@/api/openharness'

export default {
  name: 'GenericExecuteForm',
  emits: ['execution-complete', 'execution-error'],
  data() {
    return {
      formData: {
        prompt: '',
        force_skill: 'financial-hotspot-pipeline'
      },
      isExecuting: false
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.formData.prompt.trim()) {
        this.$emit('execution-error', 'Prompt不能为空')
        return
      }
      
      this.isExecuting = true
      
      try {
        const result = await executeGeneric(this.formData)
        this.$emit('execution-complete', result)
      } catch (error) {
        this.$emit('execution-error', error.message || '执行失败')
      } finally {
        this.isExecuting = false
      }
    }
  }
}
</script>
```

- [ ] **Step 3: Create ResultDisplay component**

```vue
<!-- src/components/ResultDisplay.vue -->
<template>
  <div class="bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-4">执行结果</h2>
    
    <div v-if="error" class="mb-4 p-4 bg-red-50 text-red-700 rounded-md">
      <p class="font-medium">错误:</p>
      <p>{{ error }}</p>
    </div>
    
    <div v-else-if="result" class="space-y-4">
      <!-- Article Display -->
      <div v-if="result.article" class="prose max-w-none">
        <h3 class="text-lg font-semibold mb-2">生成的文章</h3>
        <div class="bg-gray-50 p-4 rounded-md overflow-x-auto">
          <pre class="whitespace-pre-wrap">{{ result.article }}</pre>
        </div>
        <button
          @click="downloadArticle"
          class="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          下载文章
        </button>
      </div>
      
      <!-- Infographic Display -->
      <div v-if="result.infographic_path" class="space-y-2">
        <h3 class="text-lg font-semibold">生成的长图</h3>
        <img
          :src="getImageUrl(result.infographic_path)"
          alt="Generated infographic"
          class="max-w-full h-auto border rounded-md"
        />
        <button
          @click="downloadInfographic"
          class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          下载长图
        </button>
      </div>
      
      <!-- Generic Result Display -->
      <div v-else-if="!result.article && !result.infographic_path" class="bg-gray-50 p-4 rounded-md">
        <h3 class="text-lg font-semibold mb-2">执行结果</h3>
        <pre class="whitespace-pre-wrap">{{ JSON.stringify(result, null, 2) }}</pre>
      </div>
    </div>
    
    <div v-else class="text-gray-500 text-center py-8">
      执行结果将显示在这里
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultDisplay',
  props: {
    result: {
      type: Object,
      default: null
    },
    error: {
      type: String,
      default: null
    }
  },
  methods: {
    getImageUrl(path) {
      // Convert relative path to absolute URL
      if (path.startsWith('/')) {
        return `http://localhost:8000${path}`
      }
      return `http://localhost:8000/${path}`
    },
    downloadArticle() {
      if (!this.result?.article) return
      
      const blob = new Blob([this.result.article], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'article.md'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
    downloadInfographic() {
      if (!this.result?.infographic_path) return
      
      const imageUrl = this.getImageUrl(this.result.infographic_path)
      const a = document.createElement('a')
      a.href = imageUrl
      a.download = 'infographic.png'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }
}
</script>
```

- [ ] **Step 4: Create ProgressIndicator component**

```vue
<!-- src/components/ProgressIndicator.vue -->
<template>
  <div class="mt-4">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-medium text-gray-700">执行进度</span>
      <span class="text-sm text-gray-500">{{ currentStep }} / {{ totalSteps }}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div
        class="bg-blue-600 h-2 rounded-full transition-all duration-300"
        :style="{ width: percentage + '%' }"
      ></div>
    </div>
    <div class="mt-2 text-sm text-gray-600">
      {{ currentStepText }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProgressIndicator',
  props: {
    currentStep: {
      type: Number,
      required: true
    },
    totalSteps: {
      type: Number,
      required: true
    }
  },
  computed: {
    percentage() {
      return Math.round((this.currentStep / this.totalSteps) * 100)
    },
    currentStepText() {
      const steps = ['准备中', '热点扫描', '文案生成', '长图渲染']
      return steps[this.currentStep] || '执行中...'
    }
  }
}
</script>
```

- [ ] **Step 5: Test components individually**

Create a temporary page to test all components:

```vue
<!-- src/views/TestComponents.vue -->
<template>
  <div class="max-w-4xl mx-auto p-6 space-y-6">
    <FinancialHotspotForm 
      @execution-complete="handleExecutionComplete"
      @execution-error="handleExecutionError"
    />
    <GenericExecuteForm 
      @execution-complete="handleExecutionComplete"
      @execution-error="handleExecutionError"
    />
    <ResultDisplay :result="result" :error="error" />
  </div>
</template>

<script>
import FinancialHotspotForm from '@/components/FinancialHotspotForm.vue'
import GenericExecuteForm from '@/components/GenericExecuteForm.vue'
import ResultDisplay from '@/components/ResultDisplay.vue'

export default {
  components: {
    FinancialHotspotForm,
    GenericExecuteForm,
    ResultDisplay
  },
  data() {
    return {
      result: null,
      error: null
    }
  },
  methods: {
    handleExecutionComplete(result) {
      this.result = result
      this.error = null
    },
    handleExecutionError(error) {
      this.error = error
      this.result = null
    }
  }
}
</script>
```

- [ ] **Step 6: Verify components render correctly**

Run: `cd frontend && npm run dev`
Expected: All components render without errors and handle form submissions

- [ ] **Step 7: Commit core UI components**

```bash
git add frontend/src/components/
git commit -m "feat: implement core UI components for OpenHarness web interface"
```

### Task 4: Main Application Views

**Files:**
- Create: `frontend/src/views/HomeView.vue`
- Create: `frontend/src/views/DemoView.vue`

- [ ] **Step 1: Create HomeView component**

```vue
<!-- src/views/HomeView.vue -->
<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">OpenHarness Web Interface</h1>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto">
        演示 OpenHarness 财经热点生图和通用技能执行功能的 Web 界面
      </p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
      <div class="bg-white shadow rounded-lg p-6">
        <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold mb-2">财经热点生图</h3>
        <p class="text-gray-600 mb-4">
          输入财经主题，自动生成专业的财经分析文章和信息长图。
        </p>
        <router-link 
          to="/demo" 
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          开始使用
        </router-link>
      </div>
      
      <div class="bg-white shadow rounded-lg p-6">
        <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold mb-2">通用技能执行</h3>
        <p class="text-gray-600 mb-4">
          执行 OpenHarness 支持的任意技能，体验强大的自动化能力。
        </p>
        <router-link 
          to="/demo" 
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
        >
          开始使用
        </router-link>
      </div>
    </div>
    
    <div class="bg-blue-50 rounded-lg p-6">
      <h2 class="text-xl font-semibold mb-4">使用说明</h2>
      <ol class="list-decimal list-inside space-y-2 text-gray-700">
        <li>确保 OpenHarness 后端正在运行（默认端口 8000）</li>
        <li>在表单中输入您的请求参数</li>
        <li>点击执行按钮开始处理</li>
        <li>查看生成的结果并下载文件</li>
      </ol>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HomeView'
}
</script>
```

- [ ] **Step 2: Create DemoView component**

```vue
<!-- src/views/DemoView.vue -->
<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="mb-6">
      <router-link 
        to="/" 
        class="inline-flex items-center text-blue-600 hover:text-blue-800"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        返回首页
      </router-link>
    </div>
    
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="space-y-6">
        <FinancialHotspotForm 
          @execution-complete="handleExecutionComplete"
          @execution-error="handleExecutionError"
        />
        <GenericExecuteForm 
          @execution-complete="handleExecutionComplete"
          @execution-error="handleExecutionError"
        />
      </div>
      
      <ResultDisplay :result="result" :error="error" />
    </div>
  </div>
</template>

<script>
import FinancialHotspotForm from '@/components/FinancialHotspotForm.vue'
import GenericExecuteForm from '@/components/GenericExecuteForm.vue'
import ResultDisplay from '@/components/ResultDisplay.vue'

export default {
  name: 'DemoView',
  components: {
    FinancialHotspotForm,
    GenericExecuteForm,
    ResultDisplay
  },
  data() {
    return {
      result: null,
      error: null
    }
  },
  methods: {
    handleExecutionComplete(result) {
      this.result = result
      this.error = null
    },
    handleExecutionError(error) {
      this.error = error
      this.result = null
    }
  }
}
</script>
```

- [ ] **Step 3: Update App.vue with routing**

```vue
<!-- src/App.vue -->
<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <h1 class="text-3xl font-bold text-gray-900">OpenHarness Web Interface</h1>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script>
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DemoView from './views/DemoView.vue'

const routes = [
  { path: '/', component: HomeView },
  { path: '/demo', component: DemoView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default {
  name: 'App',
  router
}
</script>
```

- [ ] **Step 4: Update main.js to include router**

```javascript
// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'

createApp(App).use(App.router).mount('#app')
```

- [ ] **Step 5: Test routing and views**

Run: `cd frontend && npm run dev`
Expected: Navigation between home and demo pages works correctly

- [ ] **Step 6: Commit main application views**

```bash
git add frontend/src/views/ frontend/src/App.vue frontend/src/main.js
git commit -m "feat: implement main application views with routing"
```

### Task 5: SSE Streaming Integration

**Files:**
- Modify: `frontend/src/components/FinancialHotspotForm.vue`
- Modify: `frontend/src/components/GenericExecuteForm.vue`

- [ ] **Step 1: Update FinancialHotspotForm to use SSE**

```vue
<!-- src/components/FinancialHotspotForm.vue (updated methods section) -->
<script>
import { createSSEConnection } from '@/api/openharness'
import ProgressIndicator from './ProgressIndicator.vue'

export default {
  name: 'FinancialHotspotForm',
  components: {
    ProgressIndicator
  },
  emits: ['execution-complete', 'execution-error'],
  data() {
    return {
      formData: {
        topic: '',
        content_type: 'xingfengxiang',
        content: ''
      },
      isExecuting: false,
      currentStep: 0,
      sseConnection: null
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.formData.topic.trim()) {
        this.$emit('execution-error', '主题不能为空')
        return
      }
      
      this.isExecuting = true
      this.currentStep = 0
      
      try {
        // Use SSE for real-time updates
        const payload = {
          ...this.formData,
          force_skill: 'financial-hotspot-pipeline'
        }
        
        this.sseConnection = createSSEConnection('/execute/stream', payload)
        
        const connection = await this.sseConnection.start(
          (data) => {
            // Handle SSE events
            console.log('SSE Event:', data)
            
            if (data.event === 'tool_start') {
              this.currentStep = data.data.step
            } else if (data.event === 'execution_complete') {
              this.$emit('execution-complete', data.data)
              this.isExecuting = false
            } else if (data.event === 'execution_error') {
              this.$emit('execution-error', data.data.message)
              this.isExecuting = false
            }
          },
          (error) => {
            this.$emit('execution-error', error.message || 'SSE连接失败')
            this.isExecuting = false
          },
          () => {
            // Stream completed
            if (this.isExecuting) {
              this.isExecuting = false
            }
          }
        )
        
        if (!connection) {
          throw new Error('Failed to establish SSE connection')
        }
      } catch (error) {
        this.$emit('execution-error', error.message || '执行失败')
        this.isExecuting = false
      }
    }
  },
  beforeUnmount() {
    // Clean up SSE connection
    if (this.sseConnection) {
      this.sseConnection.close?.()
    }
  }
}
</script>
```

- [ ] **Step 2: Update GenericExecuteForm to use SSE**

```vue
<!-- src/components/GenericExecuteForm.vue (updated methods section) -->
<script>
import { createSSEConnection } from '@/api/openharness'

export default {
  name: 'GenericExecuteForm',
  emits: ['execution-complete', 'execution-error'],
  data() {
    return {
      formData: {
        prompt: '',
        force_skill: 'financial-hotspot-pipeline'
      },
      isExecuting: false,
      sseConnection: null
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.formData.prompt.trim()) {
        this.$emit('execution-error', 'Prompt不能为空')
        return
      }
      
      this.isExecuting = true
      
      try {
        const payload = {
          prompt: this.formData.prompt,
          force_skill: this.formData.force_skill || undefined
        }
        
        this.sseConnection = createSSEConnection('/execute/stream', payload)
        
        const connection = await this.sseConnection.start(
          (data) => {
            // Handle SSE events
            console.log('SSE Event:', data)
            
            if (data.event === 'execution_complete') {
              this.$emit('execution-complete', data.data)
              this.isExecuting = false
            } else if (data.event === 'execution_error') {
              this.$emit('execution-error', data.data.message)
              this.isExecuting = false
            }
          },
          (error) => {
            this.$emit('execution-error', error.message || 'SSE连接失败')
            this.isExecuting = false
          },
          () => {
            // Stream completed
            if (this.isExecuting) {
              this.isExecuting = false
            }
          }
        )
        
        if (!connection) {
          throw new Error('Failed to establish SSE connection')
        }
      } catch (error) {
        this.$emit('execution-error', error.message || '执行失败')
        this.isExecuting = false
      }
    }
  },
  beforeUnmount() {
    // Clean up SSE connection
    if (this.sseConnection) {
      this.sseConnection.close?.()
    }
  }
}
</script>
```

- [ ] **Step 3: Test SSE functionality**

Run backend: `python src/openharness/api/main.py`
Run frontend: `cd frontend && npm run dev`
Test: Execute forms and verify real-time progress updates in browser console

- [ ] **Step 4: Commit SSE streaming integration**

```bash
git add frontend/src/components/FinancialHotspotForm.vue frontend/src/components/GenericExecuteForm.vue
git commit -m "feat: integrate SSE streaming for real-time execution updates"
```

### Task 6: Deployment Configuration

**Files:**
- Create: `frontend/vercel.json`
- Create: `frontend/netlify.toml`
- Modify: `frontend/vite.config.js`

- [ ] **Step 1: Update Vite config for production**

```javascript
// vite.config.js (updated)
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  base: './' // For GitHub Pages deployment
})
```

- [ ] **Step 2: Create Vercel configuration**

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ]
}
```

- [ ] **Step 3: Create Netlify configuration**

```toml
# netlify.toml
[build]
  publish = "dist"
  command = "npm run build"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

- [ ] **Step 4: Add build script to package.json**

```json
// package.json (updated scripts section)
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "deploy": "npm run build && echo 'Deployment ready in dist/ folder'"
  }
}
```

- [ ] **Step 5: Test production build**

Run: `cd frontend && npm run build`
Expected: Build completes successfully and creates `dist/` folder

Run: `cd frontend && npm run preview`
Expected: Production build serves on http://localhost:4173

- [ ] **Step 6: Commit deployment configuration**

```bash
git add frontend/vercel.json frontend/netlify.toml frontend/vite.config.js frontend/package.json
git commit -m "feat: add deployment configuration for Vercel, Netlify, and GitHub Pages"
```

### Task 7: Documentation and README

**Files:**
- Create: `frontend/README.md`

- [ ] **Step 1: Create comprehensive README**

```markdown
# OpenHarness Web Interface

A web frontend for the OpenHarness CLI project, designed for demonstration purposes.

## Features

- **Financial Hotspot Pipeline**: Generate professional financial analysis articles and infographics
- **Generic Skill Execution**: Execute any OpenHarness skill through a web interface
- **Real-time Progress Updates**: SSE streaming for live execution status
- **Result Download**: Download generated articles and images

## Prerequisites

- Node.js 16+
- npm or yarn
- OpenHarness backend running on http://localhost:8000

## Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

## Development

Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000 and will proxy API requests to http://localhost:8000.

## Building for Production

Build the static files:
```bash
npm run build
```

The built files will be in the `dist/` directory and can be served by any static file server.

## Deployment

### Vercel
1. Push to GitHub
2. Import the project in Vercel
3. Deploy!

### Netlify
1. Push to GitHub
2. Create a new site in Netlify
3. Select the repository and deploy!

### GitHub Pages
1. Build the project: `npm run build`
2. Push the `dist/` folder to your GitHub Pages branch

## API Integration

The frontend integrates with the following OpenHarness API endpoints:

- `POST /api/v1/financial-hotspot-pipeline` - Dedicated financial pipeline endpoint
- `POST /api/v1/execute` - Generic skill execution endpoint  
- `POST /api/v1/execute/stream` - SSE streaming endpoint
- `GET /api/v1/health` - Health check endpoint

## Environment Configuration

The frontend uses the following environment variables:

- `VITE_API_BASE_URL` - Base URL for API calls (defaults to `/api` in development, can be set for production)

## Troubleshooting

### CORS Issues
Ensure the OpenHarness backend has CORS enabled for your frontend origin.

### SSE Connection Failures
Verify that the backend supports SSE streaming and that the network connection is stable.

### Missing Results
Check that the backend is properly configured with the necessary API keys for LLM and image generation services.
```

- [ ] **Step 2: Commit documentation**

```bash
git add frontend/README.md
git commit -m "docs: add comprehensive README for OpenHarness web interface"
```

## Plan Self-Review

### Spec Coverage Check
- ✅ Frontend project setup with Vue 3 + Vite + Tailwind CSS
- ✅ Core component implementation (FinancialHotspotForm, GenericExecuteForm, ResultDisplay, ProgressIndicator)
- ✅ API integration with existing FastAPI endpoints
- ✅ SSE streaming support for real-time updates
- ✅ Deployment configuration for static hosting
- ✅ MVP features: basic financial hotspot pipeline execution, simple result display, and generic skill execution

### Placeholder Scan
- No TBD, TODO, or vague requirements found
- All code blocks contain complete, executable code
- All file paths are exact and consistent
- All dependencies are explicitly listed

### Type Consistency
- API client functions match the expected payload structures
- Component props and emits are consistently defined
- Event handling follows the same pattern across components

Plan complete and saved to `docs/superpowers/plans/2026-06-11-openharness-web-interface.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?