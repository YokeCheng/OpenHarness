<template>
  <div class="home" :class="'theme-' + theme">
    <div class="home-hero">
      <div class="hero-icon">⚡</div>
      <h1>OpenHarness</h1>
      <p class="hero-sub">AI Agent 驆动的自动化平台</p>
    </div>

    <div class="home-features">
      <div class="feature-card" @click="$router.push('/chat')">
        <div class="feature-icon">🤖</div>
        <h3>智能对话</h3>
        <p>与 AI Agent 交互式对话，支持三种模式：</p>
        <div class="mode-list">
          <span class="mode-item mode-auto">⚡自动 — 直接执行</span>
          <span class="mode-item mode-plan">📋规划 — 先规划后执行</span>
          <span class="mode-item mode-default">🔒严谨 — 逐步确认</span>
        </div>
      </div>

      <div class="feature-card" @click="$router.push('/chat')">
        <div class="feature-icon">📊</div>
        <h3>财经热点生图</h3>
        <p>输入财经主题，自动生成专业的财经分析文章和信息长图。</p>
      </div>
    </div>

    <div class="home-guide">
      <h2>使用说明</h2>
      <ol>
        <li>确保 OpenHarness 后端正在运行（端口 8002）</li>
        <li>点击「智能对话」进入聊天界面</li>
        <li>使用 <kbd>Tab</kbd> 切换交互模式（自动/规划/严谨）</li>
        <li>输入消息开始对话</li>
      </ol>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HomeView',
  data() {
    return {
      theme: localStorage.getItem('oh-theme') || 'dark',
    }
  },
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  padding: 40px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.home-hero {
  text-align: center;
  margin-bottom: 32px;
}
.hero-icon { font-size: 64px; }
.home-hero h1 { color: var(--t1); font-size: 32px; margin: 8px 0 4px; }
.hero-sub { color: var(--t2); font-size: 16px; }

.home-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 600px;
  margin: 0 auto 32px;
}
.feature-card {
  background: var(--mb);
  border: 1px solid var(--b);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.feature-card:hover { border-color: var(--acc); }
.feature-icon { font-size: 28px; margin-bottom: 8px; }
.feature-card h3 { color: var(--t1); font-size: 16px; margin-bottom: 4px; }
.feature-card p { color: var(--t2); font-size: 13px; line-height: 1.4; }

.mode-list {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.mode-item {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}
.mode-auto { background: #1a3a1a; color: #4caf50; }
.mode-plan { background: #2a3a5a; color: #8ab4f8; }
.mode-default { background: var(--errb); color: var(--err); }

.home-guide {
  max-width: 600px;
  margin: 0 auto;
  background: var(--mb);
  border-radius: 12px;
  padding: 16px;
}
.home-guide h2 { color: var(--t1); font-size: 16px; margin-bottom: 12px; }
.home-guide ol { color: var(--t2); font-size: 13px; line-height: 1.6; }
kbd {
  padding: 1px 4px;
  border: 1px solid var(--b);
  border-radius: 3px;
  font-size: 11px;
  background: var(--kbdb);
}

/* Dark theme */
.theme-dark {
  --b: #2a2a4a; --t1: #e0e0e0; --t2: #a0a0b0;
  --mb: #1e1e3a; --acc: #6c63ff; --err: #ff6b6b; --errb: #2a1a1a;
  --kbdb: #2a2a4a;
  background: #0f0f23; color: #e0e0e0;
}
.theme-light {
  --b: #e0e0e0; --t1: #1a1a1a; --t2: #666;
  --mb: #f0f0f0; --acc: #4f46e5; --err: #dc2626; --errb: #fef2f2;
  --kbdb: #f0f0f0;
  background: #fafafa; color: #1a1a1a;
}
</style>