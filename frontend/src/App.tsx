import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import type { ReactNode, TouchEvent } from 'react'

import {
  Apple,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Coins,
  Crown,
  Bug,
  Gamepad2,
  Heart,
  Lightbulb,
  LogIn,
  LogOut,
  RotateCcw,
  Sparkles,
  Trophy,
  Undo2,
  Volume2,
  VolumeX,
  X,
  Zap,
} from 'lucide-react'

import './styles.css'
import { GAME_NAME } from './config/gameConfig'

import {
  TOKEN_KEY,
  REFRESH_KEY,
  SESSION_EXPIRED_EVENT,
  SESSION_EXPIRED_MESSAGE,
  TOKEN_UPDATED_EVENT,
  getStoredToken,
  request,
} from './authClient'
const SESSION_KEY = 'veloop_active_session'

type Player = {
  id: number
  username: string
  email: string
  coins: number
  total_score: number
  email_verified?: boolean
}

type Screen =
  | 'home'
  | 'login'
  | 'register'
  | 'game'
  | 'levels'
  | 'leaderboard'
  | 'wallet'
  | 'achievements'
  | 'verify-email'
  | 'forgot-password'
  | 'reset-password'

type Pos = {
  r: number
  c: number
}

type LevelObjective = {
  id: string
  type: string
  title: string
  required: boolean
  target?: number
}

type Level = {
  number: number
  unlocked: boolean
  completed: boolean
  stars: number
  best_score: number
  best_moves: number | null
  objectives: LevelObjective[]
}

type GameState = {
  worm: Pos[]
  apples: Pos[]
  obstacles: Pos[]
  portal: Pos
  moves: number
  score: number
  failed: boolean
  failedMove: Pos | null
  completed: boolean
  started: number
  revives: number
  hints: number
  boosters: number
  extraMoves: number
}

const dirs: Record<string, Pos> = {
  up: { r: -1, c: 0 },
  down: { r: 1, c: 0 },
  left: { r: 0, c: -1 },
  right: { r: 0, c: 1 },
}

function same(a: Pos, b: Pos) {
  return a.r === b.r && a.c === b.c
}


function hasRequiredCoreObjectives(
  objectives: LevelObjective[],
) {
  if (!Array.isArray(objectives) || objectives.length === 0) {
    return false
  }

  const required = objectives.filter(
    (objective) => objective && objective.required === true,
  )

  // Collecting every apple and reaching the portal are mandatory game rules.
  // Fail closed if the server omits or misconfigures either objective.
  return (
    required.some((objective) => objective.type === 'collect_apples') &&
    required.some((objective) => objective.type === 'reach_portal')
  )
}

function objectivesSatisfied(
  game: GameState,
  objectives: LevelObjective[],
) {
  if (!hasRequiredCoreObjectives(objectives)) {
    return false
  }

  const required = objectives.filter(
    (objective) => objective && objective.required === true,
  )

  return required.every((objective) => {
    if (objective.type === 'collect_apples') {
      return game.apples.length === 0
    }
    if (objective.type === 'reach_portal') {
      // A portal touch is not a win until every apple has been collected.
      return (
        game.apples.length === 0 &&
        same(game.worm[0], game.portal)
      )
    }
    if (objective.type === 'move_limit') {
      return (
        game.moves <=
        (objective.target || 0) +
          game.extraMoves
      )
    }
    if (objective.type === 'no_revive') {
      return game.revives === 0
    }
    return false
  })
}

function starsFor(g: GameState) {
  const threshold = Math.max(
    1,
    10 + g.apples.length * 3,
  )

  return g.revives === 0 &&
    g.moves <= threshold
    ? 3
    : g.revives === 0
      ? 2
      : 1
}

export default function App() {
  const [screen, setScreen] =
    useState<Screen>('home')

  const [player, setPlayer] =
    useState<Player | null>(null)

  const [token, setToken] =
    useState(
      () =>
        localStorage.getItem(
          TOKEN_KEY,
        ) || '',
    )

  // A successful login/register response already includes the player. Avoid
  // issuing a redundant /auth/me request for that same freshly-issued token.
  // Reloads and cross-tab token changes still follow the normal restore path.
  const authCompletedTokenRef = useRef('')
  const registrationTokenRef = useRef('')

  const [api, setApi] =
    useState('checking')

  const [error, setError] =
    useState('')

  const [notice, setNotice] =
    useState('')

  const [verificationStatus, setVerificationStatus] =
    useState<'loading' | 'success' | 'error'>('loading')

  const [verificationMessage, setVerificationMessage] =
    useState('')

  const [resetToken, setResetToken] = useState('')

  const [levels, setLevels] =
    useState<Level[]>([])

  const [
    levelsLoading,
    setLevelsLoading,
  ] = useState(false)

  const [
    levelsError,
    setLevelsError,
  ] = useState('')

  const [levelNo, setLevelNo] =
    useState(1)

  const [game, setGame] =
    useState<GameState | null>(null)

  const [gameObjectives, setGameObjectives] =
    useState<LevelObjective[]>([])

  const [session, setSession] =
    useState('')

  const [wallet, setWallet] =
    useState<any>(null)

  const [loading, setLoading] =
    useState(false)

  const audio =
    useRef<AudioContext | null>(
      null,
    )

  const musicTimer =
    useRef<number | null>(null)

  const [musicOn, setMusicOn] =
    useState(() => localStorage.getItem('veloop_music_enabled') === 'true')

  const [soundOn, setSoundOn] =
    useState(() => localStorage.getItem('veloop_sound_enabled') !== 'false')

  const [hintDirection, setHintDirection] =
    useState('')

  const history =
    useRef<GameState[]>([])

  // Serialize checkpoint writes so rapid keyboard/touch input cannot arrive out of order.
  const checkpointChain = useRef<Promise<unknown>>(Promise.resolve())

  // Prevent overlapping move calculations while a checkpoint is being saved.
  // Without this guard, rapid keyboard/touch events can calculate the same
  // next move from a stale React state snapshot.
  const moveInFlight = useRef(false)

  // Invalidates queued writes when a new session/reward-authoritative state replaces
  // the current checkpoint. This prevents stale requests from mutating a newer game.
  const checkpointEpoch = useRef(0)

  /*
   * PASSWORD RESET LINK
   * The backend emails /reset-password/?token=... .
   * Keep the token in component state and remove it from the address bar
   * only after a successful reset.
   */
  useEffect(() => {
    const pathName = window.location.pathname.replace(/\/+$/, '')
    if (pathName !== '/reset-password') return

    const params = new URLSearchParams(window.location.search)
    const value = (params.get('token') || '').trim()
    setResetToken(value)
    window.history.replaceState({}, document.title, '/reset-password/')
    setScreen('reset-password')
    if (!value) {
      setError('This password-reset link is missing its token. Request a new link.')
    }
  }, [])

  /*
   * EMAIL VERIFICATION LINK
   *
   * The backend emails users a link such as:
   * /verify-email/?token=...
   *
   * This effect reads the token from the URL,
   * verifies it through the backend, and then
   * gives the player a clear success/error state.
   */
  useEffect(() => {
    const pathName =
      window.location.pathname.replace(/\/+$/, '')

    if (pathName !== '/verify-email') {
      return
    }

    const params =
      new URLSearchParams(
        window.location.search,
      )

    const verificationToken =
      (
        params.get('token') || ''
      ).trim()

    setScreen('verify-email')

    if (!verificationToken) {
      setVerificationStatus('error')
      setVerificationMessage(
        'Verification link is missing its token.',
      )
      return
    }

    let alive = true

    setVerificationStatus('loading')
    setVerificationMessage(
      'Verifying your email address...',
    )

    request<any>(
      '/auth/verify-email/',
      {
        method: 'POST',
        body: JSON.stringify({
          token: verificationToken,
        }),
      },
    )
      .then((response) => {
        if (!alive) return

        if (response?.verified) {
          setVerificationStatus('success')

          setVerificationMessage(
            response.already_verified
              ? 'Your email address is already verified. You can log in now.'
              : 'Your email address has been verified successfully. You can log in now.',
          )

          window.history.replaceState(
            {},
            document.title,
            '/verify-email/',
          )

          return
        }

        setVerificationStatus('error')
        setVerificationMessage(
          response?.detail ||
            'Email verification could not be completed.',
        )
      })
      .catch((err) => {
        if (!alive) return

        setVerificationStatus('error')

        setVerificationMessage(
          err instanceof Error
            ? err.message
            : 'This verification link is invalid or has expired.',
        )
      })

    return () => {
      alive = false
    }
  }, [])

  /*
   * Backend health check.
   *
   * This endpoint does not require
   * authentication.
   */
  useEffect(() => {
    let alive = true

    const check = () => {
      request<any>('/health/')
        .then(() => {
          if (alive) {
            setApi('online')
          }
        })
        .catch(() => {
          if (alive) {
            setApi('offline')
          }
        })
    }

    check()

    const id =
      window.setInterval(
        check,
        10000,
      )

    return () => {
      alive = false
      window.clearInterval(id)
    }
  }, [])

  /*
   * AUTH SYNCHRONISATION
   *
   * authClient.ts owns the token lifecycle. React only mirrors it:
   *  - a refresh elsewhere updates the token held in state,
   *  - a definitive auth failure (or a logout in another tab) returns the
   *    player to the login screen instead of leaving a dead session on screen.
   */
  useEffect(() => {
    const onTokenUpdated = (e: Event) => {
      const next = String(
        (e as CustomEvent<{ token?: string }>).detail?.token || '',
      )
      if (next) setToken(next)
    }

    const onSessionExpired = () => {
      setToken('')
      setPlayer(null)
      setScreen('login')
      setError(SESSION_EXPIRED_MESSAGE)
    }

    const onStorage = (e: StorageEvent) => {
      if (e.key !== TOKEN_KEY) return
      if (e.newValue) {
        setToken(e.newValue)
      } else {
        onSessionExpired()
      }
    }

    window.addEventListener(TOKEN_UPDATED_EVENT, onTokenUpdated)
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
    window.addEventListener('storage', onStorage)

    return () => {
      window.removeEventListener(TOKEN_UPDATED_EVENT, onTokenUpdated)
      window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  /*
   * SESSION RESTORE
   *
   * First use the stored access token.
   *
   * If it has expired, request()
   * automatically uses the refresh token.
   *
   * Only if refresh also fails do
   * we finally send the user to login.
   */
  useEffect(() => {
    let alive = true

    if (!token) {
      setPlayer(null)
      return
    }

    if (authCompletedTokenRef.current === token) {
      authCompletedTokenRef.current = ''
      return
    }

    request<{ user: Player }>(
      '/auth/me/',
      {},
      token,
    )
      .then((x) => {
        if (!alive) return

        setPlayer(x.user)

        /*
         * request() may have refreshed
         * the access token.
         *
         * Synchronize React state with
         * the latest localStorage token.
         */
        const latestToken =
          localStorage.getItem(
            TOKEN_KEY,
          )

        if (
          latestToken &&
          latestToken !== token
        ) {
          setToken(latestToken)
        }
      })
      .catch((e) => {
        if (!alive) return

        /*
         * authClient owns definitive session expiry and emits
         * SESSION_EXPIRED_EVENT only when credentials are rejected.
         * A network error, 429, or server 5xx must not erase otherwise
         * valid local credentials or force an avoidable logout.
         */
        setError(
          e instanceof Error
            ? e.message
            : 'Unable to restore your session. Please try again.',
        )
      })

    return () => {
      alive = false
    }
  }, [token])

  const loadLevels =
    async (accessToken = token) => {
      if (!accessToken) return

      setLevelsLoading(true)
      setLevelsError('')

      try {
        const x =
          await request<{
            levels: Level[]
          }>(
            '/levels/',
            {},
            accessToken,
          )

        setLevels(x.levels)
      } catch (e) {
        setLevels([])

        setLevelsError(
          e instanceof Error
            ? e.message
            : 'Unable to load levels.',
        )
      } finally {
        setLevelsLoading(false)
      }
    }

  useEffect(() => {
    if (token) {
      void loadLevels()
    }
  }, [token])

  useEffect(() => {
    if (!token || screen === 'game' || game) return

    // A newly registered account cannot have an active game yet. Avoid an
    // unnecessary authenticated request during the critical registration →
    // level-selection transition. Normal login/reload still restores games.
    if (registrationTokenRef.current === token) {
      registrationTokenRef.current = ''
      return
    }

    let alive = true

    const restoreActiveGame = async () => {
      try {
        const result = await request<any>('/games/active/', {}, token)
        if (!alive || !result.active || !result.session?.state) return

        const active = result.session
        if (!hasRequiredCoreObjectives(active.objectives)) {
          throw new Error('Server returned incomplete objectives for the active level.')
        }
        const restored = active.state as GameState
        const activeObjectives = Array.isArray(active.objectives)
          ? active.objectives
          : []

        setSession(active.sessionId)
        setLevelNo(Number(active.level))
        setGameObjectives(activeObjectives)
        setGame(restored)
        setScreen('game')
        setHintDirection('')
        localStorage.setItem(SESSION_KEY, active.sessionId)

        // Recovery for the narrow case where the final portal checkpoint was
        // saved but the browser refreshed/closed before POST /complete/ ran.
        // The backend still validates the stored checkpoint and owns all
        // progression/reward decisions.
        const portalCompletionPending =
          restored.apples.length === 0 &&
          Array.isArray(restored.worm) &&
          restored.worm.length > 0 &&
          same(restored.worm[0], restored.portal) &&
          objectivesSatisfied(restored, activeObjectives)

        if (portalCompletionPending) {
          try {
            const completion = await request<any>(
              `/games/${active.sessionId}/complete/`,
              { method: 'POST' },
              token,
            )
            if (!alive) return

            const completedState: GameState = {
              ...restored,
              completed: true,
              score: Number(completion.score ?? restored.score),
            }
            setGame(completedState)
            localStorage.removeItem(SESSION_KEY)
            setSession('')
            await loadLevels(token)
            if (!alive) return
            setPlayer((playerState) =>
              playerState
                ? {
                    ...playerState,
                    coins: playerState.coins + Number(completion.coins || 0),
                    total_score: playerState.total_score + Number(completion.score || 0),
                  }
                : playerState,
            )
            setNotice(
              `Level ${active.level} complete. Level ${Number(active.level) + 1} is unlocked.`,
            )
          } catch (completionError) {
            if (alive) {
              setError(
                completionError instanceof Error
                  ? `Portal completion is awaiting server confirmation: ${completionError.message}`
                  : 'Portal completion is awaiting server confirmation. Please retry.',
              )
            }
          }
        } else {
          setNotice(`Resumed Level ${active.level} · Moves ${active.moves} · Score ${active.score}`)
        }
      } catch {
        // A missing/expired active session should not block normal level selection.
      }
    }

    void restoreActiveGame()

    return () => {
      alive = false
    }
  }, [token])

  useEffect(() => {
    localStorage.setItem('veloop_sound_enabled', String(soundOn))
  }, [soundOn])

  useEffect(() => {
    localStorage.setItem('veloop_music_enabled', String(musicOn))
  }, [musicOn])

  const sound = (
    freq = 520,
  ) => {
    if (!soundOn) return
    try {
      audio.current ??=
        new AudioContext()

      const o =
        audio.current.createOscillator()

      const g =
        audio.current.createGain()

      o.frequency.value = freq
      g.gain.value = 0.035

      o.connect(g)
      g.connect(
        audio.current.destination,
      )

      o.start()

      o.stop(
        audio.current.currentTime +
          0.09,
      )
    } catch {
      // Audio is optional.
    }
  }

  const stopMusic = () => {
    if (musicTimer.current !== null) {
      window.clearInterval(
        musicTimer.current,
      )
      musicTimer.current = null
    }
    setMusicOn(false)
    localStorage.setItem('veloop_music_enabled', 'false')
  }

  const startMusic = () => {
    try {
      audio.current ??=
        new AudioContext()

      void audio.current.resume()

      if (musicTimer.current !== null) {
        setMusicOn(true)
        return
      }

      const notes = [
        261.63,
        329.63,
        392.0,
        329.63,
        293.66,
        349.23,
        440.0,
        349.23,
      ]
      let step = 0

      const playNote = () => {
        if (!audio.current) return

        const oscillator =
          audio.current.createOscillator()
        const gain =
          audio.current.createGain()

        oscillator.type = 'sine'
        oscillator.frequency.value =
          notes[step % notes.length]
        gain.gain.setValueAtTime(0.012, audio.current.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.0001, audio.current.currentTime + 0.35)

        oscillator.connect(gain)
        gain.connect(audio.current.destination)
        oscillator.start()
        oscillator.stop(audio.current.currentTime + 0.36)
        step += 1
      }

      playNote()
      musicTimer.current =
        window.setInterval(playNote, 520)
      setMusicOn(true)
      localStorage.setItem('veloop_music_enabled', 'true')
    } catch {
      setMusicOn(false)
    }
  }

  useEffect(() => {
    return () => {
      if (musicTimer.current !== null) {
        window.clearInterval(
          musicTimer.current,
        )
      }
    }
  }, [])

  const startGame =
    async (
      n: number,
      restarting = false,
    ) => {
      const startEpoch = checkpointEpoch.current + 1
      checkpointEpoch.current = startEpoch
      checkpointChain.current = Promise.resolve()
      setError('')

      try {
        if (!token) {
          throw new Error(
            'Please log in before starting a level.',
          )
        }

        // The backend is authoritative for the initial board/state.
        // Do not send a client-generated state as the source of truth.
        const x =
          await request<any>(
            '/games/start/',
            {
              method: 'POST',
              body: JSON.stringify({
                level: n,
              }),
            },
            token,
          )

        const g = x.state as GameState
        if (
          !g ||
          !Array.isArray(g.worm) ||
          !Array.isArray(g.apples)
        ) {
          throw new Error('Server returned an invalid initial game state.')
        }

        // Restart must always receive a brand-new server-authoritative state.
        // Never silently render the previous checkpoint as a successful restart.
        if (
          restarting &&
          (g.moves !== 0 || g.score !== 0 || g.completed || g.failed)
        ) {
          throw new Error(
            `Restart was rejected: server returned Moves ${g.moves}, Score ${g.score}. The previous game state was kept.`,
          )
        }

        if (!hasRequiredCoreObjectives(x.objectives)) {
          throw new Error('Server returned incomplete level objectives. Reload the level list and try again.')
        }

        // A newer restart/start request wins. Never let an older response
        // overwrite the newer session or board.
        if (checkpointEpoch.current !== startEpoch) {
          return
        }

        if (restarting) {
          history.current = []
        }

        setSession(
          x.sessionId,
        )
        localStorage.setItem(SESSION_KEY, x.sessionId)

        setLevelNo(n)
        setGameObjectives(
          Array.isArray(x.objectives)
            ? x.objectives
            : [],
        )
        setGame(g)
        setScreen('game')
        setHintDirection('')
        setNotice(
          restarting
            ? `Level restarted · Moves ${g.moves} · Score ${g.score}`
            : '',
        )
        if (musicOn) startMusic()
        sound(660)
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : 'Unable to start level',
        )
      }
    }

  const saveCheckpoint =
    async (
      checkpointSession: string,
      checkpointToken: string,
      state: GameState,
      epoch: number,
    ) => {
      checkpointChain.current =
        checkpointChain.current
          .catch(() => undefined)
          .then(async () => {
            if (checkpointEpoch.current !== epoch) {
              return
            }

            await request(
              `/games/${checkpointSession}/checkpoint/`,
              {
                method: 'POST',
                body: JSON.stringify({
                  state,
                }),
              },
              // Always the latest stored token, never a stale captured one.
              getStoredToken() || checkpointToken,
            )
          })

      await checkpointChain.current
    }

  const finish =
    async (
      g: GameState,
      epoch = checkpointEpoch.current,
    ): Promise<boolean> => {
      const stars =
        starsFor(g)

      if (
        token &&
        session
      ) {
        try {
          // Completion is based only on the server's stored checkpoint.
          // The final move is checkpointed first; the backend then adds
          // the completion bonus and calculates authoritative stars.
          if (checkpointEpoch.current !== epoch) {
            return false
          }

          const result =
            await request<any>(
              `/games/${session}/complete/`,
              {
                method: 'POST',
              },
              token,
            )

          if (checkpointEpoch.current !== epoch) {
            return false
          }

          await loadLevels(token)
          localStorage.removeItem(SESSION_KEY)
          setSession('')

          setPlayer((p) =>
            p
              ? {
                  ...p,
                  coins:
                    p.coins +
                    (result.coins ||
                      0),
                  total_score:
                    p.total_score +
                    (result.score ||
                      0),
                }
              : p,
          )

          setNotice(
            `Level ${levelNo} complete · ${stars}★ · ${
              result.score ||
              g.score
            } points`,
          )
        } catch (e) {
          if (checkpointEpoch.current === epoch) {
            setError(
              e instanceof Error
                ? e.message
                : 'Save failed',
            )
          }
          return false
        }
      } else {
        setNotice(
          `Level ${levelNo} complete · ${stars}★ · ${g.score} points`,
        )
      }

      sound(880)
      return true
    }

  const performMove =
    async (
      name: string,
    ) => {
      if (
        !game ||
        game.failed ||
        game.completed
      ) {
        return
      }

      const moveEpoch = checkpointEpoch.current

      const d = dirs[name]

      const head =
        game.worm[0]

      const next = {
        r: head.r + d.r,
        c: head.c + d.c,
      }

      const size =
        7 +
        Math.min(
          3,
          Math.floor(
            levelNo / 12,
          ),
        )

      if (
        next.r <= 0 ||
        next.c <= 0 ||
        next.r >= size - 1 ||
        next.c >= size - 1 ||
        game.obstacles.some(
          (x) =>
            same(x, next),
        ) ||
        game.worm.some(
          (x, i) =>
            i > 0 &&
            same(x, next),
        )
      ) {
        const failedState: GameState = {
          ...game,
          moves: game.moves + 1,
          score: game.score,
          failed: true,
          completed: false,
          failedMove: { ...next },
        }

        if (token && session) {
          try {
            await saveCheckpoint(
              session,
              token,
              failedState,
              moveEpoch,
            )

            if (
              checkpointEpoch.current !==
              moveEpoch
            ) {
              return
            }
          } catch (e) {
            if (
              checkpointEpoch.current ===
              moveEpoch
            ) {
              setError(
                e instanceof Error
                  ? "Checkpoint save failed: " +
                    e.message
                  : "Checkpoint save failed.",
              )
            }
            return
          }
        }

        setGame(failedState)
        sound(130)
        return
      }

      history.current.push({
        ...game,
        worm: game.worm.map((p) => ({ ...p })),
        apples: game.apples.map((p) => ({ ...p })),
        obstacles: game.obstacles.map((p) => ({ ...p })),
        portal: { ...game.portal },
      })

      let apples =
        game.apples

      let score =
        game.score

      let worm = [
        next,
        ...game.worm,
      ]

      const ate =
        apples.findIndex(
          (a) =>
            same(a, next),
        )

      if (ate >= 0) {
        apples =
          apples.filter(
            (_, i) =>
              i !== ate,
          )

        score += 10

        if (
          apples.length === 0
        ) {
          score += 50
        }

        sound(740)
      } else {
        worm.pop()
      }

      const moves =
        game.moves + 1

      const g = {
        ...game,
        worm,
        apples,
        score,
        moves,
      }

      const objectivesComplete =
        objectivesSatisfied(
          g,
          gameObjectives,
        )

      if (objectivesComplete) {
        const final = {
          ...g,
          completed: true,
          score:
            g.score + 100,
        }

        if (
          token &&
          session
        ) {
          // Keep the board playable until the backend confirms completion.
          // A rejected completion must never leave a locally-finished session.
          setGame(g)

          try {
            // Save the legal final move as a normal checkpoint first.
            // The completion endpoint must consume that stored state.
            await saveCheckpoint(
              session,
              token,
              g,
              moveEpoch,
            )

            if (checkpointEpoch.current !== moveEpoch) {
              return
            }

            const confirmed = await finish(
              final,
              moveEpoch,
            )

            if (checkpointEpoch.current === moveEpoch) {
              setGame(confirmed ? final : g)
            }
          } catch (e) {
            if (checkpointEpoch.current === moveEpoch) {
              setGame(g)
              setError(
                e instanceof Error
                  ? `Checkpoint save failed: ${e.message}`
                  : 'Checkpoint save failed.',
              )
            }
          }
        } else {
          setGame(final)
          await finish(
            final,
            moveEpoch,
          )
        }

        return
      }

      setGame(g)
      if (ate < 0) sound(420)

      if (
        token &&
        session
      ) {
        const checkpointSession = session
        const checkpointToken = token

        try {
          await saveCheckpoint(
            checkpointSession,
            checkpointToken,
            g,
            moveEpoch,
          )

          if (checkpointEpoch.current !== moveEpoch) {
            return
          }
        } catch (e) {
          if (checkpointEpoch.current === moveEpoch) {
            setError(
              e instanceof Error
                ? `Checkpoint save failed: ${e.message}`
                : 'Checkpoint save failed.',
            )
          }
        }
      }
    }

  // Keep move processing single-flight across keyboard, touch, and button input.
  // The finally block guarantees that a failed network request cannot leave
  // movement permanently locked.
  const move = async (name: string) => {
    if (moveInFlight.current) {
      return
    }

    moveInFlight.current = true
    try {
      await performMove(name)
    } finally {
      moveInFlight.current = false
    }
  }

  useEffect(() => {
    const f = (
      e: KeyboardEvent,
    ) => {
      if (
        screen !== 'game'
      ) {
        return
      }

      const map: Record<
        string,
        string
      > = {
        ArrowUp: 'up',
        w: 'up',
        ArrowDown: 'down',
        s: 'down',
        ArrowLeft: 'left',
        a: 'left',
        ArrowRight: 'right',
        d: 'right',
      }

      if (map[e.key]) {
        e.preventDefault()
        move(map[e.key])
      }
    }

    window.addEventListener(
      'keydown',
      f,
    )

    return () =>
      window.removeEventListener(
        'keydown',
        f,
      )
  }, [screen, game])

  const restart =
    async () => {
      // startGame creates a new server session and validates that its
      // initial counters are zero before replacing the visible board.
      await startGame(levelNo, true)
    }

  const undo =
    async () => {
      if (!token || !session) {
        setNotice('Nothing to undo yet.')
        return
      }

      const undoEpoch = checkpointEpoch.current
      const undoSession = session
      const undoToken = token

      try {
        await checkpointChain.current.catch(() => undefined)

        if (checkpointEpoch.current !== undoEpoch) {
          return
        }

        const result = await request<any>(
          `/games/${undoSession}/undo/`,
          { method: 'POST' },
          undoToken,
        )

        if (checkpointEpoch.current !== undoEpoch) {
          return
        }

        const restored = result.state as GameState
        history.current.pop()
        setGame(restored)
        setHintDirection('')
        setNotice(`Undo complete · Moves ${restored.moves} · Score ${restored.score}`)
      } catch (e) {
        setNotice(
          e instanceof Error
            ? e.message
            : 'Nothing to undo yet.',
        )
      }
    }

  const reward = async (placement: string) => {
    if (!token) {
      setNotice('Create an account to use rewards.')
      return
    }

    if (!game || !game.worm.length) {
      setNotice('Start a level before requesting a reward.')
      return
    }

    // HINT is a free gameplay aid. Other placements use the server-authoritative
    // rewarded-ad lifecycle. With no external provider, local/staging may use
    // the explicit provider-free demo adapter; it is never a real advertisement.
    if (placement === 'HINT') {
      const target = game.apples[0] || game.portal
      const head = game.worm[0]
      const size = 7 + Math.min(3, Math.floor(levelNo / 12))
      const safe = Object.entries(dirs)
        .map(([direction, delta]) => ({
          direction,
          next: { r: head.r + delta.r, c: head.c + delta.c },
        }))
        .filter(({ next }) =>
          next.r > 0 && next.c > 0 &&
          next.r < size - 1 && next.c < size - 1 &&
          !game.obstacles.some((obstacle) => same(obstacle, next)) &&
          !game.worm.some((segment, index) => index > 0 && same(segment, next))
        )
        .sort((a, b) =>
          Math.abs(a.next.r - target.r) + Math.abs(a.next.c - target.c) -
          (Math.abs(b.next.r - target.r) + Math.abs(b.next.c - target.c))
        )
      const direction = safe[0]?.direction || ''
      if (!direction) {
        setNotice('No safe hint is available from this position.')
        return
      }
      setHintDirection(direction)
      setGame((current) => current ? { ...current, hints: current.hints + 1 } : current)
      setNotice(`Free hint unlocked: move ${direction.toUpperCase()}.`)
      sound(800)
      return
    }

    setLoading(true)
    try {
      const opportunity = await request<any>(
        '/economy/ad-opportunity/',
        {
          method: 'POST',
          body: JSON.stringify({
            placement,
            sessionId: session,
            metadata: { sessionId: session, levelId: levelNo },
          }),
        },
        token,
      )
      const eventId = String(opportunity.eventId || '').trim()
      if (!eventId) throw new Error('Reward opportunity was not created.')

      const started = await request<any>(
        `/economy/ad-opportunity/${encodeURIComponent(eventId)}/request/`,
        { method: 'POST' },
        token,
      )
      const launch = started.launch || {}
      if (launch.mode !== 'provider-free-demo') {
        throw new Error('No external rewarded-ad provider is configured for this environment.')
      }

      const seconds = Math.max(1, Number(launch.durationSeconds || 3))
      setNotice(`Provider-free demo reward: completing in ${seconds}s…`)
      await new Promise((resolve) => window.setTimeout(resolve, seconds * 1000))

      await request<any>(
        `/economy/ad-opportunity/${encodeURIComponent(eventId)}/provider-free-complete/`,
        { method: 'POST' },
        token,
      )

      const adStatus = await request<any>(
        `/economy/ad-opportunity/${encodeURIComponent(eventId)}/status/`,
        { method: 'GET' },
        token,
      )
      if (!(adStatus.verified === true && adStatus.status === 'VERIFIED')) {
        throw new Error('Reward verification is still pending.')
      }

      const result = await request<any>(
        '/economy/claim-reward/',
        {
          method: 'POST',
          body: JSON.stringify({ eventId, sessionId: session }),
        },
        token,
      )

      if (result.state) {
        setGame(result.state as GameState)
        history.current = []
      } else if (result.extra_moves) {
        setGame((current) => current ? { ...current, extraMoves: current.extraMoves + Number(result.extra_moves) } : current)
      } else if (result.hint) {
        setGame((current) => current ? { ...current, hints: current.hints + 1 } : current)
      } else if (placement === 'BOOSTER') {
        setGame((current) => current ? { ...current, boosters: current.boosters + 1 } : current)
      }
      if (result.balance !== undefined) {
        setWallet((current: any) => ({ ...(current || {}), coins: result.balance }))
      }
      setNotice(
        placement === 'DOUBLE_SCORE'
          ? `2× Score reward granted: +${result.amount} score.`
          : placement === 'DOUBLE_COINS'
            ? `2× Coins reward granted: +${result.amount} coins.`
            : `${placement.replaceAll('_', ' ')} reward granted successfully.`,
      )
      sound(1000)
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Reward could not be completed.')
    } finally {
      setLoading(false)
    }
  }

  const auth = async (
    mode:
      | 'login'
      | 'register',
    form: HTMLFormElement,
  ) => {
    setLoading(true)
    setError('')

    try {
      const fd =
        new FormData(form)

      const body: any = {
        username: String(
          fd.get('username'),
        ),

        password: String(
          fd.get('password'),
        ),
      }

      if (
        mode === 'register'
      ) {
        body.email = String(
          fd.get('email'),
        )
      }

      const x =
        await request<any>(
          mode === 'login'
            ? '/auth/login/'
            : '/auth/register/',
          {
            method: 'POST',
            body: JSON.stringify(
              body,
            ),
          },
        )

      if (
        x.refresh_token
      ) {
        localStorage.setItem(
          REFRESH_KEY,
          x.refresh_token,
        )
      }

      if (
        mode === 'register' &&
        x.verification_required
      ) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_KEY)
        setToken('')
        setPlayer(null)
        setNotice(
          x.email_sent
            ? 'Registration successful. Please verify your email using the verification link sent to your email address.'
            : 'Registration successful. Please verify your email before logging in.',
        )

        setScreen('login')

        return
      }

      if (
        !x.user?.email_verified
      ) {
        setNotice(
          'Registration successful. Verify your email before logging in.',
        )

        setScreen('login')

        return
      }

      const accessToken =
        String(
          x.token || '',
        ).trim()

      if (!accessToken) {
        throw new Error(
          'Login succeeded but no access token was returned by the server.',
        )
      }

      localStorage.setItem(
        TOKEN_KEY,
        accessToken,
      )

      if (
        x.refresh_token
      ) {
        localStorage.setItem(
          REFRESH_KEY,
          x.refresh_token,
        )
      }

      authCompletedTokenRef.current = accessToken
      if (mode === 'register') {
        registrationTokenRef.current = accessToken
      }
      setToken(accessToken)

      setPlayer(x.user)

      setScreen('levels')

      setNotice(
        `Welcome to ${GAME_NAME}`,
      )

      // The [token] effect performs one level-list request after this
      // successful authentication transition; do not issue a duplicate.
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Authentication failed',
      )
    } finally {
      setLoading(false)
    }
  }

  const submitPasswordReset = async (mode: 'request' | 'confirm', form: HTMLFormElement) => {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const fd = new FormData(form)
      if (mode === 'request') {
        await request<any>('/auth/password-reset/request/', {
          method: 'POST',
          body: JSON.stringify({ email: String(fd.get('email') || '').trim() }),
        })
        setNotice('If an account exists for that email, a password-reset link has been sent. Check your inbox.')
        form.reset()
      } else {
        if (!resetToken) throw new Error('This reset link is missing its token. Request a new link.')
        const password = String(fd.get('password') || '')
        const confirmation = String(fd.get('confirm_password') || '')
        if (password !== confirmation) throw new Error('The passwords do not match.')
        await request<any>('/auth/password-reset/confirm/', {
          method: 'POST',
          body: JSON.stringify({ token: resetToken, password }),
        })
        setResetToken('')
        window.history.replaceState({}, document.title, '/')
        setScreen('login')
        setNotice('Password reset successfully. Your previous sessions were signed out. Please log in with your new password.')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Password reset could not be completed.')
    } finally {
      setLoading(false)
    }
  }

  const signout =
    async () => {
      try {
        const currentToken =
          localStorage.getItem(
            TOKEN_KEY,
          )

        if (currentToken) {
          await request(
            '/auth/logout/',
            {
              method: 'POST',
              skipRefresh: true,
              body: JSON.stringify({
                refresh_token:
                  localStorage.getItem(
                    REFRESH_KEY,
                  ) || '',
              }),
            },
            currentToken,
          )
        }
      } catch {
        /*
         * Local logout must still
         * complete if the server is
         * unavailable.
         */
      }

      localStorage.removeItem(
        TOKEN_KEY,
      )

      localStorage.removeItem(
        REFRESH_KEY,
      )
      localStorage.removeItem(SESSION_KEY)

      setToken('')
      setPlayer(null)
      setGame(null)
      setSession('')
      stopMusic()
      setScreen('home')
    }

  const board = useMemo(() => {
    if (!game) {
      return null
    }

    const size =
      7 +
      Math.min(
        3,
        Math.floor(
          levelNo / 12,
        ),
      )

    return Array.from(
      {
        length: size * size,
      },
      (_, i) => {
        const p = {
          r: Math.floor(
            i / size,
          ),
          c: i % size,
        }

        const worm =
          game.worm.findIndex(
            (x) =>
              same(x, p),
          )

        const apple =
          game.apples.find(
            (x) =>
              same(x, p),
          )

        const obs =
          game.obstacles.some(
            (x) =>
              same(x, p),
          )

        return (
          <div
            key={i}
            className={`cell ${
              p.r === 0 ||
              p.c === 0 ||
              p.r === size - 1 ||
              p.c === size - 1
                ? 'wall'
                : ''
            } ${
              obs
                ? 'obstacle'
                : ''
            } ${
              worm >= 0
                ? 'worm'
                : ''
            } ${
              worm === 0
                ? 'head'
                : ''
            } ${
              apple
                ? 'apple'
                : ''
            } ${
              same(
                game.portal,
                p,
              )
                ? 'portal'
                : ''
            }`}
          >
            {worm === 0
              ? '◉'
              : worm > 0
                ? '•'
                : apple
                  ? (
                      <Apple
                        size={18}
                        fill="currentColor"
                      />
                    )
                  : same(
                        game.portal,
                        p,
                      )
                    ? '✦'
                    : ''}
          </div>
        )
      },
    )
  }, [game, levelNo])

  return (
    <div
      className="app"
      id="main-content"
      tabIndex={-1}
      onClickCapture={(event) => {
        const target = event.target as HTMLElement
        const button = target.closest('button')
        if (button && !button.disabled) sound(520)
      }}
    >
      <a className="skipLink" href="#main-content">Skip to main content</a>
      <header>
        <button
          className="brand"
          onClick={() =>
            setScreen('home')
          }
        >
          <span className="brandIcon">
            <Apple />
          </span>

          {GAME_NAME}
        </button>

        <div className="nav">
          <span
            className={`api ${api}`}
          >
            ● {api}
          </span>

          {player ? (
            <>
              <button
                onClick={() => {
                  setScreen(
                    'levels',
                  )

                  void loadLevels()
                }}
              >
                Levels
              </button>

              <button
                onClick={() =>
                  setScreen(
                    'leaderboard',
                  )
                }
              >
                Leaderboard
              </button>

              <button
                className={screen === 'achievements' ? 'navActive' : ''}
                aria-current={screen === 'achievements' ? 'page' : undefined}
                onClick={() =>
                  setScreen('achievements')
                }
              >
                <Crown size={15} />
                Achievements
              </button>

              <button
                onClick={() =>
                  setScreen(
                    'wallet',
                  )
                }
              >
                <Coins
                  size={15}
                />{' '}
                {player.coins}
              </button>

              <button
                onClick={signout}
              >
                <LogOut
                  size={15}
                />{' '}
                Sign out
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() =>
                  setScreen(
                    'login',
                  )
                }
              >
                <LogIn
                  size={15}
                />{' '}
                Login
              </button>

              <button
                className="primary"
                onClick={() =>
                  setScreen(
                    'register',
                  )
                }
              >
                Play free
              </button>
            </>
          )}
        </div>
      </header>

      {notice && (
        <div className="toast" role="status" aria-live="polite">
          {notice}

          <button
            onClick={() =>
              setNotice('')
            }
          >
            <X size={15} />
          </button>
        </div>
      )}

      {error && (
        <div className="error" role="alert" aria-live="assertive">
          {error}

          <button
            onClick={() =>
              setError('')
            }
          >
            <X size={15} />
          </button>
        </div>
      )}

      {screen === 'verify-email' && (
        <main className="section">
          <div className="card">
            <div className="eyebrow">
              {GAME_NAME}
            </div>

            <h1>Email Verification</h1>

            {verificationStatus === 'loading' && (
              <>
                <p>
                  {verificationMessage}
                </p>

                <div className="loading">
                  Verifying...
                </div>
              </>
            )}

            {verificationStatus === 'success' && (
              <>
                <p>
                  {verificationMessage}
                </p>

                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    setVerificationStatus(
                      'loading',
                    )
                    setVerificationMessage('')
                    setScreen('login')
                  }}
                >
                  Continue to Login
                </button>
              </>
            )}

            {verificationStatus === 'error' && (
              <>
                <p>
                  {verificationMessage}
                </p>

                <button
                  type="button"
                  onClick={() =>
                    setScreen('login')
                  }
                >
                  Back to Login
                </button>
              </>
            )}
          </div>
        </main>
      )}

      {screen === 'forgot-password' && (
        <PasswordReset
          mode="request"
          busy={loading}
          submit={submitPasswordReset}
          back={() => setScreen('login')}
        />
      )}

      {screen === 'reset-password' && (
        <PasswordReset
          mode="confirm"
          busy={loading}
          submit={submitPasswordReset}
          back={() => setScreen('login')}
        />
      )}

      {screen === 'home' && (
        <Home
          start={() =>
            player
              ? startGame(
                  levelNo,
                )
              : setScreen(
                  'register',
                )
          }
        />
      )}

      {(screen === 'login' ||
        screen === 'register') && (
        <Auth
          mode={screen}
          busy={loading}
          submit={auth}
          forgot={() => { setError(''); setScreen('forgot-password') }}
        />
      )}

      {screen === 'levels' && (
        <LevelSelect
          levels={levels}
          loading={
            levelsLoading
          }
          error={levelsError}
          retry={loadLevels}
          play={startGame}
        />
      )}

      {screen === 'game' &&
        game && (
          <GameView
            game={game}
            objectives={gameObjectives}
            levelNo={levelNo}
            board={board!}
            move={move}
            restart={restart}
            undo={undo}
            reward={reward}
            loading={loading}
            hintDirection={hintDirection}
            musicOn={musicOn}
            toggleMusic={musicOn ? stopMusic : startMusic}
            soundOn={soundOn}
            toggleSound={() => setSoundOn((enabled) => !enabled)}
            back={() =>
              setScreen(
                'levels',
              )
            }
            nextLevel={() => {
              if (levelNo < 60) {
                void startGame(levelNo + 1)
              } else {
                setScreen('levels')
                void loadLevels()
              }
            }}
            retryCompletion={async () => {
              if (!game || game.failed || !objectivesSatisfied(game, gameObjectives)) return
              const finalState: GameState = {
                ...game,
                completed: true,
                score: game.score + 100,
              }
              const confirmed = await finish(finalState, checkpointEpoch.current)
              if (confirmed) setGame(finalState)
            }}
          />
        )}

      {screen === 'leaderboard' && (
        <DataPage
          title="Leaderboard"
          icon={<Trophy />}
          load={async (signal) => {
            const response = await request<any>('/leaderboard/', { signal }, token)
            if (!Array.isArray(response?.leaderboard)) {
              throw new Error('The leaderboard response was invalid. Please try again.')
            }
            return response.leaderboard.map((entry: any, index: number) => ({
              rank: index + 1,
              ...entry,
            }))
          }}
          emptyMessage="No leaderboard scores yet. Complete a level to earn a score and appear here."
        />
      )}

      {screen === 'wallet' && (
        <Wallet
          token={token}
          onLoad={setWallet}
          data={wallet}
        />
      )}

      {screen === 'achievements' && (
        <DataPage
          title="Achievements"
          icon={<Crown />}
          load={async (signal) => {
            const response = await request<any>('/achievements/', { signal }, token)
            if (!Array.isArray(response?.achievements)) {
              throw new Error('The achievements response was invalid. Please try again.')
            }
            return response.achievements
          }}
          emptyMessage="No achievements are available yet. Please check back later."
          emptyHint="Your unlocked achievements will appear here as you play."
          onBack={() => setScreen(game ? 'game' : 'home')}
          backLabel={game ? 'Back to Game' : 'Back to Dashboard'}
        />
      )}

      <footer>
        {GAME_NAME} · VELoop Full Stack
        Game · 60 levels · responsive web
        gameplay
      </footer>
    </div>
  )
}

function Home({
  start,
}: {
  start: () => void
}) {
  return (
    <>
    <main className="hero">
      <div>
        <div className="eyebrow">
          <Sparkles size={15} />{' '}
          PUZZLE · GROW · ESCAPE
        </div>

        <h1>
          Think ahead.
          <br />
          <span>Grow smarter.</span>
        </h1>

        <p>
          Guide your worm through
          handcrafted grid puzzles,
          collect every apple, avoid
          danger, and reach the portal.
          Earn stars, score and VELoop
          rewards as you progress.
        </p>

        <div className="actions">
          <button
            className="primary big"
            onClick={start}
          >
            Start Adventure{' '}
            <Gamepad2 />
          </button>

          <a
            className="exploreLink"
            href="#features"
            aria-controls="features"
          >
            Explore features
            <ArrowDown size={16} aria-hidden="true" />
          </a>
        </div>
      </div>

      <div className="heroCard">
        <div className="miniTop">
          {GAME_NAME}{' '}
          <b>60 LEVELS</b>
        </div>

        <div className="miniGrid">
          {Array.from(
            { length: 49 },
            (_, i) => (
              <div
                key={i}
                className={`miniCell ${
                  [
                    0, 1, 2, 3, 4,
                    5, 6, 7, 13,
                    14, 20, 21, 27,
                    28, 34, 35, 41,
                    42, 43, 44, 45,
                    46, 47, 48,
                  ].includes(i)
                    ? 'wall'
                    : ''
                } ${
                  [8, 9, 10].includes(
                    i,
                  )
                    ? 'worm'
                    : ''
                } ${
                  i === 18
                    ? 'apple'
                    : ''
                } ${
                  i === 40
                    ? 'portal'
                    : ''
                }`}
              >
                {i === 18 ? <Apple size={15} aria-label="Apple" /> : i === 40 ? '✦' : ''}
              </div>
            ),
          )}
        </div>

        <div className="miniStats">
          <span><Apple size={13} aria-hidden="true" /> Apples</span>
          <span><Bug size={13} aria-hidden="true" /> Growth</span>
          <span>✦ Portal</span>
        </div>
      </div>
    </main>

    <section
      id="features"
      className="featuresSection"
      aria-labelledby="features-title"
    >
      <div className="featuresHeading">
        <div className="eyebrow">MADE FOR CURIOUS MINDS</div>
        <h2 id="features-title">Explore the features</h2>
        <p>
          A puzzle adventure with persistent progress, thoughtful challenges,
          and player-focused features already built into the game.
        </p>
      </div>

      <div className="featuresGrid">
        <article className="featureCard">
          <span className="featureIcon"><Gamepad2 aria-hidden="true" /></span>
          <h3>60 puzzle levels</h3>
          <p>Work through 60 progressively arranged grid levels, with level access and completion progress saved to your player account.</p>
        </article>

        <article className="featureCard">
          <span className="featureIcon"><Apple aria-hidden="true" /></span>
          <h3>Plan every move</h3>
          <p>Guide the growing worm, collect the apples, avoid walls and obstacles, and reach the portal to satisfy each level's objectives.</p>
        </article>

        <article className="featureCard">
          <span className="featureIcon"><Lightbulb aria-hidden="true" /></span>
          <h3>Helpful game tools</h3>
          <p>Use the available hint and undo tools while solving a level. The game also provides restart controls when you want another attempt.</p>
        </article>

        <article className="featureCard">
          <span className="featureIcon"><Trophy aria-hidden="true" /></span>
          <h3>Scores and stars</h3>
          <p>Build your score, earn completion stars, and track your level progress as you improve your puzzle-solving strategy.</p>
        </article>

        <article className="featureCard">
          <span className="featureIcon"><Crown aria-hidden="true" /></span>
          <h3>Achievements and leaderboard</h3>
          <p>Visit the achievements screen to see recorded milestones and check the leaderboard to compare player scores.</p>
        </article>

        <article className="featureCard">
          <span className="featureIcon"><Coins aria-hidden="true" /></span>
          <h3>Player wallet and verified rewards</h3>
          <p>View your wallet and reward history. Rewarded-ad rewards are only eligible after the configured provider flow is completed and verified by the backend.</p>
        </article>
      </div>

      <div className="featuresFooter">
        <span>Ready to solve your first puzzle?</span>
        <button className="primary" type="button" onClick={start}>
          Start Adventure <Gamepad2 size={16} aria-hidden="true" />
        </button>
      </div>
    </section>
  </>
  )
}

function Auth({
  mode,
  busy,
  submit,
  forgot,
}: {
  mode: 'login' | 'register'
  busy: boolean
  submit: (
    m:
      | 'login'
      | 'register',
    f: HTMLFormElement,
  ) => void
  forgot: () => void
}) {
  return (
    <main className="auth">
      <div>
        <div className="eyebrow">
          VELOOP PLAYER ACCOUNT
        </div>

        <h1>
          {mode === 'login'
            ? 'Welcome back.'
            : 'Start your adventure.'}
        </h1>

        <p>
          Save your levels, stars,
          score, wallet and reward
          history across sessions.
        </p>
      </div>

      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault()

          submit(
            mode,
            e.currentTarget,
          )
        }}
      >
        <h2>
          {mode === 'login'
            ? 'Log in'
            : 'Create account'}
        </h2>

        {mode ===
          'register' && (
          <label>
            Email

            <input
              name="email"
              type="email"
              required
            />
          </label>
        )}

        <label>
          Username

          <input
            name="username"
            autoComplete="username"
            minLength={3}
            required
          />
        </label>

        <label>
          Password

          <input
            name="password"
            autoComplete={
              mode === 'login'
                ? 'current-password'
                : 'new-password'
            }
            type="password"
            minLength={8}
            required
          />
        </label>

        {mode === 'login' && (
          <button type="button" className="textButton" onClick={forgot}>Forgot password?</button>
        )}

        <button
          className="primary full"
          disabled={busy}
        >
          {busy
            ? 'Please wait…'
            : mode === 'login'
              ? 'Log in'
              : 'Create account'}
        </button>
      </form>
    </main>
  )
}

function PasswordReset({
  mode,
  busy,
  submit,
  back,
}: {
  mode: 'request' | 'confirm'
  busy: boolean
  submit: (mode: 'request' | 'confirm', form: HTMLFormElement) => void
  back: () => void
}) {
  return (
    <main className="auth">
      <div>
        <div className="eyebrow">ACCOUNT SECURITY</div>
        <h1>{mode === 'request' ? 'Reset your password.' : 'Choose a new password.'}</h1>
        <p>{mode === 'request' ? 'Enter the email address linked to your account. If it exists, we will send a single-use reset link.' : 'Choose a strong password. Reset links expire after one hour and can only be used once.'}</p>
      </div>
      <form className="card" onSubmit={(event) => { event.preventDefault(); submit(mode, event.currentTarget) }}>
        <h2>{mode === 'request' ? 'Request reset link' : 'Set new password'}</h2>
        {mode === 'request' ? (
          <label>Email<input name="email" type="email" autoComplete="email" required /></label>
        ) : (
          <>
            <label>New password<input name="password" type="password" autoComplete="new-password" minLength={8} required /></label>
            <label>Confirm password<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} required /></label>
          </>
        )}
        <button className="primary full" disabled={busy}>{busy ? 'Please wait…' : mode === 'request' ? 'Send reset link' : 'Reset password'}</button>
        <button type="button" className="textButton" onClick={back}>Back to login</button>
      </form>
    </main>
  )
}

function LevelSelect({
  levels,
  loading,
  error,
  retry,
  play,
}: {
  levels: Level[]
  loading: boolean
  error: string
  retry: () => void
  play: (n: number) => void
}) {
  return (
    <main className="section">
      <div className="sectionHead">
        <div>
          <div className="eyebrow">
            ADVENTURE MAP
          </div>

          <h1>
            Choose a level
          </h1>

          <p>
            Stars, best score and
            best moves are saved to
            your account.
          </p>
        </div>
      </div>

      {loading && (
        <div className="card">
          <h2>
            Loading 60 levels…
          </h2>

          <p>
            Syncing your progress
            with the server.
          </p>
        </div>
      )}

      {error && !loading && (
        <div className="error">
          <span>{error}</span>

          <button onClick={retry}>
            Retry
          </button>
        </div>
      )}

      {!loading &&
        !error &&
        !levels.length && (
          <div className="card">
            <h2>
              No levels available
            </h2>

            <p>
              The server returned no
              level progress for this
              account.
            </p>

            <button
              className="primary"
              onClick={retry}
            >
              Reload levels
            </button>
          </div>
        )}

      {!loading &&
        !error &&
        levels.length > 0 && (
          <div className="levelGrid">
            {levels.map((l) => (
              <button
                key={l.number}
                className={`level ${
                  l.unlocked
                    ? ''
                    : 'locked'
                }`}
                disabled={
                  !l.unlocked
                }
                onClick={() =>
                  play(l.number)
                }
              >
                <b>
                  {String(
                    l.number,
                  ).padStart(2, '0')}
                </b>

                <span>
                  {l.unlocked
                    ? l.completed
                      ? 'COMPLETED'
                      : 'PLAY'
                    : 'LOCKED'}
                </span>

                <em>
                  {'★'.repeat(
                    l.stars || 0,
                  )}

                  {'☆'.repeat(
                    Math.max(
                      0,
                      3 -
                        (l.stars ||
                          0),
                    ),
                  )}
                </em>

                <small>
                  {l.best_score ||
                    0}{' '}
                  pts ·{' '}
                  {l.best_moves ??
                    '—'}{' '}
                  moves
                </small>
              </button>
            ))}
          </div>
        )}
    </main>
  )
}

function GameView({
  game,
  objectives,
  levelNo,
  board,
  move,
  restart,
  undo,
  reward,
  loading: rewardLoading,
  hintDirection,
  musicOn,
  toggleMusic,
  soundOn,
  toggleSound,
  back,
  nextLevel,
  retryCompletion,
}: {
  game: GameState
  objectives: LevelObjective[]
  levelNo: number
  board: ReactNode
  move: (d: string) => void
  restart: () => void
  undo: () => void
  reward: (p: string) => void
  loading: boolean
  hintDirection: string
  musicOn: boolean
  toggleMusic: () => void
  soundOn: boolean
  toggleSound: () => void
  back: () => void
  nextLevel: () => void
  retryCompletion: () => void
}) {
  const touchStart = useRef<{ x: number; y: number } | null>(null)

  const handleBoardTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    const touch = event.changedTouches[0]
    if (touch) {
      touchStart.current = { x: touch.clientX, y: touch.clientY }
    }
  }

  const handleBoardTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    const start = touchStart.current
    const touch = event.changedTouches[0]
    touchStart.current = null
    if (!start || !touch) return

    const dx = touch.clientX - start.x
    const dy = touch.clientY - start.y
    const threshold = 24
    if (Math.max(Math.abs(dx), Math.abs(dy)) < threshold) return

    event.preventDefault()
    if (Math.abs(dx) > Math.abs(dy)) {
      move(dx > 0 ? 'right' : 'left')
    } else {
      move(dy > 0 ? 'down' : 'up')
    }
  }

  const noReviveObjective = objectives.some(
    (objective) =>
      objective.type === 'no_revive' &&
      objective.required,
  )

  return (
    <main className="game">
      <div className="gameTop">
        <button onClick={back}>
          ← Levels
        </button>

        <div>
          <b>
            LEVEL{' '}
            {String(
              levelNo,
            ).padStart(2, '0')}
          </b>

          <span>
            Apples{' '}
            {game.apples.length}
            {' · '}
            Moves {game.moves}
            {' · '}
            Score {game.score}
          </span>
        </div>

        <button
          onClick={restart}
        >
          <RotateCcw
            size={16}
          />{' '}
          Restart
        </button>
      </div>

      <div className="gameLayout">
        <div className="gameCard">
          <div className="objectiveBanner" role="status" aria-live="polite">
            {game.apples.length > 0
              ? same(game.worm[0], game.portal)
                ? `Portal locked — collect all ${game.apples.length} remaining apple${game.apples.length === 1 ? '' : 's'} first.`
                : `Collect all ${game.apples.length} remaining apple${game.apples.length === 1 ? '' : 's'}, then reach the portal.`
              : same(game.worm[0], game.portal)
                ? 'All objectives complete — saving your level…'
                : 'All apples collected — reach the portal to complete this level.'}
          </div>

          <div
            className="board"
            aria-label="Game board. Swipe up, down, left, or right to move the worm."
            onTouchStart={handleBoardTouchStart}
            onTouchEnd={handleBoardTouchEnd}
            style={{
              gridTemplateColumns:
                `repeat(${
                  7 +
                  Math.min(
                    3,
                    Math.floor(
                      levelNo /
                        12,
                    ),
                  )
                },1fr)`,
            }}
          >
            {board}
          </div>

          {!game.completed &&
            !game.failed &&
            game.apples.length === 0 &&
            same(game.worm[0], game.portal) &&
            objectivesSatisfied(game, objectives) && (
              <div className="portalReady" role="status">
                <span>All objectives complete. Confirm your level result.</span>
                <button className="primary" onClick={retryCompletion}>
                  Complete Level
                </button>
              </div>
            )}

          {game.failed && (
            <div className="modal">
              <Heart size={38} />

              <h2>
                Level failed
              </h2>

              <p>
                You hit danger.
                Continue from your
                last safe position or
                restart.
              </p>

              <div className="modalActions">
                {!noReviveObjective && (
                  <button
                    className="primary"
                    onClick={() => reward('REVIVE')}
                    disabled={rewardLoading}
                  >
                    Watch Rewarded Demo & Revive
                  </button>
                )}

                {noReviveObjective && (
                  <p className="errorNotice">
                    Revive is disabled for this level.
                  </p>
                )}

                <button
                  onClick={restart}
                >
                  Restart
                </button>
              </div>
            </div>
          )}

          {game.completed &&
            !game.failed &&
            game.apples.length ===
              0 &&
            same(
              game.worm[0],
              game.portal,
            ) && (
              <div className="modal">
                <Trophy size={38} />

                <h2>
                  Level complete!
                </h2>

                <p>
                  Excellent route.
                  Your result has
                  been saved.
                </p>

                <div className="modalActions">
                  <button onClick={() => reward('DOUBLE_SCORE')} disabled={rewardLoading}>
                    2× Score · Rewarded Demo
                  </button>

                  <button onClick={() => reward('DOUBLE_COINS')} disabled={rewardLoading}>
                    2× Coins · Rewarded Demo
                  </button>

                  <button
                    className="primary"
                    onClick={nextLevel}
                  >
                    {levelNo < 60
                      ? `Continue to Level ${String(levelNo + 1).padStart(2, '0')}`
                      : 'Back to Levels'}
                  </button>
                </div>
              </div>
            )}
        </div>

        <aside className="side">
          <div className="hud">
            <span>
              <Apple />
              Apples
              <b>
                {game.apples.length}
              </b>
            </span>

            <span>
              <Zap />
              Score
              <b>
                {game.score}
              </b>
            </span>

            <span>
              <Gamepad2 />
              Moves
              <b>
                {game.moves}
              </b>
            </span>
          </div>

          {objectives.length > 0 && (
            <div className="objectivesCard" aria-label="Level objectives">
              <h3>Objectives</h3>
              <ul>
                {objectives.map((objective) => {
                  const completed =
                    objective.type === 'collect_apples'
                      ? game.apples.length === 0
                      : objective.type === 'reach_portal'
                        ? game.apples.length === 0 &&
                          same(game.worm[0], game.portal)
                        : objective.type === 'move_limit'
                          ? game.moves <=
                            ((objective.target || 0) + game.extraMoves)
                          : objective.type === 'no_revive'
                            ? game.revives === 0
                            : false

                  return (
                    <li key={objective.id}>
                      <span className={completed ? 'objectiveDone' : ''}>
                        {completed ? '✓' : '○'} {objective.title}
                      </span>
                      {objective.type === 'move_limit' && (
                        <small>
                          {game.moves}/{(objective.target || 0) + game.extraMoves} moves
                        </small>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          <div className="controls">
            <button
              onClick={() =>
                move('up')
              }
            >
              <ArrowUp />
            </button>

            <div>
              <button
                onClick={() =>
                  move('left')
                }
              >
                <ArrowLeft />
              </button>

              <button
                onClick={() =>
                  move('down')
                }
              >
                <ArrowDown />
              </button>

              <button
                onClick={() =>
                  move('right')
                }
              >
                <ArrowRight />
              </button>
            </div>
          </div>

          <div className="tools">
            <button
              onClick={undo}
              disabled={game.failed && noReviveObjective}
              title={
                game.failed && noReviveObjective
                  ? 'Undo is disabled after failure on a No-Revive level.'
                  : 'Undo last move'
              }
            >
              <Undo2 /> Undo
            </button>

            <button
              onClick={() =>
                reward('HINT')
              }
            >
              <Lightbulb /> Hint
            </button>

            <button
              onClick={() => reward('EXTRA_MOVES')}
              disabled={rewardLoading}
              title="Provider-free demo reward in local/staging; real production ads require a configured provider."
            >
              <Zap /> +5 Moves · Rewarded Demo
            </button>

            <button
              onClick={() => reward('BOOSTER')}
              disabled={rewardLoading}
              title="Provider-free demo reward in local/staging; real production ads require a configured provider."
            >
              <Sparkles /> Booster · Rewarded Demo
            </button>

            <button
              onClick={toggleMusic}
              aria-pressed={musicOn}
            >
              {musicOn ? <><Volume2 size={15} /> Music On</> : <><VolumeX size={15} /> Music Off</>}
            </button>

            <button
              onClick={toggleSound}
              aria-pressed={soundOn}
              title="Toggle sound effects. Your preference is saved on this device."
            >
              {soundOn ? <><Volume2 size={15} /> Sound On</> : <><VolumeX size={15} /> Sound Off</>}
            </button>
          </div>

          {hintDirection && (
            <div className="toast" role="status" aria-live="polite">
              Hint: move {hintDirection.toUpperCase()}
            </div>
          )}

          <p className="help">
            Keyboard: arrows / WASD ·
            Mobile: direction pad ·
            Collect every apple before
            entering the portal.
          </p>
        </aside>
      </div>
    </main>
  )
}

type WalletTransaction = {
  amount: number
  balance_after: number
  kind: string
  reason: string
  reference?: string
  created_at: string
}

type WalletReward = {
  placement: string
  reward_type: string
  amount: number
  status: string
  event_id: string
  created_at: string
}

type WalletResponse = {
  coins: number
  transactions: WalletTransaction[]
  rewards: WalletReward[]
}

function Wallet({
  token,
  onLoad,
  data,
}: {
  token: string
  onLoad: (value: WalletResponse) => void
  data: WalletResponse | null
}) {
  const [status, setStatus] = useState<DataPageStatus>('loading')
  const [loadError, setLoadError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), 15000)

    setStatus('loading')
    setLoadError('')

    request<WalletResponse>('/economy/wallet/', { signal: controller.signal }, token)
      .then((response) => {
        if (!Number.isFinite(Number(response?.coins)) ||
            !Array.isArray(response?.transactions) ||
            !Array.isArray(response?.rewards)) {
          throw new Error('The wallet response was invalid. Please try again.')
        }
        if (!active) return
        onLoad(response)
        setStatus('success')
      })
      .catch((error: unknown) => {
        if (!active) return
        setLoadError(error instanceof Error
          ? error.message
          : 'Unable to load your wallet. Please try again.')
        setStatus('error')
      })
      .finally(() => window.clearTimeout(timeoutId))

    return () => {
      active = false
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [token, reloadKey, onLoad])

  const money = (value: unknown) => Number(value || 0).toLocaleString()
  const date = (value: string) => {
    const parsed = new Date(value)
    return Number.isNaN(parsed.getTime()) ? 'Date unavailable' : parsed.toLocaleString()
  }

  return (
    <main className="section">
      <div className="dataPageActions">
        <h1><Coins aria-hidden="true" /> Wallet</h1>
      </div>

      {status === 'loading' ? (
        <div className="dataList" role="status" aria-live="polite">Loading wallet…</div>
      ) : status === 'error' ? (
        <div className="dataState" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={() => setReloadKey((value) => value + 1)}>Try again</button>
        </div>
      ) : (
        <>
          <section className="dataList" aria-label="Wallet balance">
            <div className="dataRow">
              <b>Available coins</b>
              <strong>{money(data?.coins)}</strong>
            </div>
          </section>

          <section className="dataList" aria-labelledby="wallet-transactions-title">
            <h2 id="wallet-transactions-title">Wallet transactions</h2>
            {(data?.transactions?.length ?? 0) === 0 ? (
              <p className="dataState" role="status">No wallet transactions yet.</p>
            ) : data!.transactions.map((transaction, index) => (
              <div className="dataRow" key={`${transaction.reference || transaction.kind}-${transaction.created_at}-${index}`}>
                <div>
                  <b>{transaction.reason || transaction.kind}</b>
                  <span>{date(transaction.created_at)}</span>
                </div>
                <strong>{transaction.amount > 0 ? '+' : ''}{money(transaction.amount)} coins</strong>
              </div>
            ))}
          </section>

          <section className="dataList" aria-labelledby="wallet-rewards-title">
            <h2 id="wallet-rewards-title">Reward history</h2>
            {(data?.rewards?.length ?? 0) === 0 ? (
              <p className="dataState" role="status">No verified rewards yet.</p>
            ) : data!.rewards.map((reward) => (
              <div className="dataRow" key={reward.event_id}>
                <div>
                  <b>{reward.reward_type} · {reward.placement}</b>
                  <span>{date(reward.created_at)} · {reward.status}</span>
                </div>
                <strong>{money(reward.amount)} coins</strong>
              </div>
            ))}
          </section>
        </>
      )}
    </main>
  )
}

type DataPageStatus = 'loading' | 'success' | 'empty' | 'error'

function DataPage({
  title,
  icon,
  load,
  emptyMessage = 'No records are available yet.',
  emptyHint,
  onBack,
  backLabel = 'Back',
}: {
  title: string
  icon: ReactNode
  load: (signal: AbortSignal) => Promise<any[]>
  emptyMessage?: string
  emptyHint?: string
  onBack?: () => void
  backLabel?: string
}) {
  const [status, setStatus] = useState<DataPageStatus>('loading')
  const [data, setData] = useState<any[]>([])
  const [loadError, setLoadError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    let timeoutId = 0

    setStatus('loading')
    setLoadError('')

    const timeout = new Promise<never>((_, reject) => {
      timeoutId = window.setTimeout(() => {
        controller.abort()
        reject(new Error(`Loading ${title.toLowerCase()} timed out. Check your connection and try again.`))
      }, 15000)
    })

    // The timeout bounds the UI state even if a server/proxy never responds.
    Promise.race([load(controller.signal), timeout])
      .then((records) => {
        if (!Array.isArray(records)) {
          throw new Error(`The ${title.toLowerCase()} response was invalid. Please try again.`)
        }
        if (!active) return
        setData(records)
        setStatus(records.length > 0 ? 'success' : 'empty')
      })
      .catch((error: unknown) => {
        if (!active) return
        setData([])
        setLoadError(
          error instanceof Error
            ? error.message
            : `Unable to load ${title.toLowerCase()}. Please try again.`,
        )
        setStatus('error')
      })
      .finally(() => {
        window.clearTimeout(timeoutId)
      })

    return () => {
      active = false
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [reloadKey, title])

  return (
    <main className="section">
      {onBack && (
        <div className="dataPageActions">
          <button type="button" onClick={onBack}>
            <ArrowLeft size={16} />
            {backLabel}
          </button>
        </div>
      )}

      <div className="sectionHead">
        <div className="eyebrow">PLAYER PROGRESS</div>
        <h1>{icon}{title}</h1>
      </div>

      <div className="dataList" aria-live="polite" aria-busy={status === 'loading'}>
        {status === 'loading' ? (
          <p className="dataState" role="status">Loading {title.toLowerCase()}…</p>
        ) : status === 'error' ? (
          <div className="dataState" role="alert">
            <p>{loadError}</p>
            <button type="button" onClick={() => setReloadKey((value) => value + 1)}>
              Try again
            </button>
          </div>
        ) : status === 'empty' ? (
          <div className="dataState" role="status">
            <p>{emptyMessage}</p>
            {emptyHint && <p className="dataStateHint">{emptyHint}</p>}
            <button type="button" onClick={() => setReloadKey((value) => value + 1)}>
              Refresh
            </button>
          </div>
        ) : (
          data.map((x, i) => (
            <div className="dataRow" key={x.code || x.username || x.id || i}>
              <b>{x.icon || (x.rank ? `#${x.rank}` : `#${i + 1}`)} {x.title || x.username}</b>
              <span>{x.description || `${x.score ?? (x.unlocked ? 'Unlocked' : 'Locked')}`}</span>
              <strong>{x.score ?? (x.unlocked ? '✓' : '—')}</strong>
            </div>
          ))
        )}
      </div>
    </main>
  )
}
