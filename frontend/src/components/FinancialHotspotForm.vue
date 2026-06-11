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