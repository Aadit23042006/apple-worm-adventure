// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  AuthExpiredError,
  REFRESH_KEY,
  SESSION_EXPIRED_EVENT,
  TOKEN_KEY,
  TOKEN_UPDATED_EVENT,
  request,
} from './authClient'

type Call = { url: string; auth: string | null }

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status })

let calls: Call[]
let handler: (url: string, auth: string | null) => Promise<Response> | Response

beforeEach(() => {
  localStorage.clear()
  calls = []
  vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
    const auth = new Headers(init.headers).get('Authorization')
    calls.push({ url, auth })
    return handler(url, auth)
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const events = () => {
  const seen: string[] = []
  const rec = (n: string) => () => seen.push(n)
  window.addEventListener(SESSION_EXPIRED_EVENT, rec('expired'))
  window.addEventListener(TOKEN_UPDATED_EVENT, rec('updated'))
  return seen
}

describe('authClient.request', () => {
  it('sends the Token header and returns data on success', async () => {
    handler = () => json(200, { ok: true })
    const out = await request<{ ok: boolean }>('/x/', {}, 'T1')
    expect(out.ok).toBe(true)
    expect(calls[0].auth).toBe('Token T1')
  })

  it('uses the refreshed token for the retry and stores it (#6)', async () => {
    localStorage.setItem(TOKEN_KEY, 'OLD')
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = (url, auth) => {
      if (url.endsWith('/auth/refresh/'))
        return json(200, { token: 'NEW', refresh_token: 'R1' })
      return auth === 'Token NEW' ? json(200, { ok: true }) : json(401, { detail: 'Invalid token.' })
    }

    await request('/games/s/checkpoint/', { method: 'POST', body: '{}' }, 'OLD')

    expect(calls.map((c) => c.auth)).toEqual(['Token OLD', null, 'Token NEW'])
    expect(localStorage.getItem(TOKEN_KEY)).toBe('NEW')
  })

  it('prefers a newer stored token over a stale captured one, without refreshing', async () => {
    localStorage.setItem(TOKEN_KEY, 'FRESH')
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = (_u, auth) =>
      auth === 'Token FRESH' ? json(200, { ok: true }) : json(401, { detail: 'Invalid token.' })

    await request('/y/', {}, 'STALE')

    expect(calls.map((c) => c.auth)).toEqual(['Token STALE', 'Token FRESH'])
    expect(calls.some((c) => c.url.endsWith('/auth/refresh/'))).toBe(false)
  })

  it('ends the session when the refresh token is rejected', async () => {
    localStorage.setItem(TOKEN_KEY, 'OLD')
    localStorage.setItem(REFRESH_KEY, 'R1')
    const seen = events()
    handler = (url) =>
      url.endsWith('/auth/refresh/')
        ? json(401, { detail: 'Refresh token invalid or expired.' })
        : json(401, { detail: 'Invalid token.' })

    await expect(request('/z/', {}, 'OLD')).rejects.toBeInstanceOf(AuthExpiredError)

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull()
    expect(seen).toContain('expired')
  })

  it.each([429, 500, 503])(
    'keeps the session when refresh fails transiently (HTTP %i)',
    async (status) => {
      localStorage.setItem(TOKEN_KEY, 'OLD')
      localStorage.setItem(REFRESH_KEY, 'R1')
      const seen = events()
      seen.length = 0
      handler = (url) =>
        url.endsWith('/auth/refresh/') ? json(status, {}) : json(401, { detail: 'Invalid token.' })

      const err = await request('/z/', {}, 'OLD').catch((e) => e)

      expect(err).toBeInstanceOf(Error)
      expect(err).not.toBeInstanceOf(AuthExpiredError)
      expect(localStorage.getItem(TOKEN_KEY)).toBe('OLD')
      expect(localStorage.getItem(REFRESH_KEY)).toBe('R1')
      expect(seen).not.toContain('expired')
    },
  )

  it('keeps the session when the refresh request cannot reach the server', async () => {
    localStorage.setItem(TOKEN_KEY, 'OLD')
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = (url) => {
      if (url.endsWith('/auth/refresh/')) throw new TypeError('network down')
      return json(401, { detail: 'Invalid token.' })
    }

    const err = await request('/z/', {}, 'OLD').catch((e) => e)

    expect(err).not.toBeInstanceOf(AuthExpiredError)
    expect(localStorage.getItem(REFRESH_KEY)).toBe('R1')
  })

  it('never loops: original + one refresh + one retry, then ends the session', async () => {
    localStorage.setItem(TOKEN_KEY, 'OLD')
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = (url) =>
      url.endsWith('/auth/refresh/')
        ? json(200, { token: 'STILL_BAD', refresh_token: 'R1' })
        : json(401, { detail: 'Invalid token.' })

    await expect(request('/z/', {}, 'OLD')).rejects.toBeInstanceOf(AuthExpiredError)

    expect(calls).toHaveLength(3)
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
  })

  it('shares one refresh between concurrent requests', async () => {
    localStorage.setItem(TOKEN_KEY, 'OLD')
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = async (url, auth) => {
      if (url.endsWith('/auth/refresh/'))
        return json(200, { token: 'NEW', refresh_token: 'R2' })
      return auth === 'Token NEW' ? json(200, { ok: true }) : json(401, { detail: 'Invalid token.' })
    }

    await Promise.all([request('/a/', {}, 'OLD'), request('/b/', {}, 'OLD'), request('/c/', {}, 'OLD')])

    expect(calls.filter((c) => c.url.endsWith('/auth/refresh/'))).toHaveLength(1)
    expect(localStorage.getItem(REFRESH_KEY)).toBe('R2')
  })

  it('does not refresh when skipRefresh is set', async () => {
    localStorage.setItem(REFRESH_KEY, 'R1')
    handler = () => json(401, { detail: 'Invalid token.' })

    await expect(request('/z/', { skipRefresh: true }, 'OLD')).rejects.toThrow('Invalid token.')
    expect(calls).toHaveLength(1)
  })

  it('surfaces non-auth errors without touching tokens (#15: failed save is an error, never success)', async () => {
    localStorage.setItem(TOKEN_KEY, 'T')
    localStorage.setItem(REFRESH_KEY, 'R')
    handler = () => json(400, { detail: 'Illegal move.' })

    await expect(request('/games/s/checkpoint/', { method: 'POST', body: '{}' }, 'T')).rejects.toThrow('Illegal move.')
    expect(localStorage.getItem(TOKEN_KEY)).toBe('T')
    expect(calls).toHaveLength(1)
  })
})
