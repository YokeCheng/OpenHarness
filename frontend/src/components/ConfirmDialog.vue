<template>
  <div class="dialog-overlay">
    <div class="dialog-box" :class="'dialog-' + dialog.type">
      <!-- Permission dialog -->
      <template v-if="dialog.type === 'permission'">
        <div class="dialog-title">🔧 工具调用确认</div>
        <div class="dialog-body">
          <div class="dialog-tool-name">{{ dialog.data.tool_name }}</div>
          <div class="dialog-description">{{ dialog.data.description }}</div>
        </div>
        <div class="dialog-actions">
          <button class="btn-allow" @click="respond(true)">✅ 允许 (Y)</button>
          <button class="btn-always" @click="respondAlways()">✅ 总是允许 (A)</button>
          <button class="btn-deny" @click="respond(false)">❌ 拒绝 (N)</button>
        </div>
      </template>

      <!-- Question / plan dialog -->
      <template v-if="dialog.type === 'question'">
        <div class="dialog-title">📋 {{ dialog.data.title || '确认执行计划' }}</div>
        <div class="dialog-body">
          <div v-if="dialog.data.description" class="dialog-description">{{ dialog.data.description }}</div>
          <div v-if="dialog.data.options && dialog.data.options.length" class="dialog-options">
            <div v-for="(group, gi) in optionGroups" :key="gi" class="option-group">
              <div class="option-group-label">{{ group.label }}</div>
              <div class="option-choices">
                <button
                  v-for="opt in group.items"
                  :key="opt.value"
                  class="option-chip"
                  :class="{ selected: selectedAnswers[group.label] === opt.value }"
                  @click="selectOption(group.label, opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn-confirm" @click="confirmPlan()">确认执行</button>
          <button class="btn-cancel" @click="cancelDialog()">取消</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmDialog',
  props: {
    dialog: { type: Object, required: true },
  },
  emits: ['respond'],
  data() {
    return {
      selectedAnswers: {},
    }
  },
  computed: {
    optionGroups() {
      // Group options by category if they have a group field
      // Otherwise, put all options in one group
      const opts = this.dialog.data.options || []
      if (!opts.length) return []
      // Simple: treat each option as a selectable choice
      return [{
        label: '选择方案',
        items: opts,
      }]
    },
  },
  methods: {
    respond(allowed) {
      this.$emit('respond', {
        request_id: this.dialog.request_id,
        type: 'permission_response',
        allowed,
        answer: allowed ? 'y' : 'n',
      })
    },
    respondAlways() {
      this.$emit('respond', {
        request_id: this.dialog.request_id,
        type: 'permission_response',
        allowed: true,
        answer: 'a',
      })
    },
    selectOption(groupLabel, value) {
      this.selectedAnswers = { ...this.selectedAnswers, [groupLabel]: value }
    },
    confirmPlan() {
      // Send all selected answers
      const answers = Object.values(this.selectedAnswers)
      const answer = answers.length ? answers.join(',') : ''
      this.$emit('respond', {
        request_id: this.dialog.request_id,
        type: 'question_response',
        answer,
        allowed: true,
      })
    },
    cancelDialog() {
      this.$emit('respond', {
        request_id: this.dialog.request_id,
        type: this.dialog.type === 'permission' ? 'permission_response' : 'question_response',
        allowed: false,
        answer: '',
      })
    },
  },
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dialog-box {
  background: var(--mod);
  border: 1px solid var(--b);
  border-radius: 12px;
  padding: 20px;
  min-width: 360px;
  max-width: 520px;
  max-height: 80vh;
  overflow-y: auto;
}
.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin-bottom: 12px;
}
.dialog-body {
  margin-bottom: 16px;
}
.dialog-tool-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--tbt);
  padding: 4px 8px;
  background: var(--tbb);
  border-radius: 4px;
  margin-bottom: 8px;
}
.dialog-description {
  font-size: 13px;
  color: var(--t2);
  line-height: 1.4;
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.btn-allow, .btn-always, .btn-confirm {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
}
.btn-allow { background: #4caf50; color: #fff; }
.btn-always { background: #2196f3; color: #fff; }
.btn-confirm { background: var(--acc); color: #fff; }
.btn-deny, .btn-cancel {
  padding: 8px 16px;
  border: 1px solid var(--b);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  background: transparent;
  color: var(--t2);
  font-family: inherit;
}
.btn-deny:hover { background: var(--errb); color: var(--err); }
.btn-cancel:hover { background: var(--hov); }

/* Question dialog specific */
.dialog-options {
  margin-top: 12px;
}
.option-group {
  margin-bottom: 12px;
}
.option-group-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--t1);
  margin-bottom: 6px;
}
.option-choices {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.option-chip {
  padding: 6px 12px;
  border: 1px solid var(--b);
  border-radius: 6px;
  background: var(--btn);
  color: var(--t1);
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: all 0.15s;
}
.option-chip:hover { background: var(--hov); }
.option-chip.selected {
  border-color: var(--acc);
  background: var(--hov);
}

/* Theme variables */
</style>