<template>
  <div class="tool-card" :class="{ collapsed: isCollapsed, running: isRunning, error: isError }" @click="toggleCollapse">
    <!-- Collapsed view — one-line summary -->
    <div v-if="isCollapsed" class="card-summary">
      <span class="card-icon">{{ icon }}</span>
      <span class="card-label">{{ summaryLabel }}</span>
      <span v-if="isError" class="card-error-tag">✗</span>
    </div>

    <!-- Expanded / running view -->
    <div v-else class="card-expanded">
      <div class="card-header">
        <span class="card-icon">{{ icon }}</span>
        <span class="card-badge">{{ toolName }}</span>
        <span v-if="isRunning" class="card-spinner">⏳</span>
        <span v-if="isError" class="card-error-tag">✗ 失败</span>
      </div>
      <div v-if="truncatedInput" class="card-input">
        <div class="card-section-label">输入</div>
        <pre>{{ truncatedInput }}</pre>
      </div>
      <div v-if="!isRunning && truncatedOutput" class="card-output">
        <div class="card-section-label">输出</div>
        <pre>{{ truncatedOutput }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
const TOOL_ICONS = {
  file_read: '📄',
  file_write: '✏️',
  file_edit: '✏️',
  shell_exec: '💻',
  search: '🔍',
  grep: '🔍',
  web_fetch: '🌐',
  web_search: '🔎',
  notebook_edit: '📊',
  agent_spawn: '🐝',
}

function getToolIcon(toolName) {
  return TOOL_ICONS[toolName] || '🔧'
}

function makeSummaryLabel(toolName, input) {
  // Create a one-line summary like "📄 Read src/main.py"
  if (!input) return toolName
  const str = typeof input === 'string' ? input : JSON.stringify(input)
  // Extract meaningful short info
  if (str.includes('file_path') || str.includes('path')) {
    try {
      const obj = typeof input === 'object' ? input : JSON.parse(input)
      const fp = obj.file_path || obj.path || ''
      if (fp) return fp.split('/').pop()
    } catch {}
  }
  if (str.includes('command')) {
    try {
      const obj = typeof input === 'object' ? input : JSON.parse(input)
      const cmd = obj.command || ''
      if (cmd) return cmd.slice(0, 40)
    } catch {}
  }
  // Fallback: first 40 chars
  return str.slice(0, 40)
}

export default {
  name: 'ToolCard',
  props: {
    toolName: { type: String, required: true },
    input: { type: [String, Object, Array], default: null },
    output: { type: String, default: null },
    isRunning: { type: Boolean, default: false },
    isCollapsed: { type: Boolean, default: false },
    isError: { type: Boolean, default: false },
  },
  emits: ['toggle'],
  computed: {
    icon() {
      return getToolIcon(this.toolName)
    },
    truncatedInput() {
      if (!this.input) return null
      const str = typeof this.input === 'string' ? this.input : JSON.stringify(this.input, null, 2)
      return str.length > 200 ? str.slice(0, 200) + '…' : str
    },
    truncatedOutput() {
      if (!this.output) return null
      return this.output.length > 300 ? this.output.slice(0, 300) + '…' : this.output
    },
    summaryLabel() {
      return makeSummaryLabel(this.toolName, this.input)
    },
  },
  methods: {
    toggleCollapse() {
      if (this.isCollapsed) {
        this.$emit('toggle', this.toolName)
      }
    },
  },
}
</script>

<style scoped>
.tool-card {
  margin: 6px 0;
  border-radius: 8px;
  border: 1px solid var(--b);
  background: var(--tcb);
  transition: all 0.2s ease;
  cursor: default;
}
.tool-card.collapsed {
  cursor: pointer;
  padding: 4px 10px;
}
.tool-card.collapsed:hover {
  background: var(--hov);
}

.card-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--t2);
}
.card-icon { font-size: 14px; }
.card-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-error-tag { color: var(--err); font-weight: bold; font-size: 12px; }

.card-expanded {
  padding: 8px 12px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.card-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--tbb);
  color: var(--tbt);
  font-weight: 500;
}
.card-spinner {
  animation: pulse 1.4s infinite;
}
@keyframes pulse { 0%,100%{opacity:.2} 50%{opacity:1} }

.card-input, .card-output {
  margin-top: 4px;
}
.card-section-label {
  font-size: 11px;
  color: var(--t3);
  margin-bottom: 2px;
}
.card-input pre, .card-output pre {
  background: var(--cb);
  padding: 6px 8px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  margin: 0;
  max-height: 120px;
  overflow-y: auto;
}

/* Theme variables — injected from parent ChatView */
</style>