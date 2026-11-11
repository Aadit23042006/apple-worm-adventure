/*
 * Central API client + token lifecycle.
 *
 * Single source of truth for the access token is localStorage[TOKEN_KEY].
 * A token that a caller captured earlier (React state, closure, queued
 * checkpoint) is only a hint: on a 401 the client first checks whether a
 * newer token has been stored, then tries ONE refresh, then retries ONCE.
 *
 * Failure policy:
 *   - refresh rejected (400/401/403)  -> session is really over: clear storage,
 *                                        emit SESSION_EXPIRED_EVENT, throw AuthExpiredError
 *   - refresh unreachable / 5xx / 429 -> transient: keep tokens, throw a retryable error
 *   - retry still 401                 -> token is genuinely invalid: end session
 * There is never a retry loop and never a fabricated success.
 */

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || '/api'
).replace(/\/$/, '')

export const TOKEN_KEY = 'veloop_auth_token'
export const REFRESH_KEY = 'veloop_refresh_token'

export const SESSION_EXPIRED_EVENT = 'veloop:session-expired'
export const TOKEN_UPDATED_EVENT = 'veloop:token-updated'

export const SESSION_EXPIRED_MESSAGE =
  'Your session has expired. Please log in again.'

export type RequestOptions = RequestInit & {
  skipRefresh?: boolean
}

export class AuthExpiredError extends Error {
  constructor(message = SESSION_EXPIRED_MESSAGE) {
    super(message)
    this.name = 'AuthExpiredError'
  }
}

export function getStoredToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

function emit(name: string, detail?: unknown) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(name, { detail }))
  }
}

export function endSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  } catch {
    /* storage unavailable */
  }
  emit(SESSION_EXPIRED_EVENT)
}

type RefreshResult =
  | { status: 'ok'; token: string }
  | { status: 'expired' }
  | { status: 'unavailable' }

let refreshPromise: Promise<RefreshResult> | null = null

export function refreshAccessToken(): Promise<RefreshResult> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async (): Promise<RefreshResult> => {
    try {
      const refreshToken = localStorage.getItem(REFRESH_KEY)

      if (!refreshToken) {
        return { status: 'expired' }
      }

      let response: Response

      try {
        response = await fetch(`${API_BASE}/auth/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
      } catch {
        return { status: 'unavailable' }
      }

      if (!response.ok) {
        // Only a definitive rejection ends the session.
        return [400, 401, 403].includes(response.status)
          ? { status: 'expired' }
          : { status: 'unavailable' }
      }

      let data: { token?: string; refresh_token?: string } = {}

      try {
        data = JSON.parse((await response.text()) || '{}')
      } catch {
        data = {}
      }

      const token = String(data.token || '').trim()
      const rotated = String(data.refresh_token || '').trim()

      if (!token || !rotated) {
        return { status: 'expired' }
      }

      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(REFRESH_KEY, rotated)
      emit(TOKEN_UPDATED_EVENT, { token })

      return { status: 'ok', token }
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
  token?: string,
): Promise<T> {
  const { skipRefresh = false, ...fetchOptions } = options

  const send = async (accessToken?: string): Promise<Response> => {
    const headers = new Headers(fetchOptions.headers)

    if (fetchOptions.body) {
      headers.set('Content-Type', 'application/json')
    }

    if (accessToken) {
      headers.set('Authorization', `Token ${accessToken}`)
    }

    try {
      return await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers })
    } catch {
      throw new Error(
        'Unable to reach the game server. Check that Docker backend is running.',
      )
    }
  }

  let sentToken = token
  let response = await send(sentToken)

  if (
    response.status === 401 &&
    sentToken &&
    !skipRefresh &&
    path !== '/auth/refresh/'
  ) {
    // 1. A newer token may already be stored (another request or tab refreshed).
    const latest = getStoredToken()

    if (latest && latest !== sentToken) {
      sentToken = latest
      response = await send(sentToken)
      if (response.ok) {
        emit(TOKEN_UPDATED_EVENT, { token: latest })
      }
    }

    // 2. Still unauthorized: one refresh, one retry.
    if (response.status === 401) {
      const refreshed = await refreshAccessToken()

      if (refreshed.status === 'expired') {
        endSession()
        throw new AuthExpiredError()
      }

      if (refreshed.status === 'unavailable') {
        throw new Error(
          'Could not refresh your session right now. Please try again.',
        )
      }

      response = await send(refreshed.token)

      // 3. Fresh token also rejected: the credentials are really invalid.
      if (response.status === 401) {
        endSession()
        throw new AuthExpiredError()
      }
    }
  }

  const text = await response.text()
  let data: any = {}

  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { detail: text || 'Request failed' }
  }

  if (!response.ok) {
    const first = Array.isArray(data)
      ? data[0]
      : data.detail || Object.values(data).flat?.()[0]

    throw new Error(String(first || `Request failed (${response.status})`))
  }

  return data as T
}
