import { fetchEventSource, type EventSourceMessage } from '@microsoft/fetch-event-source'

export interface StreamEvent {
  event: string
  data: Record<string, unknown>
}

export interface OpenStreamOptions {
  path: string
  method?: 'GET' | 'POST'
  body?: Record<string, unknown>
  signal?: AbortSignal
  onEvent: (event: StreamEvent) => void
}

export async function openJsonEventStream(options: OpenStreamOptions) {
  await fetchEventSource(`/api/v1${options.path}`, {
    method: options.method ?? 'GET',
    credentials: 'include',
    headers: {
      Accept: 'text/event-stream',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
    async onopen(response) {
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }
    },
    onmessage(message: EventSourceMessage) {
      if (!message.event || !message.data) return
      const parsed = JSON.parse(message.data) as Record<string, unknown>
      options.onEvent({
        event: message.event,
        data: parsed,
      })
    },
  })
}
