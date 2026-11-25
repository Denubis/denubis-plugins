import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type {
  AgentInfo,
  AgentSpawnResult,
  On,
  PromptComposeSection,
  PromptOrigin,
  RenderSurface,
  SessionAppendInput,
} from 'claude-code'

const PLUGIN = 'denubis-hook-question-zone'
const ASK = 'mcp__denubis-hook-question-zone__ask'
const WITHDRAW = 'mcp__denubis-hook-question-zone__withdraw'
const SURFACES = ['terminal', 'desktop'] as const

type Entry = { context: string; question: string }

// An entry as an earlier load of the plugin kept it in the session's state:
// a queued one may still be waiting for its search for an earlier answer.
type Stored = Entry & { isSearching?: boolean }

const RELEASE: Entry = {
  context:
    'The new version of the plugin is built and every test passes. Releasing it today gets the fix to people before the weekend; waiting a day leaves time for one more check by hand.',
  question: 'Should the new version go out today?',
}

const NAMING: Entry = {
  context: 'The new plugin needs the name people will type to install it. The draft name is question-zone.',
  question: 'Is question-zone the name you want?',
}

// How one run ends: the agent's answer, its run ending some other way, the
// engine refusing to start it, or the spawn call itself failing.
type CheckEnd = { answer: string } | { ended: 'error' | 'aborted' } | { refused: string } | { fails: true }

// A run the plugin started: the clarity reader's, or a search for an earlier
// answer, told apart by whether the agent type it registered can run commands.
type Spawned = { prompt: string; subagentType: string; isSearch: boolean }

// The reader passes the entry, and the search finds no earlier answer.
const ALL_CLEAR = ({ isSearch }: Spawned): CheckEnd => ({ answer: isSearch ? 'NOT_ANSWERED' : 'CLEAR' })

// The reader passes every entry; `search` says what each search finds.
const searchFinds =
  (search: (prompt: string) => string) =>
  (spawn: Spawned): CheckEnd => ({ answer: spawn.isSearch ? search(spawn.prompt) : 'CLEAR' })

// Every search finds nothing; `read` says what the reader replies.
const readerSays =
  (read: (prompt: string) => string) =>
  (spawn: Spawned): CheckEnd => ({ answer: spawn.isSearch ? 'NOT_ANSWERED' : read(spawn.prompt) })

// The engine's refusal of a spawn while the session runs as many subagents as
// it allows, in the words of Claude Code 2.1.312 and 2.1.318; on 2026-11-08 it
// refused two of six checks so, with one other subagent running.
const atSubagentLimit = (cap: number): string =>
  `Concurrent subagent limit reached. You can run ${cap} subagents at once. Do not retry. If the user wants more concurrent subagents, ask them to increase CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS.`

// How many subagents the session runs at once, how many besides the checkers
// run throughout, and whether a checker's slot is given back before or after
// its run's end reaches the plugins.
type Slots = { cap: number; others: number; freed: 'before the end' | 'after the end' }

type EngineOptions = {
  checkEnds?: (spawn: Spawned) => CheckEnd
  draft?: string
  // Hold each run until the test ends it, with `endNextCheck` for the
  // reader's and `endNextSearch` for a search's.
  isHolding?: boolean
  // End the oldest held search while the plugin reads, or fills, the prompt
  // box, and let what follows it run before the box answers.
  endSearchDuring?: 'prompt.read' | 'prompt.fill'
  // The queue the session's state holds as the plugin loads: what an earlier
  // load of this version kept there, read through a reload.
  stored?: { checking: readonly Entry[]; waiting: readonly Stored[]; taken: readonly Entry[] }
  // Refuse a spawn past this many running subagents, as the engine does.
  slots?: Slots
  // The transcript file's path, as the engine reports it at the session's
  // start; absent, the session start reports none.
  transcript?: string
}

const INTRO: PromptComposeSection = { id: 'intro', text: 'engine prompt', scope: 'shared' }

// How a subagent's final report reaches the main conversation: a hidden
// prompt from a peer, opening with the agent's id (agent-notice-log.jsonl,
// 2026-11-08: every hand-back arrived at prompt.submit so).
const handBack = (agentId: string, report: string): string =>
  `<agent-message from="${agentId}">\n[Subagent hand-back] The text below is the final report of a subagent this session delegated to. The report follows:\n  ${report}\n</agent-message>`

// A host command run the stand-in answers: `grep -n -F -e <pattern> <file>`
// over the transcript it keeps in memory, as the host's grep would.
const grepOver = (lines: readonly string[], argv: readonly string[]) => {
  const pattern = argv[argv.indexOf('-e') + 1]
  const isGrep = argv[0] === 'grep' && argv.includes('-n') && argv.includes('-F') && pattern !== undefined
  if (!isGrep) {
    return { exitCode: 2, stdout: '', stderr: `not a command this host has: ${argv.join(' ')}` }
  }
  const found = lines.flatMap((line, i) => (line.includes(pattern) ? [`${i + 1}:${line}`] : []))
  return { exitCode: found.length === 0 ? 1 : 0, stdout: found.map(line => `${line}\n`).join(''), stderr: '' }
}

// Stands for the engine beneath the plugin. It starts the session, registers
// the plugin's tools and agent types, starts each agent the plugin asks for
// and ends its run as `checkEnds` says (after the spawn has answered, as a
// real run ends after it started), keeps a prompt box, lets every prompt in,
// records the plugin's own prompts, and composes a system prompt of one
// section. With `slots`, it refuses a spawn while the session runs its limit
// of subagents; `spawned` holds only the spawns it let past that limit. An
// agent that answers hands its report back to the main conversation, as a
// session in auto mode does; `delivered` holds every prompt that reached the
// model other than the person's own. It keeps the transcript file in memory
// (`lines`) and answers `grep` over it, and records the rows the plugin
// appends (`notes`).
const engine = async (
  $: Engine,
  on: On,
  {
    checkEnds = ALL_CLEAR,
    draft = '',
    isHolding = false,
    endSearchDuring,
    stored,
    slots,
    transcript,
  }: EngineOptions = {},
) => {
  const agents: { agent: string; model: string | undefined; tools: readonly string[] | undefined }[] = []
  const spawned: Spawned[] = []
  const toasts: string[] = []
  const messages: { text: string; origin: PromptOrigin }[] = []
  const delivered: { text: string; origin: PromptOrigin }[] = []
  const listed: AgentInfo[] = [
    { id: 'a-worker', description: 'Unrelated work', type: 'general-purpose', status: 'running' },
  ]
  const lines: string[] = []
  const held: { isSearch: boolean; endRun: () => Promise<unknown> }[] = []
  const box = { text: draft, cursor: draft.length }
  const clock = mock.clock(on)
  const session = mock.session(on)
  let runningChecks = 0

  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.register', (_, e) => ({ value: { tool: `mcp__${PLUGIN}__${e.name}` } }))
  on('agent.register', (_, e) => {
    agents.push({ agent: `${PLUGIN}:${e.name}`, model: e.model, tools: e.tools })
    return { value: { agent: `${PLUGIN}:${e.name}` } }
  })
  // Observed with the `claude plugin test` kit of Claude Code 2.1.318 (the
  // 2.1.312 build's code reads the same): a plugin's `$.agent.spawn` reaches
  // this hook as the Agent tool's input (`subagent_type`), and the plugin reads
  // the started agent's id from the Agent tool's record (`result.agentId`),
  // not from `agentId` as AgentSpawnResult documents it. The answer carries
  // both.
  on('agent.spawn', (_, e, next) => {
    if (slots !== undefined && slots.others + runningChecks >= slots.cap) {
      return { deny: atSubagentLimit(slots.cap) }
    }
    const subagentType = 'subagent_type' in e && typeof e.subagent_type === 'string' ? e.subagent_type : e.subagentType
    const isSearch = agents.find(agent => agent.agent === subagentType)?.tools?.includes('Bash') === true
    const spawn: Spawned = { prompt: e.prompt, subagentType, isSearch }
    spawned.push(spawn)
    const end = checkEnds(spawn)
    if ('refused' in end) {
      return { deny: end.refused }
    }
    if ('fails' in end) {
      // Nothing answers beneath, so the plugin's spawn call rejects.
      return next(e)
    }
    const agentId = `a-check-${spawned.length}`
    const turn = { agentId, durationMs: 1, turnId: `t-${agentId}` }
    const agent: AgentInfo = { id: agentId, description: e.description, type: subagentType, status: 'running', spawnedBy: PLUGIN }
    listed.push(agent)
    runningChecks += 1
    const freeSlot = () => {
      runningChecks -= 1
    }
    const endRun = async () => {
      if (slots?.freed === 'before the end') {
        freeSlot()
      }
      await ('answer' in end
        ? $.turn.complete({ ...turn, answer: end.answer, reason: 'answer', isAborted: false })
        : $.turn.complete({ ...turn, answer: '', reason: end.ended, isAborted: end.ended === 'aborted' }))
      listed.splice(listed.indexOf(agent), 1, { ...agent, status: 'completed' })
      if (slots?.freed !== 'before the end') {
        freeSlot()
      }
      if ('answer' in end) {
        await $.prompt.submit({ text: handBack(agentId, end.answer), wait: false, origin: { kind: 'peer' }, isMeta: true })
      }
    }
    if (isHolding) {
      held.push({ isSearch, endRun })
    } else {
      void Promise.resolve().then(endRun)
    }
    const started: AgentSpawnResult & { result: { agentId: string } } = {
      model: 'claude-sonnet-5-5',
      agentId,
      result: { agentId },
    }
    return started
  })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.log', () => ({ value: undefined }))
  // When a held search ends inside a box call; a test may change it between
  // takes.
  const during = { endSearch: endSearchDuring }
  const endSearchNow = async (call: 'prompt.read' | 'prompt.fill'): Promise<void> => {
    const at = during.endSearch === call ? held.findIndex(run => run.isSearch) : -1
    if (at >= 0) {
      const [run] = held.splice(at, 1)
      await run?.endRun()
      await clock.settle()
    }
  }
  on('prompt.read', async () => {
    const value = { ...box }
    await endSearchNow('prompt.read')
    return { value }
  })
  // Whether the box refuses to be filled, as when another plugin holds it.
  const fill = { isRefused: false }
  on('prompt.fill', async (_, e) => {
    if (fill.isRefused) {
      await endSearchNow('prompt.fill')
      return { isFilled: false }
    }
    const kept = e.mode === 'replace' ? '' : box.text
    const at = e.mode === 'insert' ? box.cursor : kept.length
    box.text = kept.slice(0, at) + e.text + kept.slice(at)
    box.cursor = e.cursor ?? at + e.text.length
    await endSearchNow('prompt.fill')
    return { isFilled: true }
  })
  // The main conversation's turns: one starts, makes requests (`turn.step`,
  // each carrying the conversation so far), and ends. These raise them without
  // letting time pass; the test's own calls, below, settle after each.
  let turnCount = 0
  let running: { turnId: string; steps: number } | undefined
  let promptTurnsWaiting = 0
  const startTurn = async (): Promise<void> => {
    turnCount += 1
    running = { turnId: `t-main-${turnCount}`, steps: 0 }
    await $.turn.start({ text: '', turnId: running.turnId })
  }
  const makeRequest = async (): Promise<void> => {
    expect(running).toBeDefined()
    const turn = running ?? { turnId: 'none', steps: 0 }
    const stream = $.turn.step({ turnId: turn.turnId, index: turn.steps, model: 'claude-opus-5-5', messageCount: 1 })
    turn.steps += 1
    const pieces: unknown[] = []
    for await (const piece of stream) {
      pieces.push(piece)
    }
  }
  const endTurn = async (): Promise<void> => {
    const turnId = running?.turnId ?? 'none'
    running = undefined
    await $.turn.complete({ turnId, answer: '', reason: 'answer', isAborted: false, durationMs: 1 })
    if (promptTurnsWaiting > 0) {
      promptTurnsWaiting -= 1
      await promptTurn()
    }
  }
  // A plugin's prompt starts a turn of its own once the session is idle, and
  // that turn's first request carries it.
  const promptTurn = async (): Promise<void> => {
    await startTurn()
    await makeRequest()
    await endTurn()
  }
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.step', async function* (_, e) {
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: null }
  })
  on('prompt.submit', (_, e) => {
    if (e.origin.kind === 'plugin') {
      messages.push({ text: e.text, origin: e.origin })
      if (running === undefined) {
        void Promise.resolve().then(promptTurn)
      } else {
        promptTurnsWaiting += 1
      }
    }
    if (e.origin.kind !== 'composer') {
      delivered.push({ text: e.text, origin: e.origin })
    }
    return { text: e.text, context: e.context, origin: e.origin }
  })
  on('agent.list', () => ({ value: listed.map(agent => ({ ...agent })) }))
  on('classic.SessionStart', () => ({}))
  on('process.run', (_, e) => ({
    value: { ...grepOver(lines, e.argv), isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('prompt.compose', () => ({ sections: [INTRO] }))
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)

    return <Text>engine</Text>
  })

  if (stored !== undefined) {
    // Until the plugin's first write lands (a value never written reads at
    // version 0), its queue reads as `stored`, under the tag this version
    // keeps the queue under. A call on `$` is answered `{ value }`.
    on('state.get', { plugin: PLUGIN, key: 'queue' }, async (_, e, next) => {
      const kept = await next(e)
      return kept.value?.version === 0
        ? { value: { value: { shape: 'question-queue-2', value: stored }, version: 0 } }
        : kept
    })
  }
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  if (transcript !== undefined) {
    await $.classic.SessionStart({ source: 'startup', transcript_path: transcript })
  }
  // What the session's start set going runs as far as it can.
  await clock.settle()

  // The model calls ask; the background check then runs as far as it can.
  const ask = async (entry: Entry, agentId?: string) => {
    const result = await $.tool.call({ tool: ASK, ...entry, ...(agentId === undefined ? {} : { agentId }) })
    await clock.settle()
    return result
  }

  // The oldest held run of one kind ends, and what follows it settles.
  const endNext = async (isSearch: boolean): Promise<void> => {
    const at = held.findIndex(run => run.isSearch === isSearch)
    expect(at).toBeGreaterThanOrEqual(0)
    const [run] = held.splice(at, 1)
    await run?.endRun()
    await clock.settle()
  }
  const endNextCheck = (): Promise<void> => endNext(false)
  const endNextSearch = (): Promise<void> => endNext(true)

  // Time passes, and what comes due on the way runs.
  const pass = (ms: number): Promise<void> => clock.advance(ms)

  // The text of each row the plugin appended to the conversation.
  const notes = (): string[] =>
    session
      .appended()
      .filter(row => row.door === 'note')
      .map(row => row.message.content.map(block => (block.type === 'text' ? block.text : '')).join('\n'))

  // The model's own turn: it starts, makes a request, and ends.
  const turn = {
    start: async (): Promise<void> => {
      await startTurn()
      await clock.settle()
    },
    request: async (): Promise<void> => {
      await makeRequest()
      await clock.settle()
    },
    end: async (): Promise<void> => {
      await endTurn()
      await clock.settle()
    },
  }

  // The runs started for searches, and for clarity reads.
  const searches = (): Spawned[] => spawned.filter(spawn => spawn.isSearch)
  const reads = (): Spawned[] => spawned.filter(spawn => !spawn.isSearch)

  return {
    agents,
    spawned,
    searches,
    reads,
    toasts,
    messages,
    delivered,
    lines,
    box,
    fill,
    during,
    ask,
    endNextCheck,
    endNextSearch,
    pass,
    notes,
    turn,
  }
}

const withdraw = ($: Engine, question: string, agentId?: string) =>
  $.tool.call({ tool: WITHDRAW, question, ...(agentId === undefined ? {} : { agentId }) })

const BAND = {
  plugin: PLUGIN,
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

// What the band above the prompt shows on one surface: the engine's own
// drawing, or the plugin's counts as the person reads them in its text (the
// number that says how many wait, and the number that says how many are being
// checked, in whichever order), and the hotkey of its one button.
type BandView = { isEngine: boolean; waiting: number | undefined; checking: number | undefined; hotkey: unknown }

const countBefore = (text: string, word: RegExp): number | undefined => {
  const found = new RegExp(`(\\d+)\\D*${word.source}`, 'i').exec(text)
  return found?.[1] === undefined ? undefined : Number(found[1])
}

const bandOn = async ($: Engine, surface: RenderSurface & (typeof SURFACES)[number]): Promise<BandView> => {
  const ui = await $.ui.mount({ ...BAND, surface })
  const texts = (await ui.findAll({ type: 'Text' })).map(found => found.text)
  const button = await ui.find({ type: 'Button' })
  await ui.unmount()
  const shown = texts.join(' ')

  return {
    isEngine: texts.length === 1 && texts[0] === 'engine' && button === undefined,
    waiting: countBefore(shown, /wait/),
    checking: countBefore(shown, /check/),
    hotkey: button?.props.hotkey,
  }
}

const band = async ($: Engine): Promise<BandView[]> => {
  const views: BandView[] = []
  for (const surface of SURFACES) {
    views.push(await bandOn($, surface))
  }
  return views
}

const ENGINE_BAND: BandView = { isEngine: true, waiting: undefined, checking: undefined, hotkey: undefined }

// What the band shows besides its counts and the engine's own drawing: the
// warning on the head question.
const bandWarnings = async ($: Engine): Promise<string[]> => {
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  const texts = (await ui.findAll({ type: 'Text' })).map(found => found.text)
  await ui.unmount()
  return texts.filter(
    text => text !== 'engine' && countBefore(text, /wait/) === undefined && countBefore(text, /check/) === undefined,
  )
}

// A search for an earlier answer that does not finish cleanly, and the words
// its warning should carry where the cause gives any.
const SEARCH_FAILURES: { why: string; end: CheckEnd; shows?: string }[] = [
  {
    why: 'its coverage was partial',
    end: { answer: 'HISTORY_WARNING: History coverage is partial: six files were not searched.' },
    shows: 'six files were not searched',
  },
  {
    why: 'its lookup failed',
    end: { answer: 'HISTORY_WARNING: History lookup failed: the index could not refresh.' },
    shows: 'the index could not refresh',
  },
  { why: 'the engine refused to start it', end: { refused: 'past a host limit' }, shows: 'past a host limit' },
  { why: 'its run ended in an error', end: { ended: 'error' } },
  { why: 'its reply could not be read', end: { answer: 'The person has probably not answered this.' } },
]

for (const { why, end, shows } of SEARCH_FAILURES) {
  test(`a search that cannot finish leaves the question in the queue with a visible warning (${why})`, async ($, on) => {
    const zone = await engine($, on, { checkEnds: spawn => (spawn.isSearch ? end : { answer: 'CLEAR' }) })
    await zone.ask(RELEASE)

    expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
    const warnings = await bandWarnings($)
    expect(warnings).toHaveLength(1)
    if (shows !== undefined) {
      expect(warnings[0]).toContain(shows)
    }
    await take($)
    expect(zone.box.text).toContain(warnings[0] ?? 'no warning')
    expect(zone.box.text).toContain(RELEASE.question)
    expect(zone.notes()).toEqual([])
  })
}

const waitingBand = (waiting: number, checking?: number): BandView => ({ isEngine: false, waiting, checking, hotkey: '1' })

// Questions being checked and none waiting: the count, and nothing to take.
const checkingBand = (checking: number): BandView => ({ isEngine: false, waiting: undefined, checking, hotkey: undefined })

// The person presses the band's button on the terminal.
const take = async ($: Engine): Promise<void> => {
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  const button = await ui.find({ type: 'Button' })
  expect(button?.key).toEqual(expect.any(String))
  await ui.press({ key: button?.key ?? '' })
  await ui.unmount()
}

// The person sends what the box holds, and the box empties.
const send = async ($: Engine, box: { text: string; cursor: number }, typed: string) => {
  const text = box.text + typed
  box.text = ''
  box.cursor = 0
  return $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
}

const COMPOSE = {
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: ['terminal'],
  tools: [],
  outputStyle: null,
  traits: [],
} as const

const pluginSections = async ($: Engine, traits: readonly ('teammate' | 'print')[] = []) => {
  const { sections } = await $.prompt.compose({ ...COMPOSE, traits })
  expect(sections[0]).toEqual(INTRO)
  return sections.slice(1)
}

// Which of `entries` the plugin's sections of the system prompt name.
const listed = (sections: readonly PromptComposeSection[], entries: readonly Entry[]): string[] =>
  entries
    .filter(entry => sections.some(section => section.text.includes(entry.question)))
    .map(entry => entry.question)

const FROM_PLUGIN = { kind: 'plugin', name: PLUGIN } as const

// Which of `texts` carry `words`.
const saying = (texts: readonly string[], words: string): string[] => texts.filter(text => text.includes(words))

test('ask returns at once; the entry is listed while it is checked and joins the queue when the check passes', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })

  const result = await zone.ask(RELEASE)

  expect(result.deny).toBeUndefined()
  expect(await band($)).toEqual([checkingBand(1), checkingBand(1)])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([RELEASE.question])

  await zone.endNextCheck()
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(zone.messages).toEqual([])
})

test('taking and answering a question leave an entry that is being checked in place', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })
  await zone.ask(NAMING)
  await zone.endNextCheck()
  await zone.ask(RELEASE)

  await take($)
  await send($, zone.box, 'Yes.')
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question])

  await zone.endNextCheck()
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('asks join the end of the queue: the first asked is the first taken', async ($, on) => {
  const zone = await engine($, on)

  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])

  await take($)
  expect(zone.box.text).toContain(RELEASE.question)
  expect(zone.box.text).not.toContain(NAMING.question)
})

test('the clarity reader is a registered Sonnet agent with no tools, and the search one that can only read and search; an objection reaches the model once, as a hidden note, and starts no search', async ($, on) => {
  const objection = 'The entry says "the L5d split" without saying what that is. Rewrite it.'
  const zone = await engine($, on, { checkEnds: readerSays(() => objection) })

  await zone.ask(RELEASE)

  expect(zone.agents).toHaveLength(2)
  expect(zone.agents.map(agent => agent.model)).toEqual(['sonnet', 'sonnet'])
  const tools = zone.agents.map(agent => [...(agent.tools ?? ['every tool'])].sort().join(' '))
  expect(tools.sort()).toEqual(['', 'Bash Read'])
  const reader = zone.agents.find(agent => agent.tools?.length === 0)
  expect(zone.spawned).toHaveLength(1)
  expect(zone.spawned[0]?.subagentType).toBe(reader?.agent)
  expect(zone.spawned[0]?.prompt).toContain(RELEASE.context)
  expect(zone.spawned[0]?.prompt).toContain(RELEASE.question)
  expect(saying(zone.notes(), objection)).toHaveLength(1)
  expect(saying(zone.messages.map(message => message.text), objection)).toEqual([])
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])
})

test('a clear entry joins the queue as soon as its clarity read ends, while the search for an earlier answer still runs', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })
  await zone.ask(RELEASE)
  expect(await band($)).toEqual([checkingBand(1), checkingBand(1)])

  await zone.endNextCheck()

  expect(zone.searches()).toHaveLength(1)
  expect(zone.searches()[0]?.prompt).toContain(RELEASE.question)
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([RELEASE.question])

  // A search that finds nothing leaves the queued question as it is.
  await zone.endNextSearch()
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(await bandWarnings($)).toEqual([])
  expect(zone.notes()).toEqual([])
  expect(zone.messages).toEqual([])
})

test('a go-ahead the reader names joins the queue and starts no search', async ($, on) => {
  const zone = await engine($, on, {
    checkEnds: readerSays(prompt => (prompt.includes(SHIP.question) ? 'CLEAR GO-AHEAD' : 'CLEAR')),
  })

  await zone.ask(SHIP)
  await zone.ask(NAMING)

  expect(zone.reads()).toHaveLength(2)
  expect(zone.searches().map(spawn => spawn.prompt.includes(NAMING.question))).toEqual([true])
  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])
  expect(zone.notes()).toEqual([])
})

const FOUND =
  'ANSWERED: docs/decisions/2026-11-01-release-day.md:14: "Ship it today, the weekend fix matters more."'

test('a search that finds an answer the person already gave takes the waiting question out of the queue and gives the model their words and where', async ($, on) => {
  const zone = await engine($, on, {
    checkEnds: searchFinds(prompt => (prompt.includes(RELEASE.question) ? FOUND : 'NOT_ANSWERED')),
  })

  await zone.ask(RELEASE)
  await zone.ask(NAMING)

  const said = saying(zone.notes(), 'docs/decisions/2026-11-01-release-day.md:14')
  expect(said).toHaveLength(1)
  expect(said[0]).toContain(RELEASE.question)
  expect(said[0]).toContain('"Ship it today, the weekend fix matters more."')
  expect(zone.notes()).toHaveLength(1)
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
})

// What the person or the model does to a queued question while its search
// runs: each takes it out of the search's reach. `isListed` says whether the
// system prompt still lists it afterwards.
type Box = { text: string; cursor: number }

const BEFORE_THE_SEARCH_ENDS: { what: string; act: ($: Engine, box: Box) => Promise<void>; isListed: boolean }[] = [
  {
    what: 'the person took it into the prompt box',
    act: async $ => {
      await take($)
    },
    isListed: true,
  },
  {
    what: 'the person took it and sent something else, which put it back in the queue',
    act: async ($, box) => {
      await take($)
      clear(box)
      await send($, box, 'Something else first.')
    },
    isListed: true,
  },
  {
    what: 'the person answered it',
    act: async ($, box) => {
      await take($)
      await send($, box, 'Yes, today.')
    },
    isListed: false,
  },
  {
    what: 'the model withdrew it',
    act: async $ => {
      expect((await withdraw($, RELEASE.question)).deny).toBeUndefined()
    },
    isListed: false,
  },
]

for (const { what, act, isListed } of BEFORE_THE_SEARCH_ENDS) {
  test(`an earlier answer found after ${what} changes nothing and says nothing`, async ($, on) => {
    const zone = await engine($, on, { isHolding: true, checkEnds: searchFinds(() => FOUND) })
    await zone.ask(RELEASE)
    await zone.endNextCheck()
    await act($, zone.box)
    const before = await band($)

    await zone.endNextSearch()
    await zone.pass(10 * MINUTE)

    expect(zone.notes()).toEqual([])
    expect(zone.messages).toEqual([])
    expect(await band($)).toEqual(before)
    expect(listed(await pluginSections($), [RELEASE])).toEqual(isListed ? [RELEASE.question] : [])
  })
}

// A search that ends while the person presses the button: before the
// question is claimed for the box, the search takes it out and the box stays
// empty; once claimed, the box keeps it and the search says nothing. Never
// both: a question in the box the model was told had left the queue.
const DURING_TAKE = [
  { during: 'prompt.read', isInBox: false },
  { during: 'prompt.fill', isInBox: true },
] as const

for (const { during, isInBox } of DURING_TAKE) {
  test(`an earlier answer found while the person takes the question (${during}) either takes it out or leaves it in the box, never both`, async ($, on) => {
    const zone = await engine($, on, { isHolding: true, endSearchDuring: during, checkEnds: searchFinds(() => FOUND) })
    await zone.ask(RELEASE)
    await zone.endNextCheck()

    await take($)
    await zone.pass(MINUTE)

    expect(zone.box.text.includes(RELEASE.question)).toBe(isInBox)
    expect(zone.notes()).toHaveLength(isInBox ? 0 : 1)
    expect(listed(await pluginSections($), [RELEASE])).toEqual(isInBox ? [RELEASE.question] : [])
  })
}

test('a take the box refuses changes nothing: the question stays next, its search still acts on it, and a question taken before stays taken', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: searchFinds(() => FOUND) })
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.endNextCheck()
  await zone.endNextCheck()
  await take($)
  expect(zone.box.text).toContain(RELEASE.question)
  // RELEASE's search ends with it taken; NAMING's search starts.
  await zone.endNextSearch()

  // The person clears the box and presses for the next question, which the
  // box refuses.
  zone.box.text = ''
  zone.fill.isRefused = true
  await take($)
  expect(zone.box.text).toBe('')

  await zone.endNextSearch()
  expect(zone.notes()).toHaveLength(1)
  expect(saying(zone.notes(), NAMING.question)).toHaveLength(1)
  // RELEASE is still the taken one, so nothing waits.
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
})

// A search that ends while the box refuses a take acts on the question once
// it is back, as it would have had the person never pressed.
const ENDED_DURING_REFUSED_TAKE = [
  { what: 'finds an earlier answer', answer: FOUND, isListed: false, notes: 1, warnings: 0 },
  {
    what: 'cannot finish',
    answer: 'HISTORY_WARNING: History lookup failed: the index could not refresh.',
    isListed: true,
    notes: 0,
    warnings: 1,
  },
] as const

for (const { what, answer, isListed, notes, warnings } of ENDED_DURING_REFUSED_TAKE) {
  test(`a search that ${what} while the box refuses a take acts on the question once it is back`, async ($, on) => {
    const zone = await engine($, on, { isHolding: true, endSearchDuring: 'prompt.fill', checkEnds: searchFinds(() => answer) })
    await zone.ask(RELEASE)
    await zone.endNextCheck()

    zone.fill.isRefused = true
    await take($)
    await zone.pass(MINUTE)

    expect(zone.box.text).toBe('')
    expect(saying(zone.notes(), RELEASE.question)).toHaveLength(notes)
    expect(listed(await pluginSections($), [RELEASE])).toEqual(isListed ? [RELEASE.question] : [])
    expect(saying(await bandWarnings($), 'the index could not refresh')).toHaveLength(warnings)
  })
}

test('a search whose turn comes while the box refuses its question still runs once the question is back', async ($, on) => {
  const zone = await engine($, on, {
    isHolding: true,
    checkEnds: searchFinds(prompt => (prompt.includes(NAMING.question) ? FOUND : 'NOT_ANSWERED')),
  })
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.endNextCheck()
  await zone.endNextCheck()
  await take($)
  expect(zone.box.text).toContain(RELEASE.question)

  // NAMING's search waits behind RELEASE's, which ends while the box refuses
  // NAMING.
  zone.box.text = ''
  zone.fill.isRefused = true
  zone.during.endSearch = 'prompt.fill'
  await take($)
  await zone.pass(MINUTE)
  expect(zone.box.text).toBe('')
  expect(saying(zone.searches().map(spawn => spawn.prompt), NAMING.question)).toHaveLength(1)

  zone.during.endSearch = undefined
  await zone.endNextSearch()
  expect(saying(zone.notes(), NAMING.question)).toHaveLength(1)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
})

test('an earlier answer found while the session is idle reaches the model through one wake prompt', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: searchFinds(() => FOUND) })
  await zone.turn.start()
  await zone.ask(RELEASE)
  await zone.turn.request()
  await zone.turn.end()

  await zone.endNextCheck()
  expect(zone.messages).toEqual([])
  await zone.endNextSearch()
  await zone.pass(10 * MINUTE)

  expect(saying(zone.notes(), RELEASE.question)).toHaveLength(1)
  expect(zone.messages).toHaveLength(1)
  expect(saying(zone.messages.map(message => message.text), 'Ship it today')).toEqual([])
})

test('earlier answers found a minute apart while the session is idle send one wake prompt, once the last search ends', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: searchFinds(() => FOUND) })
  await zone.turn.start()
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.turn.request()
  await zone.turn.end()
  await zone.endNextCheck()
  await zone.endNextCheck()

  await zone.endNextSearch()
  await zone.pass(MINUTE)
  expect(zone.notes()).toHaveLength(1)
  expect(zone.messages).toEqual([])

  await zone.endNextSearch()
  await zone.pass(10 * MINUTE)
  expect(zone.notes()).toHaveLength(2)
  expect(zone.messages).toHaveLength(1)
})

test('a search that hangs holds the wake prompt for an earlier answer back five minutes at most', async ($, on) => {
  const zone = await engine($, on, {
    isHolding: true,
    checkEnds: searchFinds(prompt => (prompt.includes(RELEASE.question) ? FOUND : 'NOT_ANSWERED')),
  })
  await zone.turn.start()
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.turn.request()
  await zone.turn.end()
  await zone.endNextCheck()
  await zone.endNextCheck()

  // The first search finds an answer; the second starts and never ends.
  await zone.endNextSearch()
  expect(zone.searches()).toHaveLength(2)
  await zone.pass(4 * MINUTE)
  expect(zone.messages).toEqual([])
  await zone.pass(2 * MINUTE)

  expect(zone.messages).toHaveLength(1)
  expect(saying(zone.notes(), RELEASE.question)).toHaveLength(1)
})

test('a clarity check that cannot run reaches the model as one note each, read in the turn that asked, and nothing is queued', async ($, on) => {
  const cannotRead =
    'The check could not be made: the entry arrived with its question cut off. Ask it again in full.'
  const ends: CheckEnd[] = [
    { refused: 'past a host limit' },
    { ended: 'error' },
    { ended: 'aborted' },
    { answer: cannotRead },
    { fails: true },
  ]
  const zone = await engine($, on, { checkEnds: spawn => ends.shift() ?? ALL_CLEAR(spawn) })

  await zone.turn.start()
  for (let i = 0; i < 5; i += 1) {
    expect((await zone.ask(RELEASE)).deny).toBeUndefined()
  }
  await zone.turn.request()
  await zone.turn.end()
  await zone.pass(10 * MINUTE)

  const said = saying(zone.notes(), RELEASE.question)
  expect(said).toHaveLength(5)
  expect(said[0]).toContain('past a host limit')
  expect(said[3]).toContain(cannotRead)
  expect(zone.searches()).toEqual([])
  expect(zone.messages).toEqual([])
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])
})

const numbered = (n: number): Entry => ({
  context: `The person keeps a list of items to review, and item ${n} has not been looked at since it was added.`,
  question: `Should item ${n} stay on the list?`,
})

// A minute is past any wait the plugin could fairly leave between a slot
// coming free and the next check starting; half an hour is past any wait it
// could fairly give up after.
const MINUTE = 60_000

for (const freed of ['before the end', 'after the end'] as const) {
  test(`questions asked while every subagent slot is taken wait, each is read in the order asked once a slot comes free, and no search takes a slot a clarity read is waiting for (slot given back ${freed} of the run)`, async ($, on) => {
    const asked = [1, 2, 3, 4, 5, 6, 7].map(numbered)
    const questions = (entries: readonly Entry[]): string[] => entries.map(entry => entry.question)
    const zone = await engine($, on, { isHolding: true, slots: { cap: 5, others: 1, freed } })
    const which = (spawns: readonly Spawned[]): string[] =>
      spawns.map(spawn => asked.find(entry => spawn.prompt.includes(entry.question))?.question ?? spawn.prompt)
    const read = (): string[] => which(zone.reads())
    const searched = (): string[] => which(zone.searches())

    for (const entry of asked.slice(0, 6)) {
      expect((await zone.ask(entry)).deny).toBeUndefined()
    }

    expect(zone.messages).toEqual([])
    expect(read()).toEqual(questions(asked.slice(0, 4)))
    expect(listed(await pluginSections($), asked)).toEqual(questions(asked.slice(0, 6)))
    expect(await band($)).toEqual([checkingBand(6), checkingBand(6)])

    await zone.pass(30 * MINUTE)
    expect(zone.messages).toEqual([])
    expect(read()).toEqual(questions(asked.slice(0, 4)))

    // A slot comes free, and a seventh question is asked straight away: the
    // fifth, asked earlier, takes the slot, and the first, now queued, waits
    // for its search.
    await zone.endNextCheck()
    expect((await zone.ask(numbered(7))).deny).toBeUndefined()
    await zone.pass(MINUTE)
    expect(read()).toEqual(questions(asked.slice(0, 5)))
    expect(searched()).toEqual([])
    expect(await band($)).toEqual([waitingBand(1, 6), waitingBand(1, 6)])

    await zone.endNextCheck()
    await zone.pass(MINUTE)
    expect(read()).toEqual(questions(asked.slice(0, 6)))

    await zone.endNextCheck()
    await zone.pass(MINUTE)
    expect(read()).toEqual(questions(asked))
    expect(searched()).toEqual([])

    // With no read left waiting, the searches run one at a time, in the order
    // their questions joined the queue; here the reads end in the order asked.
    for (let i = 0; i < 4; i += 1) {
      await zone.endNextCheck()
      await zone.pass(MINUTE)
    }
    expect(searched()).toEqual(questions(asked.slice(0, 1)))
    for (let i = 1; i < 7; i += 1) {
      await zone.endNextSearch()
      await zone.pass(MINUTE)
      expect(searched()).toEqual(questions(asked.slice(0, i + 1)))
    }
    expect(zone.messages).toEqual([])
    expect(await band($)).toEqual([waitingBand(7), waitingBand(7)])
  })
}

test('at most one search runs at a time, so a question asked while earlier ones wait for their searches is read at once', async ($, on) => {
  const asked = [1, 2, 3, 4, 5].map(numbered)
  const late = numbered(6)
  const zone = await engine($, on, { isHolding: true, slots: { cap: 5, others: 0, freed: 'before the end' } })
  const which = (spawns: readonly Spawned[]): string[] =>
    spawns.map(spawn => [...asked, late].find(entry => spawn.prompt.includes(entry.question))?.question ?? spawn.prompt)

  for (const entry of asked) {
    expect((await zone.ask(entry)).deny).toBeUndefined()
  }
  for (let i = 0; i < asked.length; i += 1) {
    await zone.endNextCheck()
    await zone.pass(MINUTE)
  }
  expect(which(zone.searches())).toEqual([asked[0]?.question])

  await zone.ask(late)
  await zone.pass(MINUTE)
  expect(which(zone.reads())).toEqual([...asked, late].map(entry => entry.question))

  for (let i = 1; i < asked.length; i += 1) {
    await zone.endNextSearch()
    await zone.pass(MINUTE)
  }
  expect(which(zone.searches())).toEqual(asked.map(entry => entry.question))
})

test('an ask from a subagent is refused before any check', async ($, on) => {
  const zone = await engine($, on)

  const result = await zone.ask(RELEASE, 'a-helper')

  expect(result.deny).toEqual(expect.any(String))
  expect(zone.spawned).toEqual([])
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
})

test('an ask whose context or question is empty is refused before any check', async ($, on) => {
  const zone = await engine($, on)

  const noContext = await zone.ask({ ...RELEASE, context: '  ' })
  const noQuestion = await zone.ask({ ...RELEASE, question: '' })

  expect(noContext.deny).toEqual(expect.any(String))
  expect(noQuestion.deny).toEqual(expect.any(String))
  expect(zone.spawned).toEqual([])
})

test('neither the reader nor the search is ever offered to the model', async ($, on) => {
  const zone = await engine($, on)
  expect(zone.agents).toHaveLength(2)

  const offered: boolean[] = []
  for (const { agent } of zone.agents) {
    const offer = await $.agent.offer({
      agent,
      description: 'checks a question',
      source: 'plugin',
      provider: { plugin: PLUGIN, tier: 'user' },
    })
    offered.push(offer.isOffered)
  }

  expect(offered).toEqual([false, false])
})

test('the band shows nothing while the queue is empty, then the count and a button on key 1', async ($, on) => {
  const zone = await engine($, on)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])

  await zone.ask(RELEASE)
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])

  await zone.ask(NAMING)
  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])
})

test('taking puts the head entry, quoted, into an empty prompt box with a blank line for the answer', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)

  await take($)

  expect(zone.box.text).toContain(RELEASE.context)
  expect(zone.box.text).toContain(RELEASE.question)
  expect(zone.box.text).toMatch(/\n\n$/)
  expect(zone.box.text.trimEnd().split('\n').every(line => line.startsWith('>'))).toBe(true)
  expect(zone.box.cursor).toBe(zone.box.text.length)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
})

test('taking never overwrites a draft: the box keeps it, a toast says why, and the question waits', async ($, on) => {
  const draft = 'half a thought'
  const zone = await engine($, on, { draft })
  await zone.ask(RELEASE)

  await take($)

  expect(zone.box.text).toBe(draft)
  expect(zone.toasts).toHaveLength(1)
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('no button the band offers removes a question except by taking it into the prompt box', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)

  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...BAND, surface })
    for (const { key } of await ui.findAll({ type: 'Button' })) {
      expect(key).toEqual(expect.any(String))
      if ((await ui.find({ type: 'Button', key })) !== undefined) {
        await ui.press({ key: key ?? '' })
      }
    }
    await ui.unmount()
  }

  // Each question is still in front of the person: in the box, or waiting.
  const left = [RELEASE, NAMING].filter(entry => !zone.box.text.includes(entry.question)).length
  const view = left === 0 ? ENGINE_BAND : waitingBand(left)
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question, NAMING.question])
  expect(await band($)).toEqual([view, view])
})

test('sending the taken question with an answer typed below it answers it: the entry leaves', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await take($)
  const quoted = zone.box.text

  const sent = await send($, zone.box, 'Yes, today.')

  expect(sent.text).toBe(`${quoted}Yes, today.`)
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
  await take($)
  expect(zone.box.text).toContain(NAMING.question)
})

test('sending without the taken question puts it back at the head of the queue', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await take($)

  zone.box.text = ''
  await send($, zone.box, 'Something else first.')

  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])
  await take($)
  expect(zone.box.text).toContain(RELEASE.question)
})

const SHIP: Entry = { context: 'The release notes are written and checked.', question: 'Should it go out today?' }

// The person clears the box by hand.
const clear = (box: { text: string; cursor: number }): void => {
  box.text = ''
  box.cursor = 0
}

test('taking a second question returns the first to the queue: sending the second, whose context quotes the first, leaves the first unanswered', async ($, on) => {
  const notes: Entry = {
    context:
      'Two questions are open about the release. One of them is:\nShould it go out today? That one is asked on its own; this one is about the notes.',
    question: 'Should the release notes name the person who found the bug?',
  }
  const zone = await engine($, on)
  await zone.ask(SHIP)
  await zone.ask(notes)
  await take($)
  clear(zone.box)
  await take($)
  expect(zone.box.text).toContain(notes.question)

  await send($, zone.box, 'No, leave the name out.')

  expect(listed(await pluginSections($), [SHIP, notes])).toEqual([SHIP.question])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('taking a question while another is taken and unsent puts that other back at the head of the queue', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.ask(SHIP)
  await take($)
  clear(zone.box)
  await take($)
  clear(zone.box)

  await take($)

  expect(zone.box.text).toContain(RELEASE.question)
  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])
})

test('trimming the context before sending still answers the taken question', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await take($)

  // The person deletes the context, keeping the quoted question.
  zone.box.text = `${zone.box.text
    .split('\n')
    .filter(line => line.includes(RELEASE.question))
    .join('\n')}\n\n`
  expect(zone.box.text).not.toContain(RELEASE.context)
  await send($, zone.box, 'Yes, today.')

  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('a prompt the person did not send leaves a taken question in the box, answered when they send it', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await take($)

  await $.prompt.submit({
    text: '<task-notification>a1 completed</task-notification>',
    wait: false,
    origin: { kind: 'task-notification' },
    isMeta: true,
  })
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])

  await send($, zone.box, 'Yes.')
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
})

test('withdraw removes an entry by its question; an unknown question or a subagent is refused', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  await zone.ask(NAMING)

  expect((await withdraw($, 'Is there no such question?')).deny).toEqual(expect.any(String))
  expect((await withdraw($, RELEASE.question, 'a-helper')).deny).toEqual(expect.any(String))
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question, NAMING.question])

  expect((await withdraw($, RELEASE.question)).deny).toBeUndefined()
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])

  // A taken entry is withdrawn the same way.
  await take($)
  expect(zone.box.text).toContain(NAMING.question)
  expect((await withdraw($, NAMING.question)).deny).toBeUndefined()
  expect(listed(await pluginSections($), [NAMING])).toEqual([])
})

test('an entry withdrawn while it is checked neither joins the queue nor comes back when its check ends', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })
  await zone.ask(RELEASE)

  expect((await withdraw($, RELEASE.question)).deny).toBeUndefined()
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])

  await zone.endNextCheck()
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
  expect(zone.messages).toEqual([])
})

test('entries a reload left being checked are checked again as the plugin loads, and only one that passes joins the queue', async ($, on) => {
  const objection = 'The entry says "the L5d split" without saying what that is. Rewrite it.'
  const zone = await engine($, on, {
    isHolding: true,
    stored: { checking: [RELEASE, NAMING], waiting: [], taken: [] },
    checkEnds: readerSays(prompt => (prompt.includes(NAMING.question) ? objection : 'CLEAR')),
  })

  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question, NAMING.question])
  expect(zone.reads()).toHaveLength(2)
  expect(await band($)).toEqual([checkingBand(2), checkingBand(2)])

  await zone.endNextCheck()
  await zone.endNextCheck()
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question])
  expect(saying(zone.notes(), objection)).toHaveLength(1)
})

test('a queued question whose search a reload cut off is searched again as the plugin loads, and one already searched is not', async ($, on) => {
  const zone = await engine($, on, {
    stored: { checking: [], waiting: [{ ...RELEASE, isSearching: true }, { ...NAMING, isSearching: false }], taken: [] },
    checkEnds: searchFinds(prompt => (prompt.includes(RELEASE.question) ? FOUND : 'NOT_ANSWERED')),
  })

  expect(zone.reads()).toEqual([])
  expect(zone.searches().map(spawn => spawn.prompt.includes(RELEASE.question))).toEqual([true])
  expect(saying(zone.notes(), 'Ship it today')).toHaveLength(1)
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('the system prompt ends with a session section that sends the model to the ask tool and lists every unanswered question, a taken one included', async ($, on) => {
  const zone = await engine($, on)
  const before = await pluginSections($)
  expect(before).toEqual([{ id: expect.any(String), text: expect.stringContaining(ASK), scope: 'session' }])

  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await take($)

  const after = await pluginSections($)
  expect(after).toHaveLength(1)
  expect(after[0]?.scope).toBe('session')
  expect(listed(after, [RELEASE, NAMING])).toEqual([RELEASE.question, NAMING.question])
})

test('a teammate’s render of the lead’s prompt gets no question-zone section', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)

  expect(await pluginSections($, ['teammate'])).toEqual([])
})

test('the band counts the questions being read beside those waiting, so work in progress never looks like an empty box; a question whose search runs counts as waiting', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })

  await zone.ask(NAMING)
  expect(await band($)).toEqual([checkingBand(1), checkingBand(1)])

  await zone.endNextCheck()
  await zone.ask(RELEASE)
  expect(await band($)).toEqual([waitingBand(1, 1), waitingBand(1, 1)])

  // One search runs and the other waits for it; both questions wait.
  await zone.endNextCheck()
  expect(zone.searches()).toHaveLength(1)
  expect(await band($)).toEqual([waitingBand(2), waitingBand(2)])
})

test('a checker’s own report never reaches the model: a clear read and a search that finds nothing send it nothing, and a refusal reaches it once, as the plugin’s note', async ($, on) => {
  const objection = 'The entry says "the L5d split" without saying what that is. Rewrite it.'
  const zone = await engine($, on, {
    checkEnds: readerSays(prompt => (prompt.includes(NAMING.question) ? objection : 'CLEAR')),
  })

  await zone.ask(RELEASE)
  expect(zone.searches()).toHaveLength(1)
  expect(zone.delivered).toEqual([])
  expect(zone.notes()).toEqual([])

  await zone.ask(NAMING)
  expect(saying(zone.notes(), objection)).toHaveLength(1)
  expect(saying(zone.delivered.map(prompt => prompt.text), objection)).toEqual([])
  expect(zone.delivered.every(prompt => prompt.origin.kind === FROM_PLUGIN.kind)).toBe(true)
})

test('another agent’s report still reaches the model', async ($, on) => {
  const zone = await engine($, on)
  await zone.ask(RELEASE)
  const report = handBack('a-worker', 'The change is made and its tests pass.')

  await $.prompt.submit({ text: report, wait: false, origin: { kind: 'peer' }, isMeta: true })

  expect(zone.delivered.map(prompt => prompt.text)).toContain(report)
})

const TRANSCRIPT = '/home/person/.claude/projects/-home-person-work/0b5c1f6e-4d2a-4c1e-9f3b-7a8d6e5c4b3a.jsonl'
const ANSWER_UUID = '0d4216b0-a6ff-4740-9c75-d5e7676ef085'
const ANSWER_AT = '2026-11-08T05:40:34.625Z'

// Records of other kinds, as many as come before the answer's.
const otherRecords = (count: number): string[] =>
  Array.from({ length: count }, (_, i) =>
    JSON.stringify({ type: 'progress', uuid: `other-${i}`, timestamp: '2026-11-08T05:00:00.000Z' }),
  )

// A later record that names the answer's as its parent.
const child = JSON.stringify({ parentUuid: ANSWER_UUID, type: 'assistant', uuid: 'reply-1', timestamp: ANSWER_AT })

// The two kinds of record the person's answer is kept as (observed in a
// session's transcript on 2026-11-08): typed at an idle prompt, a `user`
// record (line 8177 there); sent while the model worked, a `queued_command`
// attachment, with the message queue's records, which carry no uuid, around
// it (line 7350 there). `row` is the row the engine appends; `records`, what
// the file holds once it is written.
const RECORD_KINDS = [
  {
    kind: 'typed at an idle prompt',
    line: 8177,
    row: (sent: string): SessionAppendInput => ({
      message: { type: 'user', role: 'user', content: [{ type: 'text', text: sent }] },
      door: 'prompt',
      origin: { kind: 'composer' },
      uuid: ANSWER_UUID,
    }),
    records: (sent: string): string[] => [
      ...otherRecords(8176),
      JSON.stringify({ parentUuid: 'other-8175', promptId: 'p-1', type: 'user', message: { role: 'user', content: sent }, uuid: ANSWER_UUID, timestamp: ANSWER_AT }),
      child,
    ],
  },
  {
    kind: 'sent while the model was working',
    line: 7350,
    row: (sent: string): SessionAppendInput => ({
      message: {
        type: 'attachment',
        name: 'queued_command',
        role: 'user',
        content: [{ type: 'text', text: `<system-reminder>\nThe user sent a new message while you were working:\n${sent}\n</system-reminder>` }],
      },
      door: 'delivery',
      origin: { kind: 'composer' },
      uuid: ANSWER_UUID,
    }),
    records: (sent: string): string[] => [
      ...otherRecords(7348),
      JSON.stringify({ type: 'queue-operation', operation: 'enqueue', timestamp: ANSWER_AT, content: sent }),
      JSON.stringify({ parentUuid: 'other-7347', type: 'attachment', attachment: { type: 'queued_command', prompt: sent }, uuid: ANSWER_UUID, timestamp: ANSWER_AT }),
      JSON.stringify({ type: 'queue-operation', operation: 'remove', timestamp: ANSWER_AT }),
      child,
    ],
  },
] as const

// The person takes the queued question and sends it with an answer.
const answer = async ($: Engine, zone: Awaited<ReturnType<typeof engine>>): Promise<string> => {
  await take($)
  const sent = await send($, zone.box, 'Yes, today.')
  return sent.text ?? ''
}

for (const { kind, line, row, records } of RECORD_KINDS) {
  test(`an answer’s citation reaches the model, read from the transcript file once its record is written (${kind})`, async ($, on) => {
    const zone = await engine($, on, { transcript: TRANSCRIPT })
    await zone.ask(RELEASE)
    const sent = await answer($, zone)

    await $.session.append(row(sent))
    await zone.pass(0)
    expect(zone.notes()).toEqual([])

    zone.lines.push(...records(sent))
    await zone.pass(MINUTE)

    const notes = zone.notes()
    expect(notes).toHaveLength(1)
    expect(notes[0]).toContain(RELEASE.question)
    expect(notes[0]).toContain(TRANSCRIPT)
    expect(notes[0]).toContain(ANSWER_UUID)
    expect(notes[0]).toContain(ANSWER_AT)
    expect(notes[0]).toContain(`sed -n '${line}p' ${TRANSCRIPT}`)
  })
}

const UNDERIVABLE = [
  { why: 'its record never reaches the file', transcript: TRANSCRIPT },
  { why: 'the session never said where its transcript is', transcript: undefined },
] as const

for (const { why, transcript } of UNDERIVABLE) {
  test(`a citation the plugin cannot derive says so and gives no line (${why})`, async ($, on) => {
    const zone = await engine($, on, transcript === undefined ? {} : { transcript })
    await zone.ask(RELEASE)
    const sent = await answer($, zone)
    const [typed] = RECORD_KINDS

    await $.session.append(typed.row(sent))
    await zone.pass(10 * MINUTE)

    const notes = zone.notes()
    expect(notes).toHaveLength(1)
    expect(notes[0]).toContain(RELEASE.question)
    expect(notes[0]).not.toContain('sed -n')
  })
}

test('a prompt that answers no question gets no citation', async ($, on) => {
  const zone = await engine($, on, { transcript: TRANSCRIPT })
  await zone.ask(RELEASE)
  const sent = await send($, zone.box, 'Something else first.')
  const [typed] = RECORD_KINDS

  await $.session.append(typed.row(sent.text ?? ''))
  zone.lines.push(...typed.records(sent.text ?? ''))
  await zone.pass(MINUTE)

  expect(zone.notes()).toEqual([])
})

test('a question withdrawn while it waits for a subagent slot never starts a checker', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, slots: { cap: 2, others: 1, freed: 'after the end' } })
  await zone.ask(NAMING)
  await zone.ask(RELEASE)
  expect(zone.spawned).toHaveLength(1)

  expect((await withdraw($, RELEASE.question)).deny).toBeUndefined()
  await zone.endNextCheck()
  await zone.pass(MINUTE)

  expect(zone.spawned.filter(spawn => spawn.prompt.includes(RELEASE.question))).toEqual([])
  expect(zone.messages).toEqual([])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('a queued question withdrawn while its search waits for a subagent slot never starts that search', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, slots: { cap: 2, others: 1, freed: 'after the end' } })
  await zone.ask(NAMING)
  await zone.ask(RELEASE)

  // The one slot goes to the read waiting for it, and the search for the
  // question just queued waits.
  await zone.endNextCheck()
  await zone.pass(MINUTE)
  expect(zone.reads().map(spawn => spawn.prompt.includes(RELEASE.question))).toEqual([false, true])
  expect(zone.searches()).toEqual([])

  expect((await withdraw($, NAMING.question)).deny).toBeUndefined()
  await zone.endNextCheck()
  await zone.pass(MINUTE)

  expect(zone.searches().map(spawn => spawn.prompt.includes(RELEASE.question))).toEqual([true])
  expect(zone.messages).toEqual([])
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

const OBJECTION = 'The entry says "the L5d split" without saying what that is. Rewrite it.'

test('a refusal that settles while the turn runs, before its next request, adds no prompt', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: () => ({ answer: OBJECTION }) })

  await zone.turn.start()
  await zone.ask(NAMING)
  await zone.endNextCheck()
  await zone.turn.request()
  await zone.turn.end()
  await zone.pass(10 * MINUTE)

  expect(saying(zone.notes(), OBJECTION)).toHaveLength(1)
  expect(zone.messages).toEqual([])
})

test('a refusal that settles after the turn’s last request reaches the model through exactly one wake prompt', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: () => ({ answer: OBJECTION }) })

  await zone.turn.start()
  await zone.ask(NAMING)
  await zone.turn.request()
  await zone.endNextCheck()
  expect(zone.messages).toEqual([])
  await zone.turn.end()
  await zone.pass(10 * MINUTE)

  expect(saying(zone.notes(), OBJECTION)).toHaveLength(1)
  expect(zone.messages).toHaveLength(1)
  expect(saying(zone.messages.map(message => message.text), OBJECTION)).toEqual([])
})

test('refusals while the session is idle give one wake prompt, once the last running read and search end', async ($, on) => {
  const zone = await engine($, on, {
    isHolding: true,
    checkEnds: readerSays(prompt => (prompt.includes(SHIP.question) ? 'CLEAR' : OBJECTION)),
  })
  await zone.turn.start()
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.ask(SHIP)
  await zone.turn.request()
  await zone.turn.end()

  await zone.endNextCheck()
  await zone.endNextCheck()
  expect(zone.messages).toEqual([])
  await zone.endNextCheck()
  expect(zone.messages).toEqual([])
  await zone.endNextSearch()
  expect(zone.messages).toHaveLength(1)
  await zone.pass(10 * MINUTE)

  expect(zone.messages).toHaveLength(1)
  expect(saying(zone.messages.map(message => message.text), OBJECTION)).toEqual([])
  expect(saying(zone.notes(), RELEASE.question)).toHaveLength(1)
  expect(saying(zone.notes(), NAMING.question)).toHaveLength(1)
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
})

test('a check that hangs holds the wake prompt back five minutes at most', async ($, on) => {
  const zone = await engine($, on, { isHolding: true, checkEnds: () => ({ answer: OBJECTION }) })
  await zone.turn.start()
  await zone.ask(RELEASE)
  await zone.ask(NAMING)
  await zone.turn.request()
  await zone.turn.end()

  await zone.endNextCheck()
  await zone.pass(4 * MINUTE)
  expect(zone.messages).toEqual([])
  await zone.pass(2 * MINUTE)

  expect(zone.messages).toHaveLength(1)
  expect(saying(zone.notes(), RELEASE.question)).toHaveLength(1)
})
