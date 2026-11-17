import { atom, read, update } from 'claude-code'
import type {
  AgentInfo,
  AgentStatus,
  EngineInterface,
  Frozen,
  PromptSubmitInput,
  Register,
  SessionReceiveInput,
  SessionReceiveResult,
} from 'claude-code'

import type { MutedAgents, NoteEntry, NoticeHashes, ReminderNote, TeammateReports } from '../types'

// Agent key -> hash of the last notice body. Change the tag if the key or the
// hash changes: it declines what an earlier version stored, which outlives a
// reload.
const NO_NOTICES: NoticeHashes = {}
const lastNotice = atom({ plugin: 'denubis-hook-quiet-agents', key: 'lastNotice' } as const, NO_NOTICES, {
  shape: 'fnv1a32-first-line-1',
})

// Which teammates have reported, which went idle after reporting, and which
// agents a turn end has named for the reminder. The tag `teammate-reports-2` held
// `{ [teammate]: { lastReportAt } }` for the withdrawn time window,
// `teammate-reports-3` had no `nudged`, and `teammate-reports-4` kept the
// last turn end's names in `nudged`; this tag reads any of them as the
// initial.
const NO_TEAMMATES: TeammateReports = { reported: {}, idle: [], pending: [], nudgedIds: [] }
const reports = atom({ plugin: 'denubis-hook-quiet-agents', key: 'reports' } as const, NO_TEAMMATES, {
  shape: 'teammate-reports-5',
})

// The ids of the agents the person muted (ruled 2026-11-15): a mute goes by
// the agent, so a new agent under a muted agent's name is not muted.
const NO_MUTED: MutedAgents = []
const muted = atom({ plugin: 'denubis-hook-quiet-agents', key: 'muted' } as const, NO_MUTED, {
  shape: 'muted-ids-1',
})

// The agents a main-loop turn end named that the reminder has not yet named
// to the model: it rides on the next message (ruled 2026-11-15).
const NO_NOTE: ReminderNote = []
const note = atom({ plugin: 'denubis-hook-quiet-agents', key: 'note' } as const, NO_NOTE, {
  shape: 'reminder-note-1',
})

const NOTICE_HEAD =
  '[quiet-agents] An agent went idle. If this adds nothing the human has not been told, it gets no reply; do not restate pending decisions.'

const NOTICE_STOP = ' If its task is complete and you have no further work for it, stop it with TaskStop in this turn.'

const NOTICE_PREFIX = `${NOTICE_HEAD}${NOTICE_STOP}\n`

// A muted agent's notice gives the model no prompt to stop it: the mute is
// for "this nag" (ruled 2026-11-15; reading it as every prompt to stop the
// agent is the assistant's).
const MUTED_NOTICE_PREFIX = `${NOTICE_HEAD}\n`

// Beside an agent notice that arrives as a prompt. PromptSubmitInput names no
// agent (its notice origins carry no name or id), so a mute cannot reach
// this, and it keeps its prompt to stop the agent.
const NOTICE_CONTEXT =
  "This turn was started by an agent notification, not by the human. If the notification adds nothing the human has not already been told, it gets no reply. Do not restate decisions already pending with the human, do not write 'waiting on you', and do not summarise the agent's work again. If the agent reports its task complete and you have no further work for it, stop it with TaskStop in this turn."

const idleContext = (names: readonly string[]): string =>
  `quiet-agents: these agents went idle since your last turn, their reports already received: ${names.join(', ')}.`

const TIDY_SECTION = {
  id: 'quiet-agents:tidy',
  text: 'Agent hygiene: when a subagent or teammate reports its task complete and you have no further work for it, stop it with TaskStop in the same turn you acknowledge it. Do not leave a finished agent idle across a turn boundary. A turn started by an agent notification that carries nothing new gets no reply. Treat notifications as inputs to work, not requests for a conversational reply: reconcile reports and tickets, evaluate deliverables, and continue authorized work. Review new findings or questions even inside a completion report or a closed task. An idle worker with outstanding corrections needs follow-up, not a completion assumption; return verified defects to it under the three-failure stop. Once completion is verified and owed corrections are resolved, close owned workers and stop their unneeded monitors through supported controls. Preserve human peer sessions. An interrupt is not proof of closure; report a missing closure capability once if material. Handle duplicate reports silently, cleaning up the owned worker if its work is already verified complete, and continue work in progress without summarizing it; neither calls for an acknowledgment, count, recap, or one-line status update. Answer explicit human status requests directly. Communicate changed results, consequential corrections, or a necessary human decision. Unchanged open questions and already-processed reports are not news: omit reminders, pointer replies, unrelated old tasks, dispatch recaps, and repeated waiting notices. Ask a human-only question once, stop monitors over idle dependent work, and await the answer. When the human asks for orientation or resumes after a substantial break, state the unresolved decisions and their consequences in full without referring to earlier messages, then ask the first question that needs their answer.',
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

// A message's recipient: the teammate names it may stand for, and the ids of
// the listed agents it reaches.
type Recipients = { names: readonly string[]; ids: readonly string[] }

// The main conversation sent the recipient a message: its report no longer
// answers for what it does next, it is no longer idle, and a turn end may name
// it again once it next stops.
const forgetRecipients = (state: TeammateReports, { names, ids }: Recipients): TeammateReports => ({
  ...state,
  reported: Object.fromEntries(
    Object.entries(state.reported).filter(([name]) => !names.includes(name)),
  ),
  idle: state.idle.filter(name => !names.includes(name)),
  nudgedIds: state.nudgedIds.filter(id => !ids.includes(id)),
})

const LEFTOVER: readonly AgentStatus[] = ['idle', 'completed', 'failed']

// An agent a plugin started (`spawnedBy`) is the plugin's to manage, not the
// model's: question-zone's finished checkers were named in the reminder, and
// TaskStop on them answered "is not running (status: completed)" (live,
// 2026-11-08). The reminder and /tidy go by it; the status line counts by status
// on its own.
const isLeftover = (agent: AgentInfo): boolean =>
  LEFTOVER.includes(agent.status) && agent.spawnedBy === undefined

const leftovers = (agents: readonly AgentInfo[]): AgentInfo[] => agents.filter(isLeftover)

// The name both sources share. The mailbox stamps `origin.teammate`, the
// member's name in its team; a listed teammate's `name` is "its name in the
// team" and its `teammateId` is `<name>@<team>`. An agent with no name goes
// by its id: TaskStop takes a teammate or a named agent by name, any by id.
const nameOf = (agent: AgentInfo): string =>
  agent.name ?? agent.teammateId?.split('@')[0] ?? agent.id

// The names of the listed agents that are `waiting`: "on background work it
// owns, on a plan's approval or, in a background subagent, on an Agent call
// alone" (AgentStatus). Its consumed idle notice does not make any such agent
// idle, whatever it waits on. Any other status leaves that notice standing,
// since the roster can still say `running` when the notice arrives. A
// teammate in a terminal pane of its own is only ever `running` or `idle` by
// its roster, so this cannot see its background work.
const waitingNames = (agents: readonly AgentInfo[]): Set<string> =>
  new Set(agents.filter(agent => agent.status === 'waiting').map(nameOf))

// An agent the reminder names: idle, done or failed by its roster word, or
// idle by its consumed notice (one of `idle`) and not `waiting`. A turn end
// goes by it, and so does the reminder as it rides. So at ride time an agent
// now `waiting`, or no longer idle, done or failed by its roster word, waits
// for its next stop, unless its consumed notice stands: one woken on its own
// after that notice and listed `running` is still named, as at a turn end,
// since the roster can lag the notice.
const isToName = (agent: AgentInfo, idle: readonly string[]): boolean =>
  isLeftover(agent) || (agent.status !== 'waiting' && idle.includes(nameOf(agent)))

// The names of the listed agents the person muted.
const mutedNames = (agents: readonly AgentInfo[], ids: MutedAgents): Set<string> =>
  new Set(agents.filter(agent => ids.includes(agent.id)).map(nameOf))

// `$.ui.status` keeps one line per plugin, so the idle names and the turn
// end's counts share it. The idle names are the teammates whose idle notice
// was consumed, and every listed idle agent a turn end has named, so an agent
// the model keeps stays in view (ruled 2026-11-15), less any now `waiting`.
// The muted agents are named apart, so a mute
// stays in view. The engine's own `idle` count is left out: the names stand
// for it.
const statusLine = (
  state: TeammateReports,
  agents: readonly AgentInfo[],
  mutedIds: MutedAgents,
): string | undefined => {
  const silenced = mutedNames(agents, mutedIds)
  const kept = agents.filter(
    agent => agent.status === 'idle' && state.nudgedIds.includes(agent.id) && !mutedIds.includes(agent.id),
  )
  const waiting = waitingNames(agents)
  const notified = state.idle.filter(name => !waiting.has(name) && !silenced.has(name))
  const idle = [...new Set([...notified, ...kept.map(nameOf)])].sort()
  const counts: [number, string][] = [
    [agents.filter(a => a.status === 'completed').length, 'done'],
    [agents.filter(a => a.status === 'failed').length, 'failed'],
  ]
  const tally = counts
    .filter(([count]) => count > 0)
    .map(([count, word]) => `${count} ${word}`)
    .join(', ')
  const named = [
    idle.length > 0 ? `idle: ${idle.join(', ')}` : undefined,
    silenced.size > 0 ? `muted: ${[...silenced].sort().join(', ')}` : undefined,
  ].filter(part => part !== undefined)
  if (named.length > 0) {
    const names = `agents ${named.join('; ')}`
    return tally === '' ? names : `${names}; ${tally}`
  }
  return tally === '' ? undefined : `agents: ${tally}`
}

const describeError = (error: unknown): string =>
  error instanceof Error ? `${error.name}: ${error.message}` : String(error)

// An empty list when the engine cannot answer: the counts and the kept
// agents' names drop out of the status line, and a recipient is matched by
// its name alone, so it reaches no id and stays on the record of agents named.
const listAgents = async ($: EngineInterface): Promise<readonly AgentInfo[]> => {
  try {
    return await $.agent.list()
  } catch (error) {
    $.ui.log(`quiet-agents: could not list agents: ${describeError(error)}`, { to: 'debug' })
    return []
  }
}

// Never fails the hook that calls it: a consumed notice stays consumed.
const showStatus = async ($: EngineInterface, state: TeammateReports): Promise<void> => {
  const agents = await listAgents($)
  const mutedIds = await read($, muted)
  try {
    $.ui.status(statusLine(state, agents, mutedIds))
  } catch (error) {
    $.ui.log(`quiet-agents: could not set the status line: ${describeError(error)}`, { to: 'debug' })
  }
}

// SendMessage's `to`, per its schema: "a name from ListAgents (append its
// \" [ref]\" only when a listing or an error shows one), a teammate name,
// \"main\", or a background agent's agentId". The teammate names it may stand
// for: as written, without a ref, and the name of the agent whose `id` or
// `teammateId` (`<name>@<team>`) it is. The agents it reaches: each listed
// one whose id or `teammateId` it is, or that goes by one of those names. A
// name or id cleared in error only lets that agent's next idle notice
// through, prefixed, or its next stop be named. A list the engine cannot give
// reaches no id, so that agent's next stop is not named.
const REF_SUFFIX = /\s+\[[^\]]*\]$/

const recipients = async ($: EngineInterface, to: string): Promise<Recipients> => {
  const names = new Set([to, to.replace(REF_SUFFIX, '')])
  const agents = await listAgents($)
  for (const agent of agents) {
    if (agent.name !== undefined && (agent.id === to || agent.teammateId === to)) {
      names.add(agent.name)
    }
  }
  const ids = agents
    .filter(agent => agent.id === to || agent.teammateId === to || names.has(nameOf(agent)))
    .map(agent => agent.id)
  return { names: [...names], ids }
}

// Run before the send goes on, so a reply that lands before the send resolves
// is not wiped.
const forget = async ($: EngineInterface, to: string): Promise<void> => {
  const recipient = await recipients($, to)
  const before = await read($, reports)
  // Either one is on the status line by name.
  const wasShown =
    before.idle.some(name => recipient.names.includes(name)) ||
    before.nudgedIds.some(id => recipient.ids.includes(id))
  if (!wasShown && !recipient.names.some(name => isReported(before, name))) {
    return
  }

  const after = await update($, reports, state => forgetRecipients(state, recipient))
  if (wasShown) {
    await showStatus($, after)
  }
}

// The main conversation as an agent's SendMessage spells it: "main", per the
// tool's schema, or the lead's name in its team, `team-lead`, per
// SessionReceiveOrigin.teammate. Any other recipient is another agent.
const MAIN_CONVERSATION: readonly string[] = ['main', 'team-lead']

const isToMain = (to: string): boolean => MAIN_CONVERSATION.includes(to.replace(REF_SUFFIX, ''))

// The name the agent's idle notice will carry as `origin.teammate`: its name,
// else the `<name>` of its `teammateId`; none for an agent with neither.
const teammateNameOf = (agent: AgentInfo): string | undefined =>
  agent.name ?? agent.teammateId?.split('@')[0]

// An agent's delivered send to the main conversation is its report, marked at
// the send. Its SendMessage call waits on this chain for its result (the model
// reads a refused send's `reason` as the tool's result), so the mark is set
// before that agent's turn can end and its idle notice arrive. The report
// itself may reach the main conversation only when dequeued, after the idle
// notice was judged (agent-notice-log.jsonl, 2026-10-24: the idle notice at
// 22:59:24.29Z, the report at 22:59:24.99Z). An agent the list cannot name is
// not marked.
const markSender = async ($: EngineInterface, agentId: string): Promise<void> => {
  const sender = (await listAgents($)).find(agent => agent.id === agentId)
  const teammate = sender === undefined ? undefined : teammateNameOf(sender)
  if (teammate === undefined) {
    $.ui.log(
      `quiet-agents: no name for agent ${agentId}, which sent to the main conversation, so its report is not marked`,
      { to: 'debug' },
    )
    return
  }

  if (!isReported(await read($, reports), teammate)) {
    await update($, reports, state => markReported(state, teammate))
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

// A mailbox delivery from one of this session's teammates. The harness
// verifies only what it wrote itself; a teammate in a terminal pane of its own
// writes the team's inbox file, and its deliveries arrive unverified (every
// `peer` delivery in agent-notice-log.jsonl, 2026-11-02 to 2026-11-08). So an
// unverified name counts when `$.agent.list()` names an agent of this session
// by it. Whatever can write that file can claim a listed name; the most that
// does is mark the name reported and so hide that agent's next idle notice.
const isTeammate = async ($: EngineInterface, teammate: string, isVerified: boolean): Promise<boolean> =>
  isVerified || (await listAgents($)).some(agent => teammateNameOf(agent) === teammate)

// A teammate the person muted, by its listed agent's id: the name a delivery
// carries is matched to the listed agents that go by it.
const isMuted = async ($: EngineInterface, teammate: string): Promise<boolean> => {
  const mutedIds = await read($, muted)
  if (mutedIds.length === 0) {
    return false
  }
  return (await listAgents($)).some(
    agent => teammateNameOf(agent) === teammate && mutedIds.includes(agent.id),
  )
}

const labelOf = (agent: AgentInfo): string => `${agent.name ?? agent.description} (${agent.id})`

// A muted agent is one the person keeps: /tidy leaves it alone.
const tidy = async ($: EngineInterface): Promise<string> => {
  const mutedIds = await read($, muted)
  const agents = leftovers(await $.agent.list()).filter(agent => !mutedIds.includes(agent.id))
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

// `/quiet-agents`, the mod's own command; its subcommands mute and unmute an
// agent the person keeps (ruled 2026-11-15). The person types it: the model
// is given no tool to mute with.
const USAGE =
  'quiet-agents: /quiet-agents mute <agent> stops the naming of that agent: it is left out of the end-of-turn reminder, the idle names and /tidy, until /quiet-agents unmute <agent> or the agent is stopped. Its messages and idle notices are handled as before. /quiet-agents mute alone lists the muted agents.'

// The listed agents `who` names: by name, id, or teammate address.
const agentsGoingBy = (agents: readonly AgentInfo[], who: string): AgentInfo[] =>
  agents.filter(agent => nameOf(agent) === who || agent.id === who || agent.teammateId === who)

const listMuted = async ($: EngineInterface): Promise<string> => {
  const mutedIds = await read($, muted)
  if (mutedIds.length === 0) {
    return 'quiet-agents: no agents muted.'
  }
  const agents = await listAgents($)
  const labels = mutedIds.map(id => {
    const agent = agents.find(candidate => candidate.id === id)
    return agent === undefined ? id : labelOf(agent)
  })
  return `quiet-agents: muted: ${labels.join(', ')}.`
}

const mute = async ($: EngineInterface, who: string): Promise<string> => {
  const found = agentsGoingBy(await $.agent.list(), who)
  if (found.length === 0) {
    return `quiet-agents: no agent of this session goes by ${who}, so nothing was muted.`
  }
  const ids = found.map(agent => agent.id)
  await update($, muted, before => [...before, ...ids.filter(id => !before.includes(id))])
  await showStatus($, await read($, reports))
  return `quiet-agents: muted ${found.map(labelOf).join(', ')}.`
}

const unmute = async ($: EngineInterface, who: string): Promise<string> => {
  const targets = new Set([who, ...agentsGoingBy(await $.agent.list(), who).map(agent => agent.id)])
  const before = await read($, muted)
  if (!before.some(id => targets.has(id))) {
    return `quiet-agents: ${who} is not muted.`
  }
  await update($, muted, ids => ids.filter(id => !targets.has(id)))
  await showStatus($, await read($, reports))
  return `quiet-agents: unmuted ${who}.`
}

const quietAgentsCommand = async ($: EngineInterface, args: string): Promise<string> => {
  const [subcommand = '', ...rest] = args.trim().split(/\s+/)
  const who = rest.join(' ')
  if (subcommand === 'mute') {
    return who === '' ? listMuted($) : mute($, who)
  }
  if (subcommand === 'unmute' && who !== '') {
    return unmute($, who)
  }
  return USAGE
}

// The reminder, with the names put in. Since 2026-11-08 it sends questions
// for the person to the question zone (denubis-hook-question-zone) in place
// of the open-questions file. One line, so it can lead a delivery.
const reminderText = (entries: ReminderNote): string =>
  `quiet-agents: idle or finished agents: ${[...new Set(entries.map(entry => entry.name))].sort().join(', ')}. Stop each with TaskStop, unless its work is unfinished: then continue it instead. Ask the person any question through the question zone's mcp__denubis-hook-question-zone__ask tool, never in chat.`

const sameNames = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((name, i) => name === b[i])

// One turn end's step over the reports, pure so `update` can run it again on
// a miss. Idle names no listed agent answers to are dropped (stopped and
// gone). The agents to name are the listed ones `isToName` holds. Those no
// turn end has named yet are named, and their ids recorded (ruled
// 2026-11-15). An id stays recorded until the main conversation sends that
// agent a message (`forget`), so an agent the model keeps is named once,
// however often it wakes and stops on its own and others come and go. An id
// is not dropped when its agent leaves the list: a new agent under the same
// name has an id of its own. An end without an answer only drops idle names:
// it names and records nothing (ruled 2026-10-24).
type TurnEndStep = {
  state: TeammateReports
  named: ReminderNote
  isChanged: boolean
}

const turnEndStep = (
  state: TeammateReports,
  agents: readonly AgentInfo[],
  isAnswered: boolean,
  mutedIds: MutedAgents,
): TurnEndStep => {
  const listed = new Set(agents.map(nameOf))
  const idle = state.idle.filter(name => listed.has(name))
  const isPruned = !sameNames(idle, state.idle)
  const unnamed = isAnswered
    ? agents.filter(
        agent => isToName(agent, idle) && !state.nudgedIds.includes(agent.id) && !mutedIds.includes(agent.id),
      )
    : []
  if (unnamed.length === 0) {
    return { state: { ...state, idle }, named: [], isChanged: isPruned }
  }
  return {
    state: { ...state, idle, nudgedIds: [...state.nudgedIds, ...unnamed.map(agent => agent.id)] },
    named: unnamed.map(agent => ({ id: agent.id, name: nameOf(agent) })),
    isChanged: true,
  }
}

// The note after a turn end, pure: its entries whose agent is still listed
// and on the record, then the agents this end named, no repeated id.
const noteAtTurnEnd = (
  entries: ReminderNote,
  agents: readonly AgentInfo[],
  nudgedIds: readonly string[],
  named: ReminderNote,
): ReminderNote => {
  const listed = new Set(agents.map(agent => agent.id))
  const kept = entries.filter(entry => listed.has(entry.id) && nudgedIds.includes(entry.id))
  return [...kept, ...named.filter(entry => !kept.some(other => other.id === entry.id))]
}

const sameIds = (a: ReminderNote, b: ReminderNote): boolean =>
  a.length === b.length && a.every((entry, i) => entry.id === b[i]?.id)

// The reminder's entries taken to ride on a message, and the names those
// agents had waiting for the idle line, taken with them.
type Riding = { entries: ReminderNote; pending: readonly string[] }

const NOTHING_RIDES: Riding = { entries: [], pending: [] }

// The entries due to ride on a message now, taken from the note: each whose
// agent is listed, still on the record (a message from the main
// conversation since takes it off), not muted, still one `isToName`
// holds, and not one the message already prompts the model to stop (`except`:
// "we shouldn't have double-reminders", ruled 2026-11-15). The rest wait. A
// list the engine cannot give lists no agent, so nothing rides and the note
// waits whole. An agent the reminder names no
// longer waits for the idle line, on this message or a later one (ruled
// 2026-11-15); an idle notice taken out after this is named as usual.
const takeNote = async ($: EngineInterface, except: readonly string[] = []): Promise<Riding> => {
  const entries = await read($, note)
  if (entries.length === 0) {
    return NOTHING_RIDES
  }
  const agents = await listAgents($)
  const { idle, nudgedIds, pending } = await read($, reports)
  const mutedIds = await read($, muted)
  const isDue = (entry: NoteEntry): boolean => {
    const agent = agents.find(candidate => candidate.id === entry.id)
    return (
      agent !== undefined &&
      nudgedIds.includes(entry.id) &&
      !mutedIds.includes(entry.id) &&
      !except.includes(entry.name) &&
      isToName(agent, idle)
    )
  }
  const due = entries.filter(isDue)
  if (due.length === 0) {
    return NOTHING_RIDES
  }
  await update($, note, current => current.filter(entry => !due.some(taken => taken.id === entry.id)))
  const named = pending.filter(name => due.some(entry => entry.name === name))
  if (named.length > 0) {
    await update($, reports, state => ({
      ...state,
      pending: state.pending.filter(name => !named.includes(name)),
    }))
  }
  return { entries: due, pending: named }
}

// A message that did not go in told the model nothing: its entries, and the
// names taken with them, wait for the next one.
const putBackNote = async ($: EngineInterface, taken: Riding): Promise<void> => {
  await putBackPending($, taken.pending)
  if (taken.entries.length === 0) {
    return
  }
  await update($, note, current => [
    ...taken.entries,
    ...current.filter(entry => !taken.entries.some(other => other.id === entry.id)),
  ])
}

// A mute ends once its agent is stopped: listed as `killed`, or gone from the
// list. So an agent later resumed under the same id ("a message may yet
// resume one, under the same id", AgentStatus) is not muted. Run with a list
// the engine gave: an empty one from a failed call would end every mute.
const dropStoppedMutes = async ($: EngineInterface, agents: readonly AgentInfo[]): Promise<MutedAgents> => {
  const live = new Set(agents.filter(agent => agent.status !== 'killed').map(agent => agent.id))
  const before = await read($, muted)
  if (before.every(id => live.has(id))) {
    return before
  }
  return update($, muted, ids => ids.filter(id => live.has(id)))
}

// Never stops an agent, and submits no prompt: the agents it names wait in
// the note for the next message (ruled 2026-11-15), and the model's TaskStop
// asks permission as usual. A list the engine could not give changes
// nothing, as an empty one would drop every idle name and note entry.
const recordTurnEnd = async ($: EngineInterface, isAnswered: boolean): Promise<void> => {
  let agents: readonly AgentInfo[]
  try {
    agents = await $.agent.list()
  } catch (error) {
    $.ui.log(`quiet-agents: could not list agents, so no one is named: ${describeError(error)}`, {
      to: 'debug',
    })
    return
  }

  const mutedIds = await dropStoppedMutes($, agents)
  let step = turnEndStep(await read($, reports), agents, isAnswered, mutedIds)
  if (step.isChanged) {
    await update($, reports, state => {
      step = turnEndStep(state, agents, isAnswered, mutedIds)
      return step.state
    })
  }

  const { nudgedIds } = step.state
  const before = await read($, note)
  if (!sameIds(noteAtTurnEnd(before, agents, nudgedIds, step.named), before)) {
    await update($, note, entries => noteAtTurnEnd(entries, agents, nudgedIds, step.named))
  }
}

// A delivery to the main conversation, judged: the text to queue, or taken
// out. A teammate's message to the main conversation (verified, or
// unverified from a listed agent: isTeammate) records that it reported (an
// in-process teammate's report arrives here; an agent's report is also
// marked at its send, below); its idle notice is consumed while that report
// stands, and framed with the prefix otherwise. A mute changes none of this
// (ruled 2026-11-15): it silences only the naming of the agent, and an agent
// that answers by ending its turn has its answer only in the idle notice's
// `result`. It changes only the prefix, which for a muted agent does not
// prompt a stop. Any other delivery is queued as it came. `stops` names the
// agent whose stop the queued text already prompts, if any.
type Judged = { result: SessionReceiveResult; stops: readonly string[] }

const judgeDelivery = async ($: EngineInterface, e: Frozen<SessionReceiveInput>): Promise<Judged> => {
  const origin = e.origin
  if (
    origin.kind !== 'peer' ||
    !('teammate' in origin) ||
    !(await isTeammate($, origin.teammate, origin.isVerified))
  ) {
    return { result: { text: e.text }, stops: [] }
  }

  const teammate = origin.teammate
  if (!isIdleNotice(e.text)) {
    if (!isReported(await read($, reports), teammate)) {
      await update($, reports, state => markReported(state, teammate))
    }

    return { result: { text: e.text }, stops: [] }
  }

  const prefixed = async (): Promise<Judged> =>
    (await isMuted($, teammate))
      ? { result: { text: MUTED_NOTICE_PREFIX + e.text }, stops: [] }
      : { result: { text: NOTICE_PREFIX + e.text }, stops: [teammate] }
  if (!isReported(await read($, reports), teammate)) {
    return prefixed()
  }

  // Asked again inside the write: a send to the teammate may land between.
  const after = await update($, reports, state =>
    isReported(state, teammate) ? markIdle(state, teammate) : state,
  )
  if (!isReported(after, teammate)) {
    return prefixed()
  }

  await showStatus($, after)
  return {
    result: { consumed: `quiet-agents: idle notice from ${teammate}; its report was already received` },
    stops: [],
  }
}

export const register: Register = on => {
  // One hook: the engine refuses a second prompt.submit hook without a
  // matcher. Part 1, secondary path: mute a repeated notice, frame a new one.
  // And name, once, the teammates whose idle notices were consumed since the
  // last prompt.submit, and carry the waiting reminder (Part 3), beside the
  // next prompt of any origin that enters.
  on('prompt.submit', async ($, e, next) => {
    const notice = isAgentNotice(e)
      ? { key: agentKeyOf(e.origin.kind, e.text), body: hash(normalise(e.text)) }
      : undefined
    if (notice !== undefined && (await read($, lastNotice))[notice.key] === notice.body) {
      return { drop: `quiet-agents: repeat notice from ${notice.key}, muted` }
    }

    // The reminder first, so the names it takes are not on the idle line.
    const riding = await takeNote($)
    const taken = await takePending($)
    // An agent now `waiting` did not go idle, and a muted one is not named.
    const agents = taken.length === 0 ? [] : await listAgents($)
    const skipped = new Set([...waitingNames(agents), ...mutedNames(agents, await read($, muted))])
    const idle = taken.filter(name => !skipped.has(name))
    const added = [
      ...(notice === undefined ? [] : [NOTICE_CONTEXT]),
      ...(idle.length === 0 ? [] : [idleContext(idle)]),
      ...(riding.entries.length === 0 ? [] : [reminderText(riding.entries)]),
    ]
    const result = await next(added.length === 0 ? e : { ...e, context: [...(e.context ?? []), ...added] })
    if (result.drop !== undefined) {
      // Not entered: the names and the reminder wait for the next prompt,
      // and a notice dropped beneath is not a repeat.
      await putBackPending($, taken)
      await putBackNote($, riding)
      return result
    }

    if (notice !== undefined) {
      await update($, lastNotice, hashes => ({ ...hashes, [notice.key]: notice.body }))
    }

    return result
  })

  // Part 1, primary path, and Part 3's reminder on a delivery: a delivery to
  // the main conversation is judged (judgeDelivery), and one from an agent
  // that is queued carries the waiting reminder as its leading line, less any
  // agent whose stop the delivery's own prefix already prompts. Origin
  // `peer` is "another session's or agent's model" (SessionReceiveOrigin);
  // any other delivery, the person's own words from a Remote Control client
  // or Slack among them, is queued as it came, and the reminder waits. A
  // delivery to a teammate's own loop (`e.agentId` set,
  // agent-notice-log.jsonl line 3) is left alone.
  on('session.receive', async ($, e, next) => {
    if (e.agentId !== undefined) {
      return next(e)
    }

    const { result: judged, stops } = await judgeDelivery($, e)
    if (judged.consumed !== undefined) {
      return judged
    }

    const riding = e.origin.kind === 'peer' ? await takeNote($, stops) : NOTHING_RIDES
    const result = await next({
      ...e,
      text: riding.entries.length === 0 ? judged.text : `${reminderText(riding.entries)}\n${judged.text}`,
    })
    if (result.consumed !== undefined) {
      await putBackNote($, riding)
    }

    return result
  })

  // The main conversation's message to a teammate clears its report and takes
  // it off the idle list. session.send is receive's dual, `to` a string and
  // `agentId` absent for the main conversation, but its doc names "a
  // plain-text message"; SendMessage also carries a plan approval or a
  // shutdown request, which only tool.call is known to see. Both run;
  // the second finds nothing left to clear. An agent's delivered message to
  // the main conversation marks its report (markSender).
  on('session.send', async ($, e, next) => {
    if (e.agentId === undefined) {
      await forget($, e.to)
      return next(e)
    }

    const result = await next(e)
    if (result.isDelivered && isToMain(e.to)) {
      await markSender($, e.agentId)
    }

    return result
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

  // Part 3: the reminder about idle or finished agents, and visibility.
  // Nothing here stops an agent unasked, or starts a turn: the agents a turn
  // end names wait for the next message (ruled 2026-11-15).
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId !== undefined) {
      return result
    }

    // Ruled 2026-10-24: only a turn the model answered names agents; one the
    // person interrupted, a refusal or an API error ended names no one. Any
    // end still drops a stopped teammate's name from the status line, and
    // sets it.
    await recordTurnEnd($, e.reason === 'answer')
    await showStatus($, await read($, reports))
    return result
  })

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'tidy',
      description: 'Stop idle, completed and failed agents (each stop asks permission as usual)',
    })
    // Immediate, so an agent can be muted while a turn is still running.
    await $.command.register({
      name: 'quiet-agents',
      description: 'Mute or unmute an agent you keep: mute <agent>, unmute <agent>, or mute to list',
      argumentHint: 'mute|unmute [agent]',
      immediate: true,
    })

    return next(e)
  })

  on('command.run', { command: 'tidy' }, async $ => ({ text: await tidy($) }))
  on('command.run', { command: 'quiet-agents' }, async ($, e) => ({ text: await quietAgentsCommand($, e.args) }))
}
