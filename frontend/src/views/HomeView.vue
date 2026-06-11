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