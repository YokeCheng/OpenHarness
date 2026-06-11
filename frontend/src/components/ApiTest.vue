// src/components/ApiTest.vue
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