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