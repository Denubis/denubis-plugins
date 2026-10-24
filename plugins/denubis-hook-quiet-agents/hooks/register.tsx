import { atom, read, update } from 'claude-code'
import type {
  AgentInfo,
  AgentStatus,
  EngineInterface,
  Frozen,
  PromptSubmitInput,
  Register,
} from 'claude-code'

import type { NoticeHashes, TeammateReports } from '../types'

// Agent key -> hash of the last notice body. Change the tag if the key or the
// hash changes: it declines what an earlier version stored, which outlives a
// reload.
const NO_NOTICES: NoticeHashes = {}
const lastNotice = atom({ plugin: 'denubis-hook-quiet-agents', key: 'lastNotice' } as const, NO_NOTICES, {
  shape: 'fnv1a32-first-line-1',
})

// Which teammates have reported, which went idle after reporting, and the
// names the last turn end found. The tag `teammate-reports-2` held
// `{ [teammate]: { lastReportAt } }` for the withdrawn time window, and
// `teammate-reports-3` had no `nudged`; this tag reads either as the initial.
const NO_TEAMMATES: TeammateReports = { reported: {}, idle: [], pending: [], nudged: [] }
const reports = atom({ plugin: 'denubis-hook-quiet-agents', key: 'reports' } as const, NO_TEAMMATES, {
  shape: 'teammate-reports-4',
})

const NOTICE_PREFIX =
  '[quiet-agents] An agent went idle. If this adds nothing the human has not been told, reply in one line or none; do not restate pending decisions. If its task is complete and you have no further work for it, stop it with TaskStop in this turn.\n'

const NOTICE_CONTEXT =
  "This turn was started by an agent notification, not by the human. If the notification adds nothing the human has not already been told, reply in one line or not at all. Do not restate decisions already pending with the human, do not write 'waiting on you', and do not summarise the agent's work again. If the agent reports its task complete and you have no further work for it, stop it with TaskStop in this turn."

const idleContext = (names: readonly string[]): string =>
  `quiet-agents: these agents went idle since your last turn, their reports already received: ${names.join(', ')}.`

const TIDY_SECTION = {
  id: 'quiet-agents:tidy',
  text: 'Agent hygiene: when a subagent or teammate reports its task complete and you have no further work for it, stop it with TaskStop in the same turn you acknowledge it. Do not leave a finished agent idle across a turn boundary. A turn started by an agent notification that carries nothing new is answered in one line or none.',
  scope: 'session',
} as const

// Matcher: derived from type docs; verify against agent-notice-log.jsonl.
// UNVERIFIED, and the secondary path: in agent-notice-log.jsonl (2026-10-24,
// lines 1-2) a teammate's report and its idle notice both arrived at
// session.receive as `peer`, and neither raised prompt.submit. The primary
// path is the session.receive hook below.
//   task-notification  PromptOrigin: "A background task's notification".
//   peer-send-message  PromptOrigin: "Another session's SendMessage delivery,
//                      model-authored and framed as a notification".
//   unclassified       PromptOrigin: "An idle notice or a delivery receipt the
//                      engine queued isMeta with no stamp"; UserMessage.origin:
//                      "`unclassified` for a teammate's (its drain stamps none)".
//                      Only with isMeta, so an unstamped same-user prompt passes.
// prompt.submit names no loop: PromptSubmitInput has no agentId, and the
// turn.start doc places prompt.submit on the main loop ("On the main loop it
// comes after prompt.submit settled the text"), so every submission counts.
const isAgentNotice = (e: Frozen<PromptSubmitInput>): boolean => {
  switch (e.origin.kind) {
    case 'task-notification':
    case 'peer-send-message':
      return true
    case 'unclassified':
      return e.isMeta === true
    default:
      return false
  }
}

const normalise = (text: string): string => text.replace(/\s+/g, ' ').trim()

// FNV-1a, 32 bits, over UTF-16 code units: stable across sessions and reloads,
// with no Node or crypto needed.
const hash = (text: string): string => {
  let value = 0x811c9dc5
  for (let i = 0; i < text.length; i += 1) {
    value ^= text.charCodeAt(i)
    value = Math.imul(value, 0x01000193)
  }
  return (value >>> 0).toString(16).padStart(8, '0')
}

// The types document no text framing for a notice (only the parsed render
// props UserMessage.task.id and UserMessage.from.name, which prompt.submit
// does not carry), so the key is the fallback: the origin kind plus a hash of
// the first line.
const agentKeyOf = (kind: string, text: string): string =>
  `${kind}:${hash(normalise(text.trim().split('\n')[0] ?? ''))}`

// Not JSON: an ordinary message, not an idle notice.
const parseJson = (text: string): unknown => {
  try {
    return JSON.parse(text)
  } catch (error) {
    if (error instanceof SyntaxError) {
      return undefined
    }
    throw error
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

// Observed shape (agent-notice-log.jsonl line 2): {"type":"idle_notification",
// "from","timestamp","idleReason","result"}. The text is the teammate's to
// write, so every field is untrusted: only `type` is read, and the teammate is
// taken from the mailbox's stamp, never from `from`.
const isIdleNotice = (text: string): boolean => {
  const parsed = parseJson(text)
  return isRecord(parsed) && parsed.type === 'idle_notification'
}

const isReported = (state: TeammateReports, teammate: string): boolean =>
  Object.hasOwn(state.reported, teammate)

// Entries, not an assignment, so any name (`__proto__` included) becomes an
// own key.
const markReported = (state: TeammateReports, teammate: string): TeammateReports => {
  const entry: [string, true] = [teammate, true]
  return { ...state, reported: Object.fromEntries([...Object.entries(state.reported), entry]) }
}

const withName = (names: readonly string[], name: string): string[] =>
  names.includes(name) ? [...names] : [...names, name]

// Its idle notice consumed: the teammate joins the status line's names and
// the names the next prompt carries.
const markIdle = (state: TeammateReports, teammate: string): TeammateReports => ({
  ...state,
  idle: withName(state.idle, teammate).sort(),
  pending: withName(state.pending, teammate),
})

// The main conversation sent one of `names` a message: its report no longer
// answers for what it does next, and it is no longer idle.
const forgetNames = (state: TeammateReports, names: readonly string[]): TeammateReports => ({
  ...state,
  reported: Object.fromEntries(
    Object.entries(state.reported).filter(([name]) => !names.includes(name)),
  ),
  idle: state.idle.filter(name => !names.includes(name)),
})

const LEFTOVER: readonly AgentStatus[] = ['idle', 'completed', 'failed']

const leftovers = (agents: readonly AgentInfo[]): AgentInfo[] =>
  agents.filter(agent => LEFTOVER.includes(agent.status))

// `$.ui.status` keeps one line per plugin, so the idle names and the turn
// end's counts share it. The engine's own `idle` count is left out: the names
// stand for it.
const statusLine = (idle: readonly string[], agents: readonly AgentInfo[]): string | undefined => {
  const counts: [number, string][] = [
    [agents.filter(a => a.status === 'completed').length, 'done'],
    [agents.filter(a => a.status === 'failed').length, 'failed'],
  ]
  const tally = counts
    .filter(([count]) => count > 0)
    .map(([count, word]) => `${count} ${word}`)
    .join(', ')
  if (idle.length > 0) {
    const names = `agents idle: ${idle.join(', ')}`
    return tally === '' ? names : `${names}; ${tally}`
  }
  return tally === '' ? undefined : `agents: ${tally}`
}

const describeError = (error: unknown): string =>
  error instanceof Error ? `${error.name}: ${error.message}` : String(error)

// An empty list when the engine cannot answer: the counts drop out of the
// status line and a recipient is matched by its name alone.
const listAgents = async ($: EngineInterface): Promise<readonly AgentInfo[]> => {
  try {
    return await $.agent.list()
  } catch (error) {
    $.ui.log(`quiet-agents: could not list agents: ${describeError(error)}`, { to: 'debug' })
    return []
  }
}

// Never fails the hook that calls it: a consumed notice stays consumed.
const showStatus = async ($: EngineInterface, idle: readonly string[]): Promise<void> => {
  const agents = await listAgents($)
  try {
    $.ui.status(statusLine(idle, agents))
  } catch (error) {
    $.ui.log(`quiet-agents: could not set the status line: ${describeError(error)}`, { to: 'debug' })
  }
}

// SendMessage's `to`, per its schema: "a name from ListAgents (append its
// \" [ref]\" only when a listing or an error shows one), a teammate name,
// \"main\", or a background agent's agentId". The teammate names it may stand
// for: as written, without a ref, and the name of the agent whose `id` or
// `teammateId` (`<name>@<team>`) it is. A name cleared in error only lets that
// teammate's next idle notice through, prefixed.
const REF_SUFFIX = /\s+\[[^\]]*\]$/

const recipientNames = async ($: EngineInterface, to: string): Promise<string[]> => {
  const names = new Set([to, to.replace(REF_SUFFIX, '')])
  for (const agent of await listAgents($)) {
    if (agent.name !== undefined && (agent.id === to || agent.teammateId === to)) {
      names.add(agent.name)
    }
  }
  return [...names]
}

// Run before the send goes on, so a reply that lands before the send resolves
// is not wiped.
const forget = async ($: EngineInterface, to: string): Promise<void> => {
  const names = await recipientNames($, to)
  const before = await read($, reports)
  const wasIdle = before.idle.some(name => names.includes(name))
  if (!wasIdle && !names.some(name => isReported(before, name))) {
    return
  }

  const after = await update($, reports, state => forgetNames(state, names))
  if (wasIdle) {
    await showStatus($, after.idle)
  }
}

// Removes exactly the names it answers, so a name consumed meanwhile waits
// for the next prompt.
const takePending = async ($: EngineInterface): Promise<readonly string[]> => {
  const { pending } = await read($, reports)
  if (pending.length > 0) {
    await update($, reports, state => ({
      ...state,
      pending: state.pending.filter(name => !pending.includes(name)),
    }))
  }
  return pending
}

const putBackPending = async ($: EngineInterface, names: readonly string[]): Promise<void> => {
  if (names.length === 0) {
    return
  }
  await update($, reports, state => ({
    ...state,
    pending: [...names, ...state.pending.filter(name => !names.includes(name))],
  }))
}

const labelOf = (agent: AgentInfo): string => `${agent.name ?? agent.description} (${agent.id})`

const tidy = async ($: EngineInterface): Promise<string> => {
  const agents = leftovers(await $.agent.list())
  if (agents.length === 0) {
    return 'quiet-agents: no idle, completed or failed agents to stop.'
  }

  const stopped: string[] = []
  const refused: string[] = []
  const failed: string[] = []
  // One at a time: each stop goes through the permission check and its dialog.
  for (const agent of agents) {
    try {
      const ran = await $.tool.call({ tool: 'TaskStop', task_id: agent.id })
      if (ran.deny !== undefined) {
        refused.push(`${labelOf(agent)}: ${ran.deny}`)
      } else if (ran.isError === true) {
        failed.push(`${labelOf(agent)}: ${ran.text ?? 'TaskStop reported an error'}`)
      } else {
        stopped.push(labelOf(agent))
      }
    } catch (error) {
      failed.push(`${labelOf(agent)}: ${describeError(error)}`)
    }
  }

  return [
    `quiet-agents /tidy: ${stopped.length} stopped, ${refused.length} refused, ${failed.length} failed.`,
    stopped.length > 0 ? `Stopped: ${stopped.join(', ')}` : undefined,
    refused.length > 0 ? `Refused: ${refused.join('; ')}` : undefined,
    failed.length > 0 ? `Failed: ${failed.join('; ')}` : undefined,
  ]
    .filter(line => line !== undefined)
    .join('\n')
}

// The ruled text (2026-10-24), with the names put in.
const nudgeText = (names: readonly string[]): string =>
  `quiet-agents: idle or finished agents: ${names.join(', ')}. Stop each with TaskStop. Then work through the pending questions in .notes/project_open-questions.md with the user one at a time, first looking for the answer in .notes, docs/architecture/decisions, and prior chat logs, and asking only where no evidence settles it. Where an agent's work is unfinished, continue it instead.`

// The name both sources share. The mailbox stamps `origin.teammate`, the
// member's name in its team; a listed teammate's `name` is "its name in the
// team" and its `teammateId` is `<name>@<team>`. An agent with no name goes
// by its id: TaskStop takes a teammate or a named agent by name, any by id.
const nameOf = (agent: AgentInfo): string =>
  agent.name ?? agent.teammateId?.split('@')[0] ?? agent.id

const sameNames = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((name, i) => name === b[i])

// One turn end's step over the reports, pure so `update` can run it again on
// a miss. Idle names no listed agent answers to are dropped (stopped and
// gone); what is left joins every idle, done or failed listed agent, one
// name each, sorted. Those names are recorded; `nudge` is set when they are
// some and differ from the last recorded. An end without an answer only
// drops: it records no names and nudges nothing (ruled 2026-10-24), so the
// next answered end still compares against what was last nudged.
type TurnEndStep = {
  state: TeammateReports
  nudge: readonly string[] | undefined
  isPruned: boolean
  isChanged: boolean
}

const turnEndStep = (
  state: TeammateReports,
  agents: readonly AgentInfo[],
  isAnswered: boolean,
): TurnEndStep => {
  const listed = new Set(agents.map(nameOf))
  const idle = state.idle.filter(name => listed.has(name))
  const isPruned = !sameNames(idle, state.idle)
  if (!isAnswered) {
    return { state: { ...state, idle }, nudge: undefined, isPruned, isChanged: isPruned }
  }
  const names = [...new Set([...idle, ...leftovers(agents).map(nameOf)])].sort()
  const isNew = !sameNames(names, state.nudged)
  return {
    state: { ...state, idle, nudged: names },
    nudge: isNew && names.length > 0 ? names : undefined,
    isPruned,
    isChanged: isPruned || isNew,
  }
}

// Not awaited: the call resolves only as the nudge's own turn starts, once
// the session is idle, and this turn is still ending.
const submitNudge = ($: EngineInterface, names: readonly string[]): void => {
  void $.prompt.submit({ text: nudgeText(names) }).then(
    result => {
      if (result.drop !== undefined) {
        $.ui.log(`quiet-agents: the nudge was dropped: ${result.drop}`, { to: 'debug' })
      }
    },
    (error: unknown) => {
      $.ui.log(`quiet-agents: could not submit the nudge: ${describeError(error)}`, { to: 'debug' })
    },
  )
}

// Never stops an agent: the nudge asks the model, whose TaskStop asks
// permission as usual. A list the engine could not give changes nothing, as
// an empty one would drop every idle name and clear the record.
const nudgeAtTurnEnd = async ($: EngineInterface, isAnswered: boolean): Promise<void> => {
  let agents: readonly AgentInfo[]
  try {
    agents = await $.agent.list()
  } catch (error) {
    $.ui.log(`quiet-agents: could not list agents, so no nudge: ${describeError(error)}`, { to: 'debug' })
    return
  }

  let step = turnEndStep(await read($, reports), agents, isAnswered)
  if (!step.isChanged) {
    return
  }

  const after = await update($, reports, state => {
    step = turnEndStep(state, agents, isAnswered)
    return step.state
  })
  if (step.isPruned) {
    await showStatus($, after.idle)
  }
  if (step.nudge !== undefined) {
    submitNudge($, step.nudge)
  }
}

export const register: Register = on => {
  // One hook: the engine refuses a second prompt.submit hook without a
  // matcher. Part 1, secondary path: mute a repeated notice, frame a new one.
  // And name, once, the teammates whose idle notices were consumed since the
  // last prompt.submit, beside the next prompt of any origin that enters.
  on('prompt.submit', async ($, e, next) => {
    const notice = isAgentNotice(e)
      ? { key: agentKeyOf(e.origin.kind, e.text), body: hash(normalise(e.text)) }
      : undefined
    if (notice !== undefined && (await read($, lastNotice))[notice.key] === notice.body) {
      return { drop: `quiet-agents: repeat notice from ${notice.key}, muted` }
    }

    const idle = await takePending($)
    const added = [
      ...(notice === undefined ? [] : [NOTICE_CONTEXT]),
      ...(idle.length === 0 ? [] : [idleContext(idle)]),
    ]
    const result = await next(added.length === 0 ? e : { ...e, context: [...(e.context ?? []), ...added] })
    if (result.drop !== undefined) {
      // Not entered: the names wait for the next prompt, and a notice dropped
      // beneath is not a repeat.
      await putBackPending($, idle)
      return result
    }

    if (notice !== undefined) {
      await update($, lastNotice, hashes => ({ ...hashes, [notice.key]: notice.body }))
    }

    return result
  })

  // Part 1, primary path: a verified teammate's message to the main
  // conversation records that it reported; its idle notice is consumed while
  // that report stands, and framed with the prefix otherwise. A delivery to a
  // teammate's own loop (`e.agentId` set, agent-notice-log.jsonl line 3) is
  // left alone.
  on('session.receive', async ($, e, next) => {
    if (e.agentId !== undefined) {
      return next(e)
    }

    const origin = e.origin
    if (origin.kind !== 'peer' || !('teammate' in origin) || !origin.isVerified) {
      return next(e)
    }

    const teammate = origin.teammate
    if (!isIdleNotice(e.text)) {
      if (!isReported(await read($, reports), teammate)) {
        await update($, reports, state => markReported(state, teammate))
      }

      return next(e)
    }

    const prefixed = { ...e, text: NOTICE_PREFIX + e.text }
    if (!isReported(await read($, reports), teammate)) {
      return next(prefixed)
    }

    // Asked again inside the write: a send to the teammate may land between.
    const after = await update($, reports, state =>
      isReported(state, teammate) ? markIdle(state, teammate) : state,
    )
    if (!isReported(after, teammate)) {
      return next(prefixed)
    }

    await showStatus($, after.idle)
    return { consumed: `quiet-agents: idle notice from ${teammate}; its report was already received` }
  })

  // The main conversation's message to a teammate clears its report and takes
  // it off the idle list. session.send is receive's dual, `to` a string and
  // `agentId` absent for the main conversation, but its doc names "a
  // plain-text message"; SendMessage also carries a plan approval or a
  // shutdown request, which only tool.call is known to see. Both run;
  // the second finds nothing left to clear.
  on('session.send', async ($, e, next) => {
    if (e.agentId === undefined) {
      await forget($, e.to)
    }

    return next(e)
  })

  on('tool.call', { tool: 'SendMessage' }, async ($, e, next) => {
    if (e.agentId === undefined && e.tool === 'SendMessage' && typeof e.to === 'string') {
      await forget($, e.to)
    }

    return next(e)
  })

  // Part 2: the hygiene section, last, after the cache boundary; not in an
  // in-process teammate's render of the lead's prompt (trait `teammate`).
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (e.traits.includes('teammate')) {
      return composed
    }

    return {
      sections: [...composed.sections.filter(s => s.id !== TIDY_SECTION.id), TIDY_SECTION],
    }
  })

  // Part 3: visibility, then the nudge about idle or finished agents. Nothing
  // here stops an agent unasked.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId !== undefined) {
      return result
    }

    await showStatus($, (await read($, reports)).idle)
    // Ruled 2026-10-24: the nudge fires only when the model answered. A turn
    // the person interrupted or an API error ended would otherwise queue a
    // plugin prompt ahead of what the person meant to type next. Any end
    // still drops a stopped teammate's name from the status line.
    await nudgeAtTurnEnd($, e.reason === 'answer')
    return result
  })

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'tidy',
      description: 'Stop idle, completed and failed agents (each stop asks permission as usual)',
    })

    return next(e)
  })

  on('command.run', { command: 'tidy' }, async $ => ({ text: await tidy($) }))
}
