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