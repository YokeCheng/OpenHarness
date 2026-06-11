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