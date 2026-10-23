/**
 * The case assistant (backend/chat, its own service on port 8001; the dev server forwards /api/chat to it).
 *
 * Not sent through request(): a failure here means only the assistant is down, and must not flag the whole
 * backend as unreachable in the connection banner.
 */
import { getAuthToken } from './client'

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatAnswer {
  answer: string
  complaint_id: string | null
  cost_myr: string
  latency_ms: number
  model: string
}

export class ChatError extends Error {}

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export const chatApi = {
  async ask(body: { question: string; complaint_id: string | null; history: ChatTurn[] }): Promise<ChatAnswer> {
    const token = getAuthToken()
    let response: Response
    try {
      response = await fetch(`${BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      })
    } catch {
      throw new ChatError('The assistant is not reachable. Start it with chat.bat.')
    }
    const json = response.headers.get('content-type')?.includes('application/json') ?? false
    if (!response.ok) {
      if (!json || response.status >= 502) throw new ChatError('The assistant is not running. Start it with chat.bat.')
      const detail = ((await response.json()) as { detail?: unknown }).detail
      throw new ChatError(typeof detail === 'string' ? detail : `The assistant could not answer (${response.status}).`)
    }
    return (await response.json()) as ChatAnswer
  },
}
