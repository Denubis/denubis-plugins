import type { EngineInterface, Register } from 'claude-code'

// Observation only: every hook here passes its event on unchanged, so what
// quiet-agents matches on can be checked against what really arrives.

const LOG_NAME = 'agent-notice-log.jsonl'
const HEAD_CHARS = 300

type Door = 'prompt.submit' | 'session.receive'

type Observation = {
  door: Door
  origin: unknown
  // `prompt.submit` only: `session.receive` carries no such field.
  isMeta?: boolean
  turnId?: string
  // `session.receive` only: `prompt.submit` names no loop in its input.
  agentId?: string
  // Every field the input carried, so an undocumented loop marker shows up.
  keys: readonly string[]
  textLength: number
  head: string
}

const describeError = (error: unknown): string =>
  error instanceof Error ? `${error.name}: ${error.message}` : String(error)

// The mods API gives a hooks module no data directory of its own ($.plugin has
// only `name` and `root`, and `root` is replaced on update), so the default is
// the Claude config directory: `CLAUDE_CONFIG_DIR`, documented as overriding
// it, else `~/.claude`. Outside every plugin folder, so a write never reloads
// a mod. A path the person sets is taken as given when absolute, or under HOME
// for `~/`; a relative one is refused, as `tee` would resolve it against
// whatever directory the session runs in.
const resolveLog = async ($: EngineInterface, setting: string): Promise<string> => {
  if (setting.startsWith('/')) {
    return setting
  }
  if (setting.startsWith('~/')) {
    const home = await $.env.get('HOME')
    if (home === undefined || home === '') {
      throw new Error(`log_path ${setting} starts with ~/ but HOME is not set`)
    }
    return `${home}${setting.slice(1)}`
  }
  if (setting !== '') {
    throw new Error(`log_path ${setting} is neither absolute nor under ~/`)
  }

  const configDir = await $.env.get('CLAUDE_CONFIG_DIR')
  if (configDir !== undefined && configDir !== '') {
    return `${configDir}/${LOG_NAME}`
  }
  const home = await $.env.get('HOME')
  if (home === undefined || home === '') {
    throw new Error('neither CLAUDE_CONFIG_DIR nor HOME is set, so there is no default log path')
  }
  return `${home}/.claude/${LOG_NAME}`
}

// A true append: `tee -a` on the host, fed the line on stdin, no shell. The
// engine's `$.fs` has no append and refuses files over 4 MiB, so it is not
// used here; the log can grow without bound and is never read back.
const appendLine = async ($: EngineInterface, log: string, line: string): Promise<void> => {
  const { exitCode, stderr } = await $.process.run(['tee', '-a', log], { stdin: `${line}\n` })
  if (exitCode !== 0) {
    throw new Error(`tee -a ${log} exited ${exitCode}: ${stderr.trim()}`)
  }
}

// Said where it will be seen: the debug log has the reason, the status line
// says the log is not being written.
const reportUnwritten = ($: EngineInterface, reason: string): void => {
  $.ui.log(`agent-notice-log: ${reason}`, { to: 'debug' })
  $.ui.status('agent-notice-log: the log is not being written (see the debug log)')
}

const reportFailure = async ($: EngineInterface, log: string, door: Door, error: unknown): Promise<void> => {
  const reason = describeError(error)
  try {
    const ts = new Date(await $.clock.now()).toISOString()
    await appendLine($, log, JSON.stringify({ ts, door, error: reason }))
  } catch (secondError) {
    // The file itself refuses the line.
    reportUnwritten($, `could not write ${log}: ${reason}; then ${describeError(secondError)}`)
  }
}

const writeObservation = async ($: EngineInterface, setting: string, observation: Observation): Promise<void> => {
  let log: string
  try {
    log = await resolveLog($, setting)
  } catch (error) {
    reportUnwritten($, `no log path: ${describeError(error)}`)
    return
  }

  try {
    const ts = new Date(await $.clock.now()).toISOString()
    await appendLine($, log, JSON.stringify({ ts, ...observation }))
  } catch (error) {
    await reportFailure($, log, observation.door, error)
  }
}

// One write at a time, so lines keep the order the hooks saw them in. Each
// step runs whatever the one before it settled to.
let queue: Promise<void> = Promise.resolve()

const record = ($: EngineInterface, setting: string, observation: Observation): Promise<void> => {
  const write = () => writeObservation($, setting, observation)
  const run = queue.then(write, write)
  queue = run
  return run
}

export const register: Register = (on, options) => {
  // The `log_path` option, trimmed; empty when unset.
  const configured = options['log_path']
  const setting = typeof configured === 'string' ? configured.trim() : ''

  on('prompt.submit', async ($, e, next) => {
    await record($, setting, {
      door: 'prompt.submit',
      origin: e.origin,
      isMeta: e.isMeta === true,
      turnId: e.turnId,
      keys: Object.keys(e),
      textLength: e.text.length,
      head: e.text.slice(0, HEAD_CHARS),
    })

    return next(e)
  })

  on('session.receive', async ($, e, next) => {
    await record($, setting, {
      door: 'session.receive',
      origin: e.origin,
      agentId: e.agentId,
      keys: Object.keys(e),
      textLength: e.text.length,
      head: e.text.slice(0, HEAD_CHARS),
    })

    return next(e)
  })
}
