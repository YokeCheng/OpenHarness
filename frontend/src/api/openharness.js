// src/api/openharness.js
import axios from 'axios'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: '/api/v1', // Will be proxied to backend in development
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Financial Hotspot Pipeline API
export const executeFinancialHotspotPipeline = async (payload) => {
  try {
    const response = await apiClient.post('/financial-hotspot-pipeline', payload)
    return response.data
  } catch (error) {
    throw error.response?.data || error
  }
}

// Generic Execute API
export const executeGeneric = async (payload) => {
  try {
    const response = await apiClient.post('/execute', payload)
    return response.data
  } catch (error) {
    throw error.response?.data || error
  }
}

// Health Check API
export const healthCheck = async () => {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error) {
    throw error.response?.data || error
  }
}

// SSE Streaming helper
export const createSSEConnection = (endpoint, payload) => {
  // For POST requests with SSE, we need to use a different approach
  // since EventSource only supports GET requests
  // We'll implement a custom SSE client using fetch and ReadableStream

  const url = `${window.location.origin}/api/v1${endpoint}`

  return {
    start: async (onMessage, onError, onComplete) => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        const processStream = async () => {
          try {
            const { done, value } = await reader.read()

            if (done) {
              onComplete?.()
              return
            }

            buffer += decoder.decode(value, { stream: true })

            // Process complete lines
            const lines = buffer.split('\n')
            buffer = lines.pop() // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.substring(6))
                  onMessage?.(data)
                } catch (e) {
                  console.warn('Failed to parse SSE data:', line, e)
                }
              }
            }

            // Continue reading
            processStream()
          } catch (error) {
            onError?.(error)
          }
        }

        processStream()

        return {
          close: () => reader.cancel()
        }
      } catch (error) {
        onError?.(error)
        return null
      }
    }
  }
}

export default apiClient