<template>
  <div class="mode-picker-overlay" @click.self="$emit('close')">
    <div class="mode-picker">
      <div class="picker-title">选择交互模式</div>
      <div class="mode-options">
        <button
          class="mode-option"
          :class="{ active: currentMode === 'default' }"
          @click="$emit('select', 'default')"
        >
          <span class="mode-icon">🔒</span>
          <span class="mode-label">严谨模式</span>
          <span class="mode-desc">每个工具调用都需要确认</span>
        </button>
        <button
          class="mode-option"
          :class="{ active: currentMode === 'plan' }"
          @click="$emit('select', 'plan')"
        >
          <span class="mode-icon">📋</span>
          <span class="mode-label">规划模式</span>
          <span class="mode-desc">先规划再执行，交互确认</span>
        </button>
        <button
          class="mode-option"
          :class="{ active: currentMode === 'full_auto' }"
          @click="$emit('select', 'full_auto')"
        >
          <span class="mode-icon">⚡</span>
          <span class="mode-label">自动模式</span>
          <span class="mode-desc">自动执行所有工具调用</span>
        </button>
      </div>
      <div class="picker-hint">按 <kbd>Tab</kbd> 快速切换 · 按 <kbd>Esc</kbd> 关闭</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ModePicker',
  props: {
    currentMode: { type: String, required: true },
  },
  emits: ['select', 'close'],
}
</script>

<style scoped>
.mode-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mode-picker {
  background: var(--mod);
  border: 1px solid var(--b);
  border-radius: 12px;
  padding: 16px;
  min-width: 320px;
  max-width: 400px;
}
.picker-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin-bottom: 12px;
}
.mode-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mode-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--b);
  background: var(--btn);
  color: var(--t1);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-family: inherit;
}
.mode-option:hover { background: var(--hov); }
.mode-option.active {
  border-color: var(--acc);
  background: var(--hov);
}
.mode-icon { font-size: 20px; }
.mode-label { font-size: 14px; font-weight: 500; }
.mode-desc { font-size: 12px; color: var(--t2); }
.picker-hint {
  font-size: 11px;
  color: var(--t3);
  margin-top: 10px;
}
kbd {
  padding: 1px 4px;
  border: 1px solid var(--b);
  border-radius: 3px;
  font-size: 11px;
  background: var(--kbdb);
}

/* Theme variables inherited from parent */
.theme-dark {
  --b: #2a2a4a; --mod: #22223a; --t1: #e0e0e0; --t2: #a0a0b0; --t3: #606080;
  --btn: #2a2a4a; --hov: #3a3a5a; --kbdb: #2a2a4a;
  --acc: #6c63ff;
}
.theme-light {
  --b: #e0e0e0; --mod: #fff; --t1: #1a1a1a; --t2: #666; --t3: #999;
  --btn: #f0f0f0; --hov: #e0e0e0; --kbdb: #f0f0f0;
  --acc: #4f46e5;
}
</style>