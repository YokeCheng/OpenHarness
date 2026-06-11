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