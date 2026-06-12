import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' }
})

export const healthCheck = () => apiClient.get('/health').then(r => r.data)

export function chatStream(prompt, options = {}) {
  const payload = {
    prompt,
    model: options.model || null,
    max_turns: options.maxTurns || null,
    permission_mode: options.permissionMode || 'full_auto',
  }
  return fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function sendChatResponse(requestId, type, answer, allowed) {
  const payload = {
    request_id: requestId,
    type,
    answer: answer || null,
    allowed: allowed || null,
  }
  return apiClient.post('/chat/response', payload).then(r => r.data)
}

export default apiClient