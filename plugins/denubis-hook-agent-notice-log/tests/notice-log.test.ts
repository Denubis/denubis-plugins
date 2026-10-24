import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

// The person's environment as the tests give it, and the default log path it
// implies, written out so the expected path does not come from the code under
// test.
const HOME = '/home/tester'
const LOG = '/home/tester/.claude/agent-notice-log.jsonl'

// 2026-10-24T03:00:00.000Z, written out so the expected timestamp does not
// come from the code under test.
const NOW = 1792810800000

const NOTICE =
  '<task-notification>\n<task-id>a1</task-id>\n<status>completed</status>\n</task-notification>'

// Stands for the host beneath the plugin: `tee -a` is replaced by a fake that
// appends its stdin to the named path in `files`. `failing` paths make it exit 1.
const fakeTee = (
  on: On,
  files: Map<string, string>,
  failing: ReadonlySet<string> = new Set(),
) => {
  const calls: { argv: readonly string[]; stdin: string | undefined }[] = []
  on('process.run', (_, e) => {
    calls.push({ argv: e.argv, stdin: e.init?.stdin })
    const [cmd, flag, path] = e.argv
    if (cmd !== 'tee' || flag !== '-a' || path === undefined) {
      return { deny: `unexpected command ${e.argv.join(' ')}` }
    }
    if (failing.has(path)) {
      return { value: { exitCode: 1, stdout: '', stderr: 'tee: disk full', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    files.set(path, `${files.get(path) ?? ''}${e.init?.stdin ?? ''}`)
    return { value: { exitCode: 0, stdout: e.init?.stdin ?? '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return calls
}

// Stands for the display: records the status line and the debug log.
const display = (on: On) => {
  const statuses: (string | undefined)[] = []
  const logged: string[] = []
  on('ui.status', (_, e) => {
    statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.log', (_, e) => {
    logged.push(e.text)
    return { value: undefined }
  })
  return { statuses, logged }
}

const linesAt = (files: Map<string, string>, path: string): unknown[] =>
  (files.get(path) ?? '')
    .split('\n')
    .filter(line => line !== '')
    .map(line => JSON.parse(line) as unknown)

const linesOf = (files: Map<string, string>): unknown[] => linesAt(files, LOG)

test('a task notification is logged with its origin and passes on unchanged', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map<string, string>()
  fakeTee(on, files)
  const reached: string[] = []
  on('prompt.submit', (_, e) => {
    reached.push(e.text)
    return { text: e.text, context: e.context, origin: e.origin }
  })

  const result = await $.prompt.submit({
    text: NOTICE,
    wait: false,
    origin: { kind: 'task-notification' },
    isMeta: true,
  })

  expect(result.drop).toBeUndefined()
  expect(result.text).toBe(NOTICE)
  expect(reached).toEqual([NOTICE])
  expect(linesOf(files)).toEqual([
    {
      ts: '2026-10-24T03:00:00.000Z',
      door: 'prompt.submit',
      origin: { kind: 'task-notification' },
      isMeta: true,
      keys: expect.any(Array),
      textLength: NOTICE.length,
      head: NOTICE,
    },
  ])
})

test('each submission adds one line, keeping what the file held', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map([[LOG, '{"earlier":true}\n']])
  fakeTee(on, files)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))
  const long = 'x'.repeat(450)

  await $.prompt.submit({ text: 'hello', wait: false, origin: { kind: 'composer' } })
  await $.prompt.submit({ text: long, wait: false, origin: { kind: 'composer' } })

  expect(linesOf(files)).toEqual([
    { earlier: true },
    expect.objectContaining({ door: 'prompt.submit', isMeta: false, head: 'hello' }),
    expect.objectContaining({ textLength: 450, head: 'x'.repeat(300) }),
  ])
})

test('a delivery at session.receive is logged with its door and passes on', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map<string, string>()
  fakeTee(on, files)
  on('session.receive', (_, e) => ({ text: e.text }))

  const result = await $.session.receive({
    origin: { kind: 'peer', teammate: 'researcher', isVerified: true },
    text: 'done with the search',
  })

  expect(result.consumed).toBeUndefined()
  expect(result.text).toBe('done with the search')
  expect(linesOf(files)).toEqual([
    {
      ts: '2026-10-24T03:00:00.000Z',
      door: 'session.receive',
      origin: { kind: 'peer', teammate: 'researcher', isVerified: true },
      keys: expect.any(Array),
      textLength: 20,
      head: 'done with the search',
    },
  ])
})

test('a tee that fails is said so, the file is left as it was, and the prompt still passes', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map([[LOG, 'kept\n']])
  fakeTee(on, files, new Set([LOG]))
  const { statuses, logged } = display(on)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))

  const result = await $.prompt.submit({ text: 'hi', wait: false, origin: { kind: 'composer' } })

  expect(result.text).toBe('hi')
  expect(files.get(LOG)).toBe('kept\n')
  expect(statuses).toEqual([expect.stringContaining('agent-notice-log')])
  expect(logged).toEqual([expect.stringContaining(LOG)])
})

// Where the log goes.

test('CLAUDE_CONFIG_DIR moves the default log into that directory', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME, CLAUDE_CONFIG_DIR: '/srv/claude-work' })
  const files = new Map<string, string>()
  fakeTee(on, files)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))

  await $.prompt.submit({ text: 'hello', wait: false, origin: { kind: 'composer' } })

  expect([...files.keys()]).toEqual(['/srv/claude-work/agent-notice-log.jsonl'])
  expect(linesAt(files, '/srv/claude-work/agent-notice-log.jsonl')).toEqual([
    expect.objectContaining({ door: 'prompt.submit', head: 'hello' }),
  ])
})

test('an absolute log file set in the options is used as given', { options: { log_path: '/var/log/agents/notices.jsonl' } }, async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME, CLAUDE_CONFIG_DIR: '/srv/claude-work' })
  const files = new Map<string, string>()
  fakeTee(on, files)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))

  await $.prompt.submit({ text: 'hello', wait: false, origin: { kind: 'composer' } })

  expect([...files.keys()]).toEqual(['/var/log/agents/notices.jsonl'])
  expect(linesAt(files, '/var/log/agents/notices.jsonl')).toEqual([
    expect.objectContaining({ door: 'prompt.submit', head: 'hello' }),
  ])
})

test('a log file set with ~/ is placed under HOME', { options: { log_path: '~/notes/agents.jsonl' } }, async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map<string, string>()
  fakeTee(on, files)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))

  await $.prompt.submit({ text: 'hello', wait: false, origin: { kind: 'composer' } })

  expect([...files.keys()]).toEqual(['/home/tester/notes/agents.jsonl'])
})

test('a relative log file writes nothing, says why, and the prompt still passes', { options: { log_path: 'logs/agents.jsonl' } }, async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, { HOME })
  const files = new Map<string, string>()
  const calls = fakeTee(on, files)
  const { statuses, logged } = display(on)
  on('prompt.submit', (_, e) => ({ text: e.text, origin: e.origin }))

  const result = await $.prompt.submit({ text: 'hi', wait: false, origin: { kind: 'composer' } })

  expect(result.text).toBe('hi')
  expect(calls).toEqual([])
  expect(statuses).toEqual([expect.stringContaining('agent-notice-log')])
  expect(logged).toEqual([expect.stringContaining('logs/agents.jsonl')])
})

test('with neither CLAUDE_CONFIG_DIR nor HOME set, nothing is written and the reason is shown', async ($, on) => {
  mock.clock(on, { now: NOW })
  mock.env(on, {})
  const files = new Map<string, string>()
  const calls = fakeTee(on, files)
  const { statuses, logged } = display(on)
  on('session.receive', (_, e) => ({ text: e.text }))

  const result = await $.session.receive({
    origin: { kind: 'peer', teammate: 'researcher', isVerified: true },
    text: 'done',
  })

  expect(result.text).toBe('done')
  expect(calls).toEqual([])
  expect(statuses).toEqual([expect.stringContaining('agent-notice-log')])
  expect(logged).toEqual([expect.stringContaining('HOME')])
})
