<template>
  <div class="chat-app" :class="'theme-' + theme">
    <!-- Header -->
    <header class="chat-header">
      <span class="header-title">⚡ OpenHarness Chat</span>
      <span class="header-mode" :class="'mode-' + currentMode" @click="showModePicker = !showModePicker">{{ modeLabel }}</span>
      <span class="header-status">{{ connected ? '● 已连接' : '○ 未连接' }}</span>
      <div class="header-actions">
        <button @click="toggleTheme" title="切换主题">{{ theme === 'dark' ? '☀️' : '🌙' }}</button>
        <button @click="clearChat" title="清空对话">🗑</button>
      </div>
    </header>

    <!-- Messages -->
    <div class="messages" ref="msgArea">
      <div v-if="messages.length === 0 && !streaming" class="welcome">
        <div class="welcome-icon">⚡</div>
        <h2>OpenHarness Web Chat</h2>
        <p>在下方输入消息与 AI Agent 对话，或使用 / 命令</p>
        <div class="quick-btns">
          <button @click="send('帮我分析代码质量')">分析代码质量</button>
          <button @click="send('列出可用的技能和工具')">查看技能</button>
          <button @click="send('帮我写一个单元测试')">生成测试</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="msg-avatar">{{ m.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="msg-body">
          <!-- Collapsed tool cards above text -->
          <div v-if="m.cards && m.cards.length" class="msg-cards">
            <ToolCard
              v-for="card in m.cards"
              :key="card.id"
              :tool-name="card.tool_name"
              :input="card.input"
              :output="card.output"
              :is-running="card.is_running"
              :is-collapsed="card.is_collapsed"
              :is-error="card.is_error"
              @toggle="expandCard(i, card.id)"
              @collapse="collapseCard(i, card.id)"
            />
          </div>
          <div v-if="m.content" class="msg-text" v-html="md(m.content)"></div>
          <div v-if="m.error" class="msg-error">{{ m.error }}</div>
        </div>
      </div>

      <!-- Streaming message — cards + text appear here live -->
      <div v-if="streaming" class="msg assistant streaming-msg">
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
          <!-- Live tool cards during execution -->
          <div v-if="activeCards.length" class="msg-cards">
            <ToolCard
              v-for="card in activeCards"
              :key="card.id"
              :tool-name="card.tool_name"
              :input="card.input"
              :output="card.output"
              :is-running="card.is_running"
              :is-collapsed="card.is_collapsed"
              :is-error="card.is_error"
              @toggle="expandActiveCard(card.id)"
              @collapse="collapseActiveCard(card.id)"
            />
          </div>
          <div v-if="streamBuf" class="msg-text" v-html="md(streamBuf)"></div>
          <div v-if="!streamBuf && !activeCards.length" class="msg-text"><span class="dots">思考中...</span></div>
        </div>
      </div>

      <!-- Pending dialog (permission_request or question_request) -->
      <ConfirmDialog
        v-if="pendingDialog"
        :dialog="pendingDialog"
        @respond="respondToDialog"
      />
    </div>

    <!-- Mode picker overlay -->
    <ModePicker
      v-if="showModePicker"
      :current-mode="currentMode"
      @select="switchMode"
      @close="showModePicker = false"
    />

    <!-- Status -->
    <div class="status-bar">
      <span>{{ connected ? '✅ 已连接' : '❌ 后端未连接 (端口 8002)' }}</span>
      <span>{{ modeLabel }}</span>
      <span v-if="tokensIn">↑{{ tokensIn }}</span>
      <span v-if="tokensOut">↓{{ tokensOut }}</span>
      <span v-if="streaming && activeCards.length">🔧 {{ activeCards[activeCards.length - 1].tool_name }}</span>
      <span v-if="streaming && !activeCards.length">⏳ 思考中</span>
    </div>

    <!-- Input -->
    <div class="input-area">
      <div v-if="cmdPicker" class="cmd-picker">
        <div v-for="(c, i) in cmdList" :key="c"
             class="cmd-item" :class="{ sel: i === cmdIdx }"
             @click="pickCmd(c)" @mouseenter="cmdIdx = i">
          <b>{{ c }}</b> <span>{{ cmdDesc[c] || '' }}</span>
        </div>
      </div>
      <div class="input-row">
        <textarea v-model="text" ref="inputEl"
                  @keydown="onKey" @input="onInput"
                  @compositionstart="isComposing = true"
                  @compositionend="isComposing = false"
                  placeholder="输入消息... (Enter 发送, Shift+Enter 换行, / 命令)"
                  rows="1"></textarea>
        <button @click="send(text)" class="send-btn" :disabled="!text.trim() || streaming">
          {{ streaming ? '⏳' : '➤' }}
        </button>
      </div>
      <div class="hints">
        <kbd>Enter</kbd> 发送 · <kbd>Shift+Enter</kbd> 换行 · <kbd>/</kbd> 命令 · <kbd>↑↓</kbd> 历史 · <kbd>Tab</kbd> 切换模式
      </div>
    </div>
  </div>
</template>

<script>
import { chatStream, healthCheck, sendChatResponse } from '@/api/openharness.js'
import ToolCard from '@/components/ToolCard.vue'
import ModePicker from '@/components/ModePicker.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const CMDS = ['/help','/clear','/theme','/model','/provider','/permissions','/stop','/health','/skills','/tools','/cost','/plan']
const CMD_DESC = {
  '/help':'帮助','/clear':'清空','/theme':'主题','/model':'模型','/provider':'Provider',
  '/permissions':'权限','/stop':'停止','/health':'健康检查','/skills':'技能','/tools':'工具','/cost':'成本','/plan':'切换规划模式'
}

const MODE_LABELS = {
  default: '🔒严谨',
  plan: '📋规划',
  full_auto: '⚡自动',
}

function md(t) {
  if (!t) return ''
  return t
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>')
}

let cardIdCounter = 0

export default {
  name: 'ChatView',
  components: { ToolCard, ModePicker, ConfirmDialog },
  data() {
    return {
      theme: localStorage.getItem('oh-theme') || 'dark',
      connected: false,
      messages: [],
      text: '',
      streaming: false,
      isComposing: false,  // IME composition state
      streamBuf: '',
      activeCards: [],  // Tool cards during current streaming turn
      currentMode: 'full_auto',
      showModePicker: false,
      pendingDialog: null,  // { request_id, type, data }
      tokensIn: 0,
      tokensOut: 0,
      history: [],
      histIdx: -1,
      cmdPicker: false,
      cmdList: [],
      cmdIdx: 0,
      cmdDesc: CMD_DESC,
    }
  },
  computed: {
    modeLabel() {
      return MODE_LABELS[this.currentMode] || '⚡自动'
    },
  },
  mounted() { this.ping() },
  methods: {
    md,
    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('oh-theme', this.theme)
    },
    clearChat() { this.messages = []; this.activeCards = [] },
    async ping() {
      try { await healthCheck(); this.connected = true }
      catch { this.connected = false }
    },
    scroll() {
      this.$nextTick(() => { if (this.$refs.msgArea) this.$refs.msgArea.scrollTop = this.$refs.msgArea.scrollHeight })
    },
    // Mode switching
    switchMode(mode) {
      this.currentMode = mode
      this.showModePicker = false
    },
    // Card expand/collapse
    expandCard(msgIndex, cardId) {
      const cards = this.messages[msgIndex].cards
      const card = cards.find(c => c.id === cardId)
      if (card) card.is_collapsed = false
    },
    collapseCard(msgIndex, cardId) {
      const cards = this.messages[msgIndex].cards
      const card = cards.find(c => c.id === cardId)
      if (card) card.is_collapsed = true
    },
    expandActiveCard(cardId) {
      const card = this.activeCards.find(c => c.id === cardId)
      if (card) card.is_collapsed = false
    },
    collapseActiveCard(cardId) {
      const card = this.activeCards.find(c => c.id === cardId)
      if (card) card.is_collapsed = true
    },
    // Input handlers
    onInput() {
      const v = this.text.trim()
      if (v.startsWith('/') && !this.streaming) {
        this.cmdList = CMDS.filter(c => c.startsWith(v))
        this.cmdPicker = this.cmdList.length > 0
        this.cmdIdx = 0
      } else { this.cmdPicker = false }
      const el = this.$refs.inputEl
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    },
    onKey(e) {
      // Skip events during IME composition (Chinese/Japanese/Korean input)
      if (this.isComposing || e.isComposing || e.keyCode === 229) return
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(this.text); return }
      if (e.key === 'Escape') { this.cmdPicker = false; this.showModePicker = false; if (this.streaming) this.stop(); return }
      if (e.key === 'Tab') {
        e.preventDefault()
        if (this.cmdPicker) { this.pickCmd(this.cmdList[this.cmdIdx]); return }
        // Tab on empty input → toggle mode picker
        if (!this.text.trim()) { this.showModePicker = !this.showModePicker; return }
      }
      if (e.key === 'ArrowUp' && this.text === '') { e.preventDefault(); this.histNav(-1); return }
      if (e.key === 'ArrowDown') { e.preventDefault(); this.histNav(1); return }
      if (e.key === 'ArrowUp' && this.cmdPicker) { e.preventDefault(); this.cmdIdx = Math.max(0, this.cmdIdx - 1); return }
      if (e.key === 'ArrowDown' && this.cmdPicker) { e.preventDefault(); this.cmdIdx = Math.min(this.cmdList.length - 1, this.cmdIdx + 1); return }
    },
    histNav(d) {
      if (!this.history.length) return
      this.histIdx = Math.max(-1, Math.min(this.history.length - 1, this.histIdx + d))
      this.text = this.histIdx === -1 ? '' : this.history[this.history.length - 1 - this.histIdx]
    },
    pickCmd(c) { this.text = c + ' '; this.cmdPicker = false; this.$refs.inputEl?.focus() },
    send(raw) {
      const t = (raw || '').trim()
      if (!t || this.streaming) return
      this.text = ''
      this.cmdPicker = false
      if (this.$refs.inputEl) this.$refs.inputEl.style.height = 'auto'

      // Local commands
      if (t.startsWith('/')) {
        this.history.push(t)
        this.histIdx = -1
        if (t === '/clear') { this.messages = []; this.activeCards = []; return }
        if (t === '/help') { this.messages.push({ role:'system', content: Object.entries(CMD_DESC).map(([c,d]) => `${c} — ${d}`).join('\n') }); this.scroll(); return }
        if (t === '/theme') { this.toggleTheme(); this.messages.push({ role:'system', content: `主题: ${this.theme}` }); this.scroll(); return }
        if (t === '/health') { this.ping(); this.messages.push({ role:'system', content: this.connected ? '✅ 已连接' : '❌ 未连接' }); this.scroll(); return }
        if (t === '/plan') { this.switchMode(this.currentMode === 'plan' ? 'full_auto' : 'plan'); this.messages.push({ role:'system', content: `模式: ${this.modeLabel}` }); this.scroll(); return }
        // Forward other commands to backend
      }

      this.history.push(t)
      this.histIdx = -1
      this.messages.push({ role: 'user', content: t })
      this.scroll()
      this.stream(t)
    },
    async stream(prompt) {
      this.streaming = true
      this.streamBuf = ''
      this.activeCards = []
      try {
        const res = await chatStream(prompt, { permissionMode: this.currentMode })
        if (!res.ok) { this.messages.push({ role: 'system', error: `HTTP ${res.status}` }); this.streaming = false; return }
        const reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buf += dec.decode(value, { stream: true })
            const lines = buf.split('\n')
            buf = lines.pop()
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue
              try { this.onEvent(JSON.parse(line.slice(6))) } catch {}
            }
          }
        } finally {
          reader.releaseLock()
        }
        // Only flush if streamBuf wasn't already flushed by turn_complete
        if (this.streamBuf || this.activeCards.length) {
          this._flushStreamBuf()
        }
      } catch (e) { this.messages.push({ role: 'system', error: e.message }) }
      this.streaming = false
      this.streamBuf = ''
      this.activeCards = []
      this.scroll()
    },
    _flushStreamBuf() {
      // Flush streamBuf into a final message with collapsed cards
      if (this.streamBuf) {
        const collapsedCards = this.activeCards.map(c => ({ ...c, is_running: false, is_collapsed: true }))
        this.messages.push({
          role: 'assistant',
          content: this.streamBuf,
          cards: collapsedCards,
        })
        this.streamBuf = ''
      } else if (this.activeCards.length) {
        // Cards but no text — still need to finalize
        const collapsedCards = this.activeCards.map(c => ({ ...c, is_running: false, is_collapsed: true }))
        this.messages.push({
          role: 'assistant',
          content: '',
          cards: collapsedCards,
        })
      }
      this.activeCards = []
    },
    onEvent(ev) {
      const d = ev.data
      const t = ev.event
      // Text streaming
      if (t === 'text_delta') { this.streamBuf += d.text || '' }
      // Tool calls — create/update active cards
      else if (t === 'tool_start') {
        // Flush text before card appears
        if (this.streamBuf) {
          this.messages.push({ role: 'assistant', content: this.streamBuf })
          this.streamBuf = ''
        }
        const card = {
          id: ++cardIdCounter,
          tool_name: d.tool_name || 'tool',
          input: d.tool_input || null,
          output: null,
          is_running: true,
          is_collapsed: false,
          is_error: false,
        }
        this.activeCards.push(card)
        this.scroll()
      }
      else if (t === 'tool_complete') {
        // Find the running card and update it
        const card = this.activeCards.find(c => c.tool_name === d.tool_name && c.is_running)
        if (card) {
          card.output = d.output || ''
          card.is_running = false
          card.is_error = d.is_error || false
        }
        this.scroll()
      }
      // Turn complete — collapse all active cards, flush text
      else if (t === 'turn_complete') {
        this._flushStreamBuf()
        if (d.usage) { this.tokensIn += d.usage.input_tokens || 0; this.tokensOut += d.usage.output_tokens || 0 }
      }
      // Permission request — show dialog
      else if (t === 'permission_request') {
        this.pendingDialog = {
          request_id: d.request_id,
          type: 'permission',
          data: d,
        }
        this.scroll()
      }
      // Question request — show plan dialog
      else if (t === 'question_request') {
        this.pendingDialog = {
          request_id: d.request_id,
          type: 'question',
          data: d,
        }
        this.scroll()
      }
      // Status/error/compact
      else if (t === 'status') { this.messages.push({ role: 'system', content: d.message }); this.scroll() }
      else if (t === 'error') { this.messages.push({ role: 'system', error: d.message }); this.scroll() }
      else if (t === 'compact_progress') { /* skip */ }
      else if (t === 'execution_complete') { this._flushStreamBuf() }
      else if (t === 'execution_error') { this.messages.push({ role: 'system', error: d.message || '执行错误' }) }
      this.scroll()
    },
    // Respond to a pending dialog (permission or question)
    respondToDialog(response) {
      sendChatResponse(response.request_id, response.type, response.answer, response.allowed)
      this.pendingDialog = null
    },
    stop() {
      this.streaming = false
      if (this.streamBuf) {
        const collapsedCards = this.activeCards.map(c => ({
          ...c,
          is_running: false,
          is_collapsed: true,
          output: c.output || '(已中断)',
        }))
        this.messages.push({ role: 'assistant', content: this.streamBuf + '\n_(已中断)_', cards: collapsedCards })
        this.streamBuf = ''
      }
      this.activeCards = []
    },
  },
}
</script>

<style scoped>
.chat-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.chat-header {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--b);
  background: var(--hdr);
}
.header-title { font-weight: 700; color: var(--t1); font-size: 16px; }
.header-mode {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}
.header-mode.mode-default { background: var(--errb); color: var(--err); border: 1px solid var(--err); }
.header-mode.mode-plan { background: #2a3a5a; color: #8ab4f8; border: 1px solid #8ab4f8; }
.header-mode.mode-full_auto { background: #1a3a1a; color: #4caf50; border: 1px solid #4caf50; }
.header-status { font-size: 12px; color: var(--t2); }
.header-actions { margin-left: auto; display: flex; gap: 8px; }
.header-actions button {
  width: 32px; height: 32px; border: none; background: transparent;
  color: var(--t2); cursor: pointer; border-radius: 6px; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.welcome { text-align: center; padding: 48px 20px; }
.welcome-icon { font-size: 56px; }
.welcome h2 { color: var(--t1); margin: 8px 0; }
.welcome p { color: var(--t2); }
.quick-btns { display: flex; gap: 10px; justify-content: center; margin-top: 16px; flex-wrap: wrap; }
.quick-btns button {
  padding: 8px 14px; border: 1px solid var(--b); background: var(--btn);
  color: var(--t1); border-radius: 8px; cursor: pointer; font-size: 13px;
}
.msg { display: flex; gap: 10px; margin-bottom: 14px; max-width: 80%; }
.msg.user { margin-left: auto; flex-direction: row-reverse; }
.msg.system { max-width: 100%; }
.msg.assistant { max-width: 90%; }
.msg-avatar {
  width: 32px; height: 32px; display: flex; align-items: center;
  justify-content: center; border-radius: 6px; background: var(--av); flex-shrink: 0;
}
.msg-body { flex: 1; min-width: 0; }
.msg-cards {
  margin-bottom: 6px;
}
.msg-text {
  background: var(--mb); padding: 10px 14px; border-radius: 10px;
  color: var(--t1); line-height: 1.5; word-break: break-word;
}
.msg.user .msg-text { background: var(--umb); color: var(--umt); }
.msg-text :deep(pre) { background: var(--cb); padding: 8px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }
.msg-text :deep(code) { font-family: 'SF Mono', Menlo, monospace; font-size: 13px; }
.msg-text :deep(strong) { font-weight: 600; }
.msg-error { color: var(--err); background: var(--errb); padding: 6px 10px; border-radius: 6px; }
.dots { animation: pulse 1.4s infinite; }
@keyframes pulse { 0%,100%{opacity:.2} 50%{opacity:1} }
.streaming-msg .msg-text { border-left: 2px solid var(--acc); }

.status-bar {
  padding: 4px 16px; font-size: 12px; color: var(--t3);
  border-top: 1px solid var(--b); background: var(--stb);
  display: flex;
  gap: 8px;
}

.input-area {
  padding: 10px 16px; border-top: 1px solid var(--b); background: var(--iba);
}
.cmd-picker {
  background: var(--mod); border: 1px solid var(--b); border-radius: 8px;
  padding: 6px; margin-bottom: 8px; max-height: 200px; overflow-y: auto;
}
.cmd-item { padding: 6px 8px; border-radius: 4px; cursor: pointer; color: var(--t1); display: flex; gap: 10px; }
.cmd-item.sel { background: var(--hov); }
.cmd-item b { min-width: 80px; }
.cmd-item span { color: var(--t2); font-size: 12px; }

.input-row { display: flex; gap: 8px; align-items: flex-end; }
textarea {
  flex: 1; padding: 8px 10px; border: 1px solid var(--b);
  background: var(--inp); color: var(--t1); border-radius: 8px;
  font-size: 14px; resize: none; outline: none; font-family: inherit; line-height: 1.4;
}
textarea:focus { border-color: var(--acc); }
.send-btn {
  width: 36px; height: 36px; border: none; background: var(--acc);
  color: #fff; border-radius: 8px; cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}
.send-btn:disabled { background: var(--dis); cursor: not-allowed; }
.hints { font-size: 11px; color: var(--t3); margin-top: 4px; }
kbd { padding: 1px 4px; border: 1px solid var(--b); border-radius: 3px; font-size: 11px; background: var(--kbdb); }

/* Dark */
.theme-dark {
  --b: #2a2a4a; --hdr: #16213e; --t1: #e0e0e0; --t2: #a0a0b0; --t3: #606080;
  --av: #2a2a4a; --mb: #1e1e3a; --umb: #3a5a8a; --umt: #fff;
  --cb: #0d0d1a; --mod: #22223a; --inp: #1e1e3a; --iba: #12122a; --stb: #12122a;
  --btn: #2a2a4a; --hov: #3a3a5a; --dis: #2a2a3a;
  --tbb: #4a3a2a; --tbt: #d4a060; --kbdb: #2a2a4a;
  --tcb: #1a1a30;
  --acc: #6c63ff; --err: #ff6b6b; --errb: #2a1a1a;
  background: #0f0f23; color: #e0e0e0;
}
/* Light */
.theme-light {
  --b: #e0e0e0; --hdr: #fff; --t1: #1a1a1a; --t2: #666; --t3: #999;
  --av: #e8e8e8; --mb: #f0f0f0; --umb: #3a5a8a; --umt: #fff;
  --cb: #f5f5f5; --mod: #fff; --inp: #fff; --iba: #fafafa; --stb: #fafafa;
  --btn: #f0f0f0; --hov: #e0e0e0; --dis: #d0d0d0;
  --tbb: #f0e8d0; --tbt: #8a6a3a; --kbdb: #f0f0f0;
  --tcb: #e8e8e8;
  --acc: #4f46e5; --err: #dc2626; --errb: #fef2f2;
  background: #fafafa; color: #1a1a1a;
}
</style>