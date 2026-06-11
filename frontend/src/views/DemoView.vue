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