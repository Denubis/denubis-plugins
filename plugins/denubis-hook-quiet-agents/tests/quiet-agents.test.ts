import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { AgentInfo, On, PromptOrigin, PromptSubmitInput, SessionSendInput } from 'claude-code'

// The texts as the design gives them, written out here so the expectations
// do not come from the module under test.
const CONTEXT =
  "This turn was started by an agent notification, not by the human. If the notification adds nothing the human has not already been told, reply in one line or not at all. Do not restate decisions already pending with the human, do not write 'waiting on you', and do not summarise the agent's work again. If the agent reports its task complete and you have no further work for it, stop it with TaskStop in this turn."

const SECTION_TEXT =
  'Agent hygiene: when a subagent or teammate reports its task complete and you have no further work for it, stop it with TaskStop in the same turn you acknowledge it. Do not leave a finished agent idle across a turn boundary. A turn started by an agent notification that carries nothing new is answered in one line or none.'

const NOTICE =
  '<task-notification>\n<task-id>a1</task-id>\n<status>completed</status>\n</task-notification>'

// FNV-1a (32 bits, over UTF-16 code units) of the first line,
// "<task-notification>", computed outside this module with Python.
const NOTICE_KEY = 'task-notification:54808168'

type Entered = { text: string; context: readonly string[] | undefined }

// Stands for the engine beneath the plugin: records what entered.
const engineTakesPrompts = (on: On): Entered[] => {
  const entered: Entered[] = []
  on('prompt.submit', (_, e) => {
    entered.push({ text: e.text, context: e.context })
    return { text: e.text, context: e.context, origin: e.origin }
  })
  return entered
}

const notice = (text: string, origin: PromptSubmitInput['origin']): PromptSubmitInput => ({
  text,
  wait: false,
  origin,
  isMeta: true,
})

const typed = (text: string): PromptSubmitInput => ({ text, wait: false, origin: { kind: 'composer' } })

test('two identical notices: the first passes with the context, the repeat is muted', async ($, on) => {
  const entered = engineTakesPrompts(on)

  const first = await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))
  // The same body with its whitespace changed is the same notice.
  const repeat = await $.prompt.submit(
    notice(`  ${NOTICE.replaceAll('\n', '\n   ')}\n`, { kind: 'task-notification' }),
  )

  expect(first.drop).toBeUndefined()
  expect(entered).toEqual([{ text: NOTICE, context: [CONTEXT] }])
  expect(repeat.drop).toBe(`quiet-agents: repeat notice from ${NOTICE_KEY}, muted`)
})

test('a changed notice under the same key passes again with the context', async ($, on) => {
  const entered = engineTakesPrompts(on)
  const changed = NOTICE.replace('completed', 'failed')

  await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))
  const second = await $.prompt.submit(notice(changed, { kind: 'task-notification' }))

  expect(second.drop).toBeUndefined()
  expect(entered).toEqual([
    { text: NOTICE, context: [CONTEXT] },
    { text: changed, context: [CONTEXT] },
  ])
})

test('the context is added after any context a hook above attached', async ($, on) => {
  const entered = engineTakesPrompts(on)

  await $.prompt.submit({ ...notice(NOTICE, { kind: 'peer-send-message' }), context: ['earlier'] })

  expect(entered).toEqual([{ text: NOTICE, context: ['earlier', CONTEXT] }])
})

test('a prompt the person typed is untouched, however often it repeats', async ($, on) => {
  const entered = engineTakesPrompts(on)

  const first = await $.prompt.submit(typed('carry on'))
  const again = await $.prompt.submit(typed('carry on'))

  expect(first.drop).toBeUndefined()
  expect(again.drop).toBeUndefined()
  expect(entered).toEqual([
    { text: 'carry on', context: undefined },
    { text: 'carry on', context: undefined },
  ])
})

test('unclassified is framed only when isMeta', async ($, on) => {
  const entered = engineTakesPrompts(on)

  await $.prompt.submit({ text: 'from a socket', wait: false, origin: { kind: 'unclassified' } })
  await $.prompt.submit(notice('idle', { kind: 'unclassified' }))

  expect(entered).toEqual([
    { text: 'from a socket', context: undefined },
    { text: 'idle', context: [CONTEXT] },
  ])
})

test('a notice the engine dropped is not remembered, so its repeat passes', async ($, on) => {
  const entered: string[] = []
  let isEngineDropping = true
  on('prompt.submit', (_, e) => {
    if (isEngineDropping) return { drop: 'a Stop stands' }
    entered.push(e.text)
    return { text: e.text, context: e.context, origin: e.origin }
  })

  const first = await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))
  isEngineDropping = false
  const repeat = await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))

  expect(first.drop).toBe('a Stop stands')
  expect(repeat.drop).toBeUndefined()
  expect(entered).toEqual([NOTICE])
})

const COMPOSE_INPUT = {
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: ['terminal'],
  tools: [],
  outputStyle: null,
  traits: [],
} as const

test('a teammate’s render of the lead’s prompt gets no tidy section', async ($, on) => {
  on('prompt.compose', () => ({
    sections: [{ id: 'intro', text: 'You are Claude Code.', scope: 'shared' }],
  }))

  const { sections } = await $.prompt.compose({ ...COMPOSE_INPUT, traits: ['teammate'] })

  expect(sections).toEqual([{ id: 'intro', text: 'You are Claude Code.', scope: 'shared' }])
})

test('the composed system prompt ends with the tidy section', async ($, on) => {
  on('prompt.compose', () => ({
    sections: [{ id: 'intro', text: 'You are Claude Code.', scope: 'shared' }],
  }))

  const { sections } = await $.prompt.compose(COMPOSE_INPUT)

  expect(sections).toEqual([
    { id: 'intro', text: 'You are Claude Code.', scope: 'shared' },
    { id: 'quiet-agents:tidy', text: SECTION_TEXT, scope: 'session' },
  ])
})

// session.receive and the sends: a teammate's report, its idle notice, and
// the main conversation's next message to it.

const PREFIX =
  '[quiet-agents] An agent went idle. If this adds nothing the human has not been told, reply in one line or none; do not restate pending decisions. If its task is complete and you have no further work for it, stop it with TaskStop in this turn.\n'

const consumedReason = (teammate: string): string =>
  `quiet-agents: idle notice from ${teammate}; its report was already received`

const idleContext = (names: string): string =>
  `quiet-agents: these agents went idle since your last turn, their reports already received: ${names}.`

const REPORT = 'Both mods are built.\n\nTests pass for each.'

const fromTeammate = (teammate: string, text: string) =>
  ({ origin: { kind: 'peer', teammate, isVerified: true }, text }) as const

const idleNotice = (from: string, result: unknown): string =>
  JSON.stringify({
    type: 'idle_notification',
    from,
    timestamp: '2026-10-24T03:05:20.937Z',
    idleReason: 'available',
    result,
  })

// The idle notice's `result` is the teammate's final turn text, not its
// report (agent-notice-log.jsonl lines 1-2), so it differs from REPORT here.
const IDLE = idleNotice('researcher', 'I built both mods, and each passes.')

// The main conversation's model sending through its SendMessage tool: no
// `agentId`, the main loop's.
const mainSends = (to: string, text: string): SessionSendInput => ({ to, text, origin: { kind: 'model' } })

const agent = (id: string, name: string, status: AgentInfo['status']): AgentInfo => ({
  id,
  name,
  description: `${name}'s task`,
  type: 'general-purpose',
  status,
})

// Stands for the engine beneath the plugin: records what was queued and the
// status line, delivers every send, and lists the agents given.
const engine = (on: On, agents: AgentInfo[] = []) => {
  const queued: string[] = []
  const statuses: (string | undefined)[] = []
  on('session.receive', (_, e) => {
    queued.push(e.text)
    return { text: e.text }
  })
  on('session.send', () => ({ isDelivered: true }))
  on('agent.list', () => ({ value: agents }))
  on('ui.status', (_, e) => {
    statuses.push(e.text)
    return { value: undefined }
  })
  return { queued, statuses }
}

// Records each of quiet-agents' writes to `$.state`, then lets it land.
const stateWrites = (on: On): string[] => {
  const writes: string[] = []
  on('state.set', { plugin: 'denubis-hook-quiet-agents' }, (_, e, next) => {
    writes.push(e.key)
    return next(e)
  })
  return writes
}

test('a report, then the idle notice: the notice is consumed and the teammate shown idle', async ($, on) => {
  const { queued, statuses } = engine(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  const result = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(result.consumed).toBe(consumedReason('researcher'))
  expect(queued).toEqual([REPORT])
  expect(statuses).toEqual(['agents idle: researcher'])
})

test('a second idle notice with no instruction between is consumed too', async ($, on) => {
  const { queued } = engine(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  const again = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(again.consumed).toBe(consumedReason('researcher'))
  expect(queued).toEqual([REPORT])
})

test('the status line names every idle teammate, sorted', async ($, on) => {
  const { statuses } = engine(on)

  await $.session.receive(fromTeammate('scout', REPORT))
  await $.session.receive(fromTeammate('scout', idleNotice('scout', 'done')))
  await $.session.receive(fromTeammate('helper', REPORT))
  await $.session.receive(fromTeammate('helper', idleNotice('helper', 'done')))

  expect(statuses).toEqual(['agents idle: scout', 'agents idle: helper, scout'])
})

test('an idle notice with no report before it passes with the prefix', async ($, on) => {
  const { queued, statuses } = engine(on)

  const result = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(result.consumed).toBeUndefined()
  expect(queued).toEqual([PREFIX + IDLE])
  expect(statuses).toEqual([])
})

test('a report, then a message to the teammate, then its idle notice: prefixed', async ($, on) => {
  const { queued } = engine(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  const sent = await $.session.send(mainSends('researcher', 'Now fix the tests.'))
  const result = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(sent.isDelivered).toBe(true)
  expect(result.consumed).toBeUndefined()
  expect(queued).toEqual([REPORT, PREFIX + IDLE])
})

test('a message to an idle teammate takes it off the status line', async ($, on) => {
  const { statuses } = engine(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.session.send(mainSends('researcher', 'Now fix the tests.'))

  expect(statuses).toEqual(['agents idle: researcher', undefined])
})

test('a message to another teammate leaves this one’s report standing', async ($, on) => {
  engine(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.send(mainSends('helper', 'Start on the docs.'))
  const result = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(result.consumed).toBe(consumedReason('researcher'))
})

test('a message addressed by the teammate’s agent id clears its report', async ($, on) => {
  const { queued } = engine(on, [agent('a-researcher-1f', 'researcher', 'idle')])

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.send(mainSends('a-researcher-1f', 'Now fix the tests.'))
  await $.session.receive(fromTeammate('researcher', IDLE))

  expect(queued).toEqual([REPORT, PREFIX + IDLE])
})

test('a SendMessage call with a structured message clears the report', async ($, on) => {
  const { queued } = engine(on)
  on('tool.call', () => ({ result: { success: true } }))

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.tool.call({
    tool: 'SendMessage',
    to: 'researcher',
    message: { type: 'plan_approval_response', request_id: 'r1', approve: true },
  })
  await $.session.receive(fromTeammate('researcher', IDLE))

  expect(queued).toEqual([REPORT, PREFIX + IDLE])
})

test('a SendMessage call from another agent’s loop leaves the report standing', async ($, on) => {
  engine(on)
  on('tool.call', () => ({ result: { success: true } }))

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.tool.call({ tool: 'SendMessage', to: 'researcher', message: 'ping', agentId: 'a-helper' })
  const result = await $.session.receive(fromTeammate('researcher', IDLE))

  expect(result.consumed).toBe(consumedReason('researcher'))
})

// An agent's own send to the main conversation: its report, marked at the
// send. A subagent's report reaches the main conversation only when it is
// dequeued, after its idle notice was judged (agent-notice-log.jsonl,
// 2026-10-24: the notice at 22:59:24.29Z, the report at 22:59:24.99Z).

const agentSends = (agentId: string, to: string, text: string): SessionSendInput => ({
  to,
  text,
  origin: { kind: 'model' },
  agentId,
})

const PROBE_ID = 'a-live-probe-7c'
const PROBE_REPORT = 'live-probe report: 2+2 printed 4; task complete, nothing further.'
const PROBE_IDLE = idleNotice('live-probe', 'The probe ran.')

// Records each line the plugin logs, with where it goes.
const logLines = (on: On): { text: string; to: string }[] => {
  const lines: { text: string; to: string }[] = []
  on('ui.log', (_, e) => {
    lines.push({ text: e.text, to: e.to })
    return { value: undefined }
  })
  return lines
}

test('a subagent’s report sent to main, then its idle notice: the notice is consumed', async ($, on) => {
  const { queued, statuses } = engine(on, [agent(PROBE_ID, 'live-probe', 'running')])

  const sent = await $.session.send(agentSends(PROBE_ID, 'main', PROBE_REPORT))
  const result = await $.session.receive(fromTeammate('live-probe', PROBE_IDLE))

  expect(sent.isDelivered).toBe(true)
  expect(result.consumed).toBe(consumedReason('live-probe'))
  expect(queued).toEqual([])
  expect(statuses).toEqual(['agents idle: live-probe'])
})

test('a teammate’s report sent to team-lead is marked under its name in the team', async ($, on) => {
  const scout: AgentInfo = {
    id: 'a-scout-2',
    teammateId: 'scout@session-1',
    description: 'scout’s task',
    type: 'teammate',
    status: 'running',
  }
  engine(on, [scout])

  await $.session.send(agentSends('a-scout-2', 'team-lead', REPORT))
  const result = await $.session.receive(fromTeammate('scout', idleNotice('scout', 'done')))

  expect(result.consumed).toBe(consumedReason('scout'))
})

test('a send from one agent to another does not mark the sender', async ($, on) => {
  const { queued } = engine(on, [
    agent(PROBE_ID, 'live-probe', 'running'),
    agent('a-helper-3', 'helper', 'running'),
  ])

  await $.session.send(agentSends(PROBE_ID, 'helper', 'Over to you.'))
  const result = await $.session.receive(fromTeammate('live-probe', PROBE_IDLE))

  expect(result.consumed).toBeUndefined()
  expect(queued).toEqual([PREFIX + PROBE_IDLE])
})

test('a send to main from an agent the list cannot name marks nothing and says so in the debug log', async ($, on) => {
  const { queued } = engine(on, [agent('a-helper-3', 'helper', 'running')])
  const lines = logLines(on)

  await $.session.send(agentSends('a-gone-9', 'main', PROBE_REPORT))
  const result = await $.session.receive(fromTeammate('live-probe', PROBE_IDLE))

  expect(result.consumed).toBeUndefined()
  expect(queued).toEqual([PREFIX + PROBE_IDLE])
  expect(lines.map(line => line.to)).toEqual(['debug'])
  expect(lines[0]?.text).toContain('a-gone-9')
})

test('a report the engine did not deliver marks nothing', async ($, on) => {
  // The engine's stand-ins written out: engine() delivers every send.
  const queued: string[] = []
  on('session.receive', (_, e) => {
    queued.push(e.text)
    return { text: e.text }
  })
  on('session.send', () => ({ isDelivered: false, reason: 'nobody by that name' }))
  on('agent.list', () => ({ value: [agent(PROBE_ID, 'live-probe', 'running')] }))
  on('ui.status', () => ({ value: undefined }))

  const sent = await $.session.send(agentSends(PROBE_ID, 'main', PROBE_REPORT))
  const result = await $.session.receive(fromTeammate('live-probe', PROBE_IDLE))

  expect(sent.isDelivered).toBe(false)
  expect(result.consumed).toBeUndefined()
  expect(queued).toEqual([PREFIX + PROBE_IDLE])
})

test('consumed idle notices are named once, in the next prompt’s context', async ($, on) => {
  engine(on)
  const entered = engineTakesPrompts(on)

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.session.receive(fromTeammate('helper', REPORT))
  await $.session.receive(fromTeammate('helper', idleNotice('helper', 'done')))
  await $.prompt.submit(typed('carry on'))
  await $.prompt.submit(typed('and then?'))

  expect(entered).toEqual([
    { text: 'carry on', context: [idleContext('researcher, helper')] },
    { text: 'and then?', context: undefined },
  ])
})

test('a prompt that did not enter leaves the names for the next one', async ($, on) => {
  engine(on)
  const entered: Entered[] = []
  let isEngineDropping = true
  on('prompt.submit', (_, e) => {
    if (isEngineDropping) return { drop: 'a Stop stands' }
    entered.push({ text: e.text, context: e.context })
    return { text: e.text, context: e.context, origin: e.origin }
  })

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.prompt.submit(typed('carry on'))
  isEngineDropping = false
  await $.prompt.submit(typed('carry on'))

  expect(entered).toEqual([{ text: 'carry on', context: [idleContext('researcher')] }])
})

test('a muted repeat notice leaves the names for the next prompt', async ($, on) => {
  engine(on)
  const entered = engineTakesPrompts(on)

  await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))
  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  const muted = await $.prompt.submit(notice(NOTICE, { kind: 'task-notification' }))
  await $.prompt.submit(typed('carry on'))

  expect(muted.drop).toBe(`quiet-agents: repeat notice from ${NOTICE_KEY}, muted`)
  expect(entered).toEqual([
    { text: NOTICE, context: [CONTEXT] },
    { text: 'carry on', context: [idleContext('researcher')] },
  ])
})

test('an idle notice is matched by the stamped teammate, not the `from` it claims', async ($, on) => {
  const { queued } = engine(on)
  const claimsResearcher = idleNotice('researcher', 'done')

  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('helper', claimsResearcher))

  expect(queued).toEqual([REPORT, PREFIX + claimsResearcher])
})

test('a delivery to a teammate’s own loop is untouched and writes no state', async ($, on) => {
  const { queued, statuses } = engine(on)
  const writes = stateWrites(on)

  await $.session.receive({ ...fromTeammate('researcher', REPORT), agentId: 'a-helper' })
  await $.session.receive({ ...fromTeammate('researcher', IDLE), agentId: 'a-helper' })
  expect(writes).toEqual([])

  // The next, to the main conversation, finds no report: it gets the prefix.
  await $.session.receive(fromTeammate('researcher', IDLE))
  expect(queued).toEqual([REPORT, IDLE, PREFIX + IDLE])
  expect(statuses).toEqual([])
})

test('an unverified teammate is no teammate: untouched, and no state written', async ($, on) => {
  const { queued, statuses } = engine(on)
  const writes = stateWrites(on)
  const unverified = (text: string) =>
    ({ origin: { kind: 'peer', teammate: 'researcher', isVerified: false }, text }) as const

  await $.session.receive(unverified(REPORT))
  await $.session.receive(unverified(IDLE))
  expect(writes).toEqual([])

  await $.session.receive(fromTeammate('researcher', IDLE))
  expect(queued).toEqual([REPORT, IDLE, PREFIX + IDLE])
  expect(statuses).toEqual([])
})

test('a peer message that is not an idle notice passes unchanged', async ($, on) => {
  const { queued } = engine(on)
  const other = JSON.stringify({ type: 'shutdown_request', from: 'researcher' })

  await $.session.receive(fromTeammate('researcher', other))
  await $.session.receive(fromTeammate('researcher', '{"type":"idle_notification"'))
  await $.session.receive(fromTeammate('researcher', 'plain words, not JSON'))

  expect(queued).toEqual([other, '{"type":"idle_notification"', 'plain words, not JSON'])
})

test('a delivery from no teammate passes unchanged, idle-shaped or not', async ($, on) => {
  const { queued } = engine(on)

  await $.session.receive({ origin: { kind: 'peer' }, text: IDLE })
  await $.session.receive({
    origin: { kind: 'coordinator', teammate: 'team-lead', isVerified: true },
    text: IDLE,
  })
  await $.session.receive({ origin: { kind: 'unclassified' }, text: IDLE })

  expect(queued).toEqual([IDLE, IDLE, IDLE])
})

test('a value stored under the previous shape tag is declined', async ($, on) => {
  const { queued, statuses } = engine(on)
  const entered = engineTakesPrompts(on)
  // What the previous version kept has no `nudged`, so it does not type under
  // this contract: the seed is this contract's layout under that version's
  // tag. Under any other tag, the module must read it as empty.
  on('state.get', { plugin: 'denubis-hook-quiet-agents', key: 'reports' }, () => ({
    value: {
      value: {
        shape: 'teammate-reports-3',
        value: {
          reported: { researcher: true },
          idle: ['researcher'],
          pending: ['researcher'],
          nudged: [],
        },
      },
      version: 3,
    },
  }))

  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.prompt.submit(typed('carry on'))

  expect(queued).toEqual([PREFIX + IDLE])
  expect(entered).toEqual([{ text: 'carry on', context: undefined }])
  expect(statuses).toEqual([])
})

const AGENTS: AgentInfo[] = [
  agent('a1', 'researcher', 'idle'),
  agent('a2', 'helper', 'idle'),
  agent('a3', 'scout', 'completed'),
  agent('a4', 'tester', 'failed'),
  agent('a5', 'builder', 'running'),
]

const TURN_END = {
  answer: 'ok',
  durationMs: 5,
  isAborted: false,
  turnId: 't1',
  reason: 'answer',
} as const

test('the main loop’s turn end shows the idle names with the done and failed counts', async ($, on) => {
  const agents = [...AGENTS]
  const { statuses } = engine(on, agents)
  on('turn.complete', (_, e) => ({ text: e.answer }))

  await $.turn.complete(TURN_END)
  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.turn.complete({ ...TURN_END, turnId: 't2' })
  agents.splice(0, agents.length, agent('a5', 'builder', 'running'))
  await $.session.send(mainSends('researcher', 'Now fix the tests.'))
  await $.turn.complete({ ...TURN_END, turnId: 't3' })
  await $.turn.complete({ ...TURN_END, turnId: 't4', agentId: 'a5' })

  expect(statuses).toEqual([
    'agents: 1 done, 1 failed',
    'agents idle: researcher; 1 done, 1 failed',
    'agents idle: researcher; 1 done, 1 failed',
    undefined,
    undefined,
  ])
})

// The turn-end nudge, as the human's ruling of 2026-10-24 words it.
const nudgeText = (names: string): string =>
  `quiet-agents: idle or finished agents: ${names}. Stop each with TaskStop. Then work through the pending questions in .notes/project_open-questions.md with the user one at a time, first looking for the answer in .notes, docs/architecture/decisions, and prior chat logs, and asking only where no evidence settles it. Where an agent's work is unfinished, continue it instead.`

// A plugin's prompt, framed under its name: never `asUser`.
const FROM_PLUGIN = { kind: 'plugin', name: 'denubis-hook-quiet-agents' } as const

// Stands for the engine at a turn's end: lists the agents given (the test
// changes the array between turns), ends each turn, and records each prompt
// that reached it. The module does not await its submit, so each turn end
// settles the event loop before the test looks.
const turnEngine = (on: On, agents: AgentInfo[]) => {
  const { statuses } = engine(on, agents)
  const submitted: { text: string; origin: PromptOrigin }[] = []
  on('prompt.submit', (_, e) => {
    submitted.push({ text: e.text, origin: e.origin })
    return { text: e.text, context: e.context, origin: e.origin }
  })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  const clock = mock.clock(on)
  const endTurn = async ($: Engine, turnId: string, agentId?: string): Promise<void> => {
    await $.turn.complete({ ...TURN_END, turnId, ...(agentId === undefined ? {} : { agentId }) })
    await clock.settle()
  }
  return { statuses, submitted, endTurn, clock }
}

test('the main loop’s turn end nudges once, naming each idle or finished agent once', async ($, on) => {
  const { submitted, endTurn } = turnEngine(on, [
    { ...agent('a1', 'researcher', 'idle'), teammateId: 'researcher@quiet' },
    agent('a3', 'scout', 'completed'),
    agent('a4', 'tester', 'failed'),
    agent('a5', 'builder', 'running'),
    agent('a6', 'drafter', 'killed'),
  ])
  // researcher is idle on both sources; builder by its consumed notice alone.
  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  await $.session.receive(fromTeammate('builder', REPORT))
  await $.session.receive(fromTeammate('builder', idleNotice('builder', 'done')))

  await endTurn($, 't1')

  expect(submitted).toEqual([
    { text: nudgeText('builder, researcher, scout, tester'), origin: FROM_PLUGIN },
  ])
})

test('the same agents at the next turn end raise no second nudge; one more raises it again', async ($, on) => {
  const agents = [agent('a1', 'researcher', 'idle'), agent('a3', 'scout', 'completed')]
  const { submitted, endTurn } = turnEngine(on, agents)

  await endTurn($, 't1')
  // The nudge's own turn ends with the same agents still listed.
  await endTurn($, 't2')
  agents.push(agent('a2', 'helper', 'idle'))
  await endTurn($, 't3')

  expect(submitted.map(s => s.text)).toEqual([
    nudgeText('researcher, scout'),
    nudgeText('helper, researcher, scout'),
  ])
})

test('a turn end with only working agents submits nothing', async ($, on) => {
  const { submitted, endTurn } = turnEngine(on, [agent('a5', 'builder', 'running')])

  await endTurn($, 't1')

  expect(submitted).toEqual([])
})

test('a turn end with none to name clears the record, so the same agents back are named again', async ($, on) => {
  const agents = [agent('a1', 'researcher', 'idle')]
  const { submitted, endTurn } = turnEngine(on, agents)

  await endTurn($, 't1')
  agents.splice(0, agents.length)
  await endTurn($, 't2')
  expect(submitted).toHaveLength(1)

  agents.push(agent('a1', 'researcher', 'idle'))
  await endTurn($, 't3')

  expect(submitted.map(s => s.text)).toEqual([nudgeText('researcher'), nudgeText('researcher')])
})

test('an idle teammate no longer listed leaves the status line and the next nudge', async ($, on) => {
  const agents = [agent('a1', 'researcher', 'idle')]
  const { statuses, submitted, endTurn } = turnEngine(on, agents)
  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))

  await endTurn($, 't1')
  // Stopped, and dropped from the list; a finished subagent is listed.
  agents.splice(0, agents.length, agent('a3', 'scout', 'completed'))
  await endTurn($, 't2')

  expect(submitted.map(s => s.text)).toEqual([nudgeText('researcher'), nudgeText('scout')])
  expect(statuses.at(-1)).toBe('agents: 1 done')
})

test('a subagent’s turn end submits nothing and writes no state', async ($, on) => {
  const { submitted, endTurn } = turnEngine(on, [agent('a1', 'researcher', 'idle')])
  const writes = stateWrites(on)

  await endTurn($, 't1', 'a5')
  expect(submitted).toEqual([])
  expect(writes).toEqual([])

  // The same agents at the main loop's end are named: the subagent's end
  // recorded nothing.
  await endTurn($, 't2')
  expect(submitted.map(s => s.text)).toEqual([nudgeText('researcher')])
})

test('a turn end whose agent list fails keeps the record, so no second nudge follows', async ($, on) => {
  // The engine's stand-ins written out: turnEngine's list cannot fail.
  let isListing = true
  on('agent.list', () => {
    if (!isListing) throw new Error('the roster is unreadable')
    return { value: [agent('a1', 'researcher', 'idle')] }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.log', () => ({ value: undefined }))
  const submitted: string[] = []
  on('prompt.submit', (_, e) => {
    submitted.push(e.text)
    return { text: e.text, context: e.context, origin: e.origin }
  })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  const clock = mock.clock(on)
  const endTurn = async (turnId: string): Promise<void> => {
    await $.turn.complete({ ...TURN_END, turnId })
    await clock.settle()
  }

  await endTurn('t1')
  isListing = false
  await endTurn('t2')
  isListing = true
  await endTurn('t3')

  expect(submitted).toEqual([nudgeText('researcher')])
})

test('/tidy stops each idle, done or failed agent and says what was refused', async ($, on) => {
  const asked: (string | undefined)[] = []
  on('command.register', () => ({ value: { command: 'tidy' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('agent.list', () => ({ value: AGENTS }))
  on('tool.call', (_, e) => {
    if (e.tool !== 'TaskStop') return { deny: 'only TaskStop in this test' }
    asked.push(e.task_id)
    if (e.task_id === 'a2') return { deny: 'the person said no' }
    if (e.task_id === 'a4') return { isError: true, result: undefined, text: 'no such task' }
    return { result: { message: 'stopped', task_id: e.task_id ?? '', task_type: 'local_agent' } }
  })

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({
    command: 'tidy',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 80 },
  })

  expect(asked).toEqual(['a1', 'a2', 'a3', 'a4'])
  expect(text).toContain('Stopped: researcher (a1), scout (a3)')
  expect(text).toContain('Refused: helper (a2): the person said no')
  expect(text).toContain('Failed: tester (a4): no such task')
  expect(text).not.toContain('builder')
})

test('/tidy with nothing to stop says so and calls no tool', async ($, on) => {
  on('command.register', () => ({ value: { command: 'tidy' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('agent.list', () => ({ value: [agent('a5', 'builder', 'running')] }))
  on('tool.call', () => ({ deny: 'no tool should be called' }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({
    command: 'tidy',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 80 },
  })

  expect(text).toBe('quiet-agents: no idle, completed or failed agents to stop.')
})

test('a turn the person interrupted or an error ended raises no nudge; the next answered turn does', async ($, on) => {
  const { submitted, endTurn, clock } = turnEngine(on, [agent('a3', 'scout', 'completed')])

  await $.turn.complete({ ...TURN_END, turnId: 't1', reason: 'aborted', isAborted: true })
  await clock.settle()
  await $.turn.complete({ ...TURN_END, turnId: 't2', reason: 'error' })
  await clock.settle()
  expect(submitted).toEqual([])

  await endTurn($, 't3')
  expect(submitted).toEqual([{ text: nudgeText('scout'), origin: FROM_PLUGIN }])
})

test('a refused turn raises no nudge either; each unanswered end still sets the status line', async ($, on) => {
  const { statuses, submitted, endTurn, clock } = turnEngine(on, [agent('a3', 'scout', 'completed')])

  await $.turn.complete({
    ...TURN_END,
    turnId: 't1',
    reason: 'refusal',
    refusal: { category: null, explanation: null },
  })
  await clock.settle()
  await $.turn.complete({ ...TURN_END, turnId: 't2', reason: 'aborted', isAborted: true })
  await clock.settle()
  await $.turn.complete({ ...TURN_END, turnId: 't3', reason: 'error' })
  await clock.settle()
  expect(submitted).toEqual([])
  expect(statuses).toEqual(['agents: 1 done', 'agents: 1 done', 'agents: 1 done'])

  await endTurn($, 't4')
  expect(submitted).toEqual([{ text: nudgeText('scout'), origin: FROM_PLUGIN }])
})

test('an unanswered turn end still drops a stopped teammate from the status line', async ($, on) => {
  const agents = [agent('a1', 'researcher', 'idle')]
  const { statuses, submitted, endTurn, clock } = turnEngine(on, agents)
  await $.session.receive(fromTeammate('researcher', REPORT))
  await $.session.receive(fromTeammate('researcher', IDLE))
  // Stopped, and dropped from the list; a finished subagent is listed.
  agents.splice(0, agents.length, agent('a3', 'scout', 'completed'))

  await $.turn.complete({ ...TURN_END, turnId: 't1', reason: 'aborted', isAborted: true })
  await clock.settle()
  expect(statuses.at(-1)).toBe('agents: 1 done')
  expect(submitted).toEqual([])

  // The unanswered end recorded no names: the next answered end nudges.
  await endTurn($, 't2')
  expect(submitted.map(s => s.text)).toEqual([nudgeText('scout')])
})
