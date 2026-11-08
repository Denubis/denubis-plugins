import { atom, read, update } from 'claude-code'
import type {
  EngineInterface,
  Frozen,
  HookFailure,
  PromptSubmitInput,
  Register,
  SessionAppendInput,
  TurnCompleteInput,
} from 'claude-code'

import type { QuestionZoneEntry, QuestionZoneQueue } from '../types'

// The unanswered questions. Change the tag if the layout changes: a value
// stored under another tag reads as the empty queue.
const NO_QUESTIONS: QuestionZoneQueue = { checking: [], waiting: [], taken: [] }
const queue = atom({ plugin: 'denubis-hook-question-zone', key: 'queue' } as const, NO_QUESTIONS, {
  shape: 'question-queue-2',
})

const ASK = 'mcp__denubis-hook-question-zone__ask'
const WITHDRAW = 'mcp__denubis-hook-question-zone__withdraw'
const CHECKER = 'denubis-hook-question-zone:checker'
const SECTION_ID = 'denubis-hook-question-zone:rule'

const ASK_DESCRIPTION = [
  "Puts one question for the person in a queue shown above their prompt. When they are ready, one key puts the question into their prompt box, and their answer arrives as their next message, quoting your question. Use this tool for every question to the person; never write a question to them in chat.",
  '',
  'The person will read the entry on its own, perhaps much later, without this conversation. Write it for someone who has not read the conversation:',
  '- context: what they need to know to answer, in plain full sentences, and what their answer will change.',
  '- question: exactly one question.',
  'Use no file names, ticket or record numbers, agent names, or labels coined in this conversation, unless you explain each in plain words.',
  '',
  "The call returns at once, and the entry is checked before it joins the queue: a reader who has not seen this conversation checks that it stands alone, and searches the project's decision records and the chat logs for an answer the person has already given. A clear entry joins the queue when its check ends. Otherwise a note from this plugin, which the person does not see as typed, gives the reason at your next request: what the reader could not understand (rewrite the entry and ask again), the person's existing answer with where and in what words (use it instead of asking), or why the check could not run (tell the person once what stopped it and what they can do, and do not ask that question again until they say the cause is fixed). Say nothing in chat about a question rewritten or dropped this way.",
].join('\n')

const WITHDRAW_DESCRIPTION =
  "Removes a question from the queue above the person's prompt when you no longer need its answer. Give the question exactly as you asked it; the system prompt lists the questions still waiting."

// The checker's system prompt. It sees the entry and nothing of the
// conversation the entry came from. Its reply reaches the model unchanged
// unless it is CLEAR, so each refusal says what the model should do.
const CHECKER_PROMPT = [
  'You check one entry before it is shown to a person. An assistant working with that person wrote it: a context and a question. The person will read the entry on its own, perhaps hours later, without the conversation it came from. You have not seen that conversation.',
  '',
  'Make two checks, in this order.',
  '',
  'First, does the entry stand alone? Read it as that person would, and decide whether they could understand what is asked and answer it from the entry alone. It fails when it:',
  '- uses a term, name, abbreviation or label it does not explain in plain words, such as a file name, a ticket or record number, an agent name, or a word coined in the conversation;',
  '- refers to something the entry does not give, such as "the earlier option" or "as discussed";',
  '- asks more than one question.',
  'If it fails, stop there: reply with what the reader could not understand, in one or two plain sentences that quote the words at fault, and ask for the entry to be rewritten.',
  '',
  'Second, has the person already answered it? Search for an answer in their own words:',
  "- in the project's decision records: `git rev-parse --path-format=absolute --git-common-dir` names the main checkout's git folder, whose parent is the main checkout; search its `docs/architecture/decisions/` and `docs/decisions/` with `rg`. A project with neither has no records to search;",
  '- in the chat logs. First bring their index up to date: if `cc-search-chats index --status --json` reports `index_state.freshness` other than `no_source_changes`, run `cc-search-chats index --json`. A warning that some files were left out, such as an unknown record shape, does not stop the check. Then search with `cc-search-chats search "<words>" --semantic --json`, or `--literal` for exact words. Each result\'s `identity.canonical_locator` is its `ccchat:v1:` locator, and `cc-search-chats context <locator> --json` shows the messages around it. Its JSON carries `schema_version` 5.',
  "Only the person's own words count: a message they typed themselves, or their words quoted in a decision record. A message written by an assistant, a plugin, a tool or an agent does not count. A paraphrase by an assistant or a record is not an answer, and neither is a remark that does not settle this question.",
  'If you find an answer, reply that the person has already answered this, say where (the record\'s path and line, or the `ccchat:v1:` locator), quote their words exactly, and say to use that answer instead of asking.',
  'If the index cannot be brought up to date or a search cannot run, reply that the check could not be made, with the command, its error, and a plain reason the person can act on: for example that the graphics card is busy and what to stop, or that the index reported `containment_unavailable` (it could not start in a process scope of its own).',
  '',
  'Apart from bringing the chat index up to date, use only commands that read and search; change nothing.',
  '',
  'If the entry stands alone and the searches ran and found no answer, reply with the one word CLEAR and nothing else.',
].join('\n')

const RULE = [
  'Questions for the person go through the question zone, a queue shown above their prompt.',
  `Every question for the person goes through the ${ASK} tool. Never write a question to the person in chat.`,
  'Never say you are waiting for an answer.',
  'Never mention, list or remind the person of questions waiting in the queue, except when they ask where things stand or return after a long absence.',
  `Then describe, in plain words and without referring to earlier messages, each decision still open and what its answer will change. The questions themselves stay in the queue, where the person takes the first one next; one not yet in it goes through ${ASK}.`,
  'An answer arrives as the person\'s message, quoting the question it answers.',
  'A question that comes back from its check arrives as a note from this plugin. If a reader could not follow it, rewrite it and ask again; if the person has already answered it, use that answer. Say nothing in chat about either.',
  'If its check could not be made, tell the person once, in plain words, what stopped the check and what they can do about it, and do not ask that question again until they say the cause is fixed.',
  `Questions in the project's open-questions file (.notes/project_open-questions.md at the main checkout's root) are put to the person through ${ASK}, in plain words, never in their ticket wording; the file stays the lasting list.`,
  'Ask only when the answer changes your next action, and name that decision plainly.',
  'Each entry holds exactly one specific, critical, pointed, clear question: never bundle questions into lists, options, or a compound sentence, and never end with a vague request for feedback.',
  'Ask only for answers that are missing or conflicting.',
  'Continue work already authorized while a question waits.',
].join(' ')

const listing = (heading: string, entries: readonly QuestionZoneEntry[]): string[] =>
  entries.length === 0 ? [] : ['', heading, ...entries.map(entry => `- ${entry.question}`)]

const ruleText = ({ checking, waiting, taken }: QuestionZoneQueue): string =>
  [
    RULE,
    ...listing(
      `Already in front of the person, waiting for their answer; do not ask these again (${WITHDRAW} removes one you no longer need):`,
      [...taken, ...waiting],
    ),
    ...listing(
      `Being checked before they join the queue; do not ask these again (${WITHDRAW} removes one you no longer need):`,
      checking,
    ),
  ].join('\n')

const quote = (text: string): string =>
  text
    .split('\n')
    .map(line => (line === '' ? '>' : `> ${line}`))
    .join('\n')

// What the prompt box takes: the context, then the question, quoted, then a
// blank line where the answer goes. The quoted question is also how the
// person's next prompt is matched to the entry, so text typed below it, or
// above it, leaves the match intact; an edit inside the quoted question does
// not, and the entry goes back to the queue.
const boxText = (entry: QuestionZoneEntry): string => `${quote(entry.context)}\n>\n${quote(entry.question)}\n\n`

const isAnsweredBy = (text: string) => (entry: QuestionZoneEntry): boolean => text.includes(quote(entry.question))

const sameEntry = (a: QuestionZoneEntry) => (b: QuestionZoneEntry): boolean =>
  a.context === b.context && a.question === b.question

const trimmed = (value: unknown): string => (typeof value === 'string' ? value.trim() : '')

// What a `.catch` handler reads on `next.error`: plain data, not an Error.
const failureOf = (failure: HookFailure | undefined): string =>
  failure === undefined
    ? 'no reason given'
    : failure.kind === 'timeout'
      ? 'it ran past its time limit'
      : (failure.message ?? 'it failed')

// Each check waits for its checker's run to end: the run's turn.complete
// carries the agentId $.agent.spawn answered. The run's end can reach this
// module before the spawn's answer does (observed under `claude plugin
// test`: the turn.complete hook ran first), so an agent's end that finds no
// waiter while a check is in flight is kept for the waiter that follows, and
// dropped once no check is in flight.
const waiters = new Map<string, (turn: Frozen<TurnCompleteInput>) => void>()
const endedEarly = new Map<string, Frozen<TurnCompleteInput>>()
let checksInFlight = 0

const runEnd = (agentId: string): Promise<Frozen<TurnCompleteInput>> =>
  new Promise(resolve => {
    const early = endedEarly.get(agentId)
    if (early !== undefined) {
      endedEarly.delete(agentId)
      resolve(early)
      return
    }
    waiters.set(agentId, resolve)
  })

type Verdict = { kind: 'clear' } | { kind: 'refused'; reply: string } | { kind: 'failed'; reason: string }

type Start = { kind: 'started'; agentId: string } | { kind: 'failed'; reason: string }

// The engine refuses a spawn while the session runs as many subagents as it
// allows (CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS), in these words in Claude
// Code 2.1.312 and 2.1.318: "Concurrent subagent limit reached. You can run 5
// subagents at once. Do not retry. ..." (observed 2026-11-08: two of six
// checks refused so). A check refused so waits for a slot.
const isAtSubagentLimit = (reason: string): boolean => reason.includes('Concurrent subagent limit reached')

// A check waiting for a slot asks again this often. It does not wait for a
// subagent's end instead: that end may reach this module before the engine
// gives the slot back (the slot is released as the run's completion is
// recorded), and a retry it set off could be refused with no end to follow.
const SLOT_RETRY_MS = 15_000

// A timer, not `$.clock.sleep`, which counts against a hook's budget.
const pause = ($: EngineInterface, ms: number): Promise<void> =>
  new Promise(resolve => {
    $.clock.after(ms, () => resolve())
  })

// An entry withdrawn while it waits starts no checker; its end then finds it
// gone from `checking` and does nothing.
const startChecker = async ($: EngineInterface, entry: QuestionZoneEntry): Promise<Start> => {
  try {
    for (;;) {
      if (!(await read($, queue)).checking.some(sameEntry(entry))) {
        return { kind: 'failed', reason: 'withdrawn before its check started' }
      }
      const spawned = await $.agent.spawn({
        subagentType: CHECKER,
        description: 'Check a question for the person',
        prompt: `Context:\n${entry.context}\n\nQuestion:\n${entry.question}`,
      })
      if (spawned.deny === undefined) {
        return spawned.agentId === undefined
          ? { kind: 'failed', reason: 'no checker started' }
          : { kind: 'started', agentId: spawned.agentId }
      }
      if (!isAtSubagentLimit(spawned.deny)) {
        return { kind: 'failed', reason: spawned.deny }
      }
      await pause($, SLOT_RETRY_MS)
    }
  } catch (error) {
    return { kind: 'failed', reason: describeError(error) }
  }
}

// Checkers start one at a time, in the order asked, so a check waiting for a
// slot holds back each one asked after it. A start never rejects
// (startChecker answers every failure), so the line never stops.
let startLine: Promise<void> = Promise.resolve()

const inAskOrder = (start: () => Promise<Start>): Promise<Start> => {
  const started = startLine.then(start)
  startLine = started.then(() => undefined)
  return started
}

const check = async ($: EngineInterface, entry: QuestionZoneEntry): Promise<Verdict> => {
  checksInFlight += 1
  try {
    return await runCheck($, entry)
  } finally {
    checksInFlight -= 1
    if (checksInFlight === 0) {
      endedEarly.clear()
    }
  }
}

const runCheck = async ($: EngineInterface, entry: QuestionZoneEntry): Promise<Verdict> => {
  const start = await inAskOrder(() => startChecker($, entry))
  if (start.kind === 'failed') {
    return start
  }

  const turn = await runEnd(start.agentId)
  if (turn.reason !== 'answer') {
    return { kind: 'failed', reason: `the checker's run ended without an answer (${turn.reason})` }
  }
  const answer = turn.answer.trim()
  if (answer === '') {
    return { kind: 'failed', reason: 'the checker gave no answer' }
  }
  return /^clear\.?$/i.test(answer) ? { kind: 'clear' } : { kind: 'refused', reply: answer }
}

const describeError = (error: unknown): string =>
  error instanceof Error ? `${error.name}: ${error.message}` : String(error)

// What the model does with a question that came back: fix it silently when it
// can, and tell the person, once, what stopped a check only they can unblock
// (the person, 2026-11-08: "it can just tell me to turn off the thing
// consuming gpu. that's an entirely fine pushback").
const COULD_NOT_RUN =
  'tell the person once, in plain words, what stopped the check and what they can do about it, and do not ask this question again until they say the cause is fixed'

const refusalText = (entry: QuestionZoneEntry, verdict: Exclude<Verdict, { kind: 'clear' }>): string =>
  verdict.kind === 'refused'
    ? [
        `question-zone: your question "${entry.question}" came back from its check and is not in the queue. The checker's reply:`,
        verdict.reply,
        `If the reply says a reader could not follow the question, rewrite it and ask again. If it gives the person's existing answer, use that answer. Say nothing in chat about either. If it says the check could not be made, ${COULD_NOT_RUN}.`,
      ].join('\n')
    : `question-zone: the check of your question "${entry.question}" could not run (${verdict.reason}), so it is not in the queue. Nothing unchecked joins the queue: ${COULD_NOT_RUN}.`

// A question that comes back reaches the model as a row of the conversation
// the person does not see as typed, which starts no turn and is carried by the model's
// next request (observed 2026-11-08 under `claude -p`, Claude Code 2.1.318).
// A row the session's main loop has not yet sent in a request is unread. A
// row can settle after a turn's last request, or while the session is idle;
// then nothing would carry it, so once no main turn runs and no check is
// running (or this long has passed since the wait began), one short prompt
// starts a turn whose first request carries every unread row. The prompt
// carries none of their text, so each reaches the model once, and a burst
// of asks costs one prompt the person sees; a check still running after the
// cap can add one more when it ends.
const WAKE_WAIT_CAP_MS = 5 * 60_000
const WAKE_TEXT = "question-zone: questions you asked came back from their checks; the reasons are in this plugin's notes."

let isMainTurnRunning = false
const unreadRefusals = new Set<string>()
// Rows a prompt has already been sent for: never a second, so a turn that
// failed before its first request cannot set off a run of prompts.
const wokenFor = new Set<string>()
let wakeWait: { cycle: number; isCapped: boolean } | undefined
let wakeCycles = 0

const needsWake = (): boolean => [...unreadRefusals].some(id => !wokenFor.has(id))

const maybeWake = async ($: EngineInterface): Promise<void> => {
  if (!needsWake()) {
    wakeWait = undefined
    return
  }
  if (isMainTurnRunning) {
    return
  }
  if (wakeWait === undefined) {
    wakeCycles += 1
    const cycle = wakeCycles
    wakeWait = { cycle, isCapped: false }
    $.clock.after(WAKE_WAIT_CAP_MS, () => {
      if (wakeWait?.cycle === cycle) {
        wakeWait.isCapped = true
        wakeLater($)
      }
    })
  }
  if (!wakeWait.isCapped && (await read($, queue)).checking.length > 0) {
    return
  }
  // Asked again after the read: a turn may have started, or read the rows.
  if (isMainTurnRunning || !needsWake()) {
    return
  }
  wakeWait = undefined
  for (const id of unreadRefusals) {
    wokenFor.add(id)
  }
  // Not awaited: it resolves only as its own turn starts.
  void $.prompt.submit({ text: WAKE_TEXT }).then(
    result => {
      if (result.drop !== undefined) {
        $.ui.log(`question-zone: the prompt for questions that came back was dropped: ${result.drop}`, { to: 'debug' })
      }
    },
    (error: unknown) => {
      $.ui.log(`question-zone: could not send the prompt for questions that came back: ${describeError(error)}`, {
        to: 'debug',
      })
    },
  )
}

const wakeLater = ($: EngineInterface): void => {
  maybeWake($).catch((error: unknown) => {
    $.ui.log(`question-zone: could not decide whether to send a prompt: ${describeError(error)}`, { to: 'debug' })
  })
}

// A check's end: a clear entry moves from `checking` to the end of the
// queue; any other ends it with one hidden row for the model. An entry
// withdrawn meanwhile is no longer in `checking`, and its end does nothing.
const settleCheck = async ($: EngineInterface, entry: QuestionZoneEntry, verdict: Verdict): Promise<void> => {
  let wasChecking = false
  await update($, queue, state => {
    const at = state.checking.findIndex(sameEntry(entry))
    wasChecking = at >= 0
    if (!wasChecking) {
      return state
    }
    const checking = state.checking.filter((_, i) => i !== at)
    return verdict.kind === 'clear' ? { ...state, checking, waiting: [...state.waiting, entry] } : { ...state, checking }
  })
  if (wasChecking && verdict.kind !== 'clear') {
    const appended = await $.session.append({
      message: { type: 'user', content: [{ type: 'text', text: refusalText(entry, verdict) }] },
    })
    if (appended.deny === undefined) {
      unreadRefusals.add(appended.uuid)
    } else {
      $.ui.log(`question-zone: the note about a question that came back was refused: ${appended.deny}`, { to: 'debug' })
    }
  }
  // A check has ended: a wait for running checks may be over.
  await maybeWake($)
}

// The check takes a minute or more when it searches, past a hook's ten
// seconds of its own time (HookBudget), which waiting for a subagent's end
// counts against (observed 2026-11-08: both asks refused at 10.06 s). So it
// runs after the ask has answered.
const checkInBackground = ($: EngineInterface, entry: QuestionZoneEntry): void => {
  void (async () => {
    let verdict: Verdict
    try {
      verdict = await check($, entry)
    } catch (error) {
      verdict = { kind: 'failed', reason: describeError(error) }
    }
    await settleCheck($, entry, verdict)
  })().catch((error: unknown) => {
    $.ui.log(`question-zone: a check could not be settled: ${describeError(error)}`, { to: 'debug' })
  })
}

// A checker's report also reaches the main conversation by itself: in a
// session in auto mode each subagent ends by handing its report back, and the
// engine delivers it as a hidden prompt from a peer whose text opens
// `<agent-message from="<agent id>">` (observed 2026-11-08 in
// agent-notice-log.jsonl: 16 hand-backs, every one at prompt.submit, none at
// session.receive). The plugin reads the checker's answer at turn.complete
// and tells the model what it needs, so a checker's message is dropped: a
// clear check sends the model nothing, and a refusal reaches it once.
const AGENT_MESSAGE = /^<agent-message from="([^"]+)">/

const isCheckerReport = async ($: EngineInterface, e: Frozen<PromptSubmitInput>): Promise<boolean> => {
  const from = e.origin.kind === 'peer' && e.isMeta === true ? AGENT_MESSAGE.exec(e.text)?.[1] : undefined
  if (from === undefined) {
    return false
  }
  // Only this plugin starts a checker: the type is never offered to the model.
  return (await $.agent.list()).some(agent => agent.id === from && agent.type === CHECKER)
}

// Where this session's transcript file is, as the engine reports it
// (`transcript_path`) at the session's start and with each prompt the person
// sends. Unknown after a reload until the next of those.
let transcriptPath: string | undefined

// Entries the person has just answered whose record is not yet known. The
// row that keeps their prompt is told by the quoted question it carries.
let awaitingRecord: QuestionZoneEntry[] = []

// The rows that keep a prompt the person sent, as observed under `claude -p`
// with Claude Code 2.1.318 on 2026-11-08: one typed at an idle prompt is a
// `user` row (door `prompt`); one sent while the model works, a
// `queued_command` attachment (door `delivery`), its text inside a reminder.
const isPromptRow = (e: Frozen<SessionAppendInput>): boolean =>
  e.agentId === undefined &&
  ((e.message.type === 'user' && e.message.isMeta !== true && e.door === 'prompt') ||
    (e.message.type === 'attachment' && e.message.name === 'queued_command'))

const textOf = (e: Frozen<SessionAppendInput>): string =>
  e.message.content.map(block => (block.type === 'text' ? block.text : '')).join('\n')

// Not JSON: a line of some other kind, read past.
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

// A row reaches the transcript file only once its append, hooks and all, has
// run (observed: held inside its hook, a row stayed out of the file for 3 s;
// let go, it was there within 100 to 200 ms). So the record is looked for
// after the row is kept, until it is there or this long has passed.
const RECORD_POLL_MS = 100
const RECORD_WAIT_MS = 30_000

type Lookup = { line: number; timestamp: string | undefined } | { missing: string; isFinal: boolean }

// The record's line and timestamp, read from the file itself: the line grep
// finds holding `"uuid":"<uuid>"`, once that line parses as the record whose
// own uuid it is.
const lookUp = async ($: EngineInterface, path: string, uuid: string): Promise<Lookup> => {
  let found
  try {
    found = await $.process.run(['grep', '-n', '-F', '-e', `"uuid":"${uuid}"`, path])
  } catch (error) {
    return { missing: `grep could not run (${describeError(error)})`, isFinal: true }
  }
  if (found.exitCode !== 0) {
    const said = found.stderr.trim()
    return { missing: found.exitCode === 1 ? 'no line held it' : `grep failed: ${said === '' ? `exit ${found.exitCode}` : said}`, isFinal: false }
  }
  for (const hit of found.stdout.split('\n')) {
    const colon = hit.indexOf(':')
    const record = colon > 0 ? parseJson(hit.slice(colon + 1)) : undefined
    if (typeof record === 'object' && record !== null && 'uuid' in record && record.uuid === uuid) {
      const timestamp = 'timestamp' in record && typeof record.timestamp === 'string' ? record.timestamp : undefined
      return { line: Number(hit.slice(0, colon)), timestamp }
    }
  }
  return { missing: 'lines named it, but none was its record', isFinal: false }
}

const questionsOf = (entries: readonly QuestionZoneEntry[]): string =>
  entries.map(entry => `"${entry.question}"`).join(' and ')

// A path the shell reads as one word, quoted only when it has to be.
const shellWord = (text: string): string => (/^[\w@%+=:,./-]+$/.test(text) ? text : `'${text.replaceAll("'", "'\\''")}'`)

const citationOf = async ($: EngineInterface, uuid: string, entries: readonly QuestionZoneEntry[]): Promise<string> => {
  const path = transcriptPath
  const uncited = (reason: string): string =>
    `question-zone: the citation for the person's answer to ${questionsOf(entries)} could not be derived: ${reason}. The record's uuid is ${uuid}; nothing else about it is known, and nothing here is guessed.`
  if (path === undefined) {
    return uncited("the engine has not said where this session's transcript is since the plugin last loaded")
  }
  for (let waited = 0; ; waited += RECORD_POLL_MS) {
    const looked = await lookUp($, path, uuid)
    if ('line' in looked) {
      return [
        `question-zone: the person's answer to ${questionsOf(entries)} is recorded here, ready to cite:`,
        `- transcript: ${path}`,
        `- line: ${looked.line}`,
        `- record uuid: ${uuid}`,
        `- timestamp: ${looked.timestamp ?? 'the record carries none'}`,
        `- resolver: sed -n '${looked.line}p' ${shellWord(path)}`,
      ].join('\n')
    }
    if (looked.isFinal || waited >= RECORD_WAIT_MS) {
      return uncited(`its record was not found in ${path} (${looked.missing})`)
    }
    await pause($, RECORD_POLL_MS)
  }
}

// The citation reaches the model as a row of the conversation, in the first
// request after the record is in the file: the turn's next request, or the
// next turn's first.
const citeInBackground = ($: EngineInterface, uuid: string, entries: readonly QuestionZoneEntry[]): void => {
  void (async () => {
    const text = await citationOf($, uuid, entries)
    const appended = await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] } })
    if (appended.deny !== undefined) {
      $.ui.log(`question-zone: the citation of an answer was refused: ${appended.deny}`, { to: 'debug' })
    }
  })().catch((error: unknown) => {
    $.ui.log(`question-zone: could not give the citation of an answer: ${describeError(error)}`, { to: 'debug' })
  })
}

// The band's button. The box offers no way to put text ahead of a draft
// without rewriting the draft, so a box holding anything is left alone.
const take = async ($: EngineInterface): Promise<void> => {
  const head = (await read($, queue)).waiting[0]
  if (head === undefined) {
    return
  }
  const box = await $.prompt.read()
  if (box.text !== '') {
    $.ui.toast('Send or clear what you have typed first, then take the next question.')
    return
  }
  const filled = await $.prompt.fill({ text: boxText(head), mode: 'replace' })
  if (!filled.isFilled) {
    return
  }
  // One entry is taken at a time. An earlier taken entry the person cleared
  // from the box goes back to the head of the queue, so another entry's text
  // that quotes its question never answers it.
  await update($, queue, state => {
    const at = state.waiting.findIndex(sameEntry(head))
    if (at < 0) {
      return state
    }
    return {
      ...state,
      waiting: [...state.taken, ...state.waiting.filter((_, i) => i !== at)],
      taken: [head],
    }
  })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'ask',
      description: ASK_DESCRIPTION,
      inputSchema: {
        type: 'object',
        properties: {
          context: {
            type: 'string',
            description:
              'What the person needs to know to answer, in plain full sentences, and what their answer will change.',
          },
          question: { type: 'string', description: 'Exactly one question, in plain words.' },
        },
        required: ['context', 'question'],
      },
      isDeferred: false,
    })
    await $.tool.register({
      name: 'withdraw',
      description: WITHDRAW_DESCRIPTION,
      inputSchema: {
        type: 'object',
        properties: { question: { type: 'string', description: 'The question exactly as you asked it.' } },
        required: ['question'],
      },
      isDeferred: false,
    })
    await $.agent.register({
      name: 'checker',
      description: 'Checks that a question for the person stands alone and that the person has not already answered it.',
      prompt: CHECKER_PROMPT,
      // Read and search the decision records and run cc-search-chats.
      tools: ['Read', 'Bash'],
      model: 'sonnet',
      effort: 'xhigh',
    })

    const started = await next(e)
    // session.start runs once per fresh load of the module, whose memory then
    // holds no waiter: a check that was running when the plugin last loaded
    // ended with that load, and its entry is still in `checking`. Each such
    // entry is checked again; it joins the queue only if that check passes.
    for (const entry of (await read($, queue)).checking) {
      checkInBackground($, entry)
    }
    return started
  })

  on('agent.offer', { agent: CHECKER }, () => ({ isOffered: false }))

  on('turn.complete', async ($, e, next) => {
    if (e.agentId !== undefined) {
      const waiter = waiters.get(e.agentId)
      if (waiter !== undefined) {
        waiters.delete(e.agentId)
        waiter(e)
      } else if (checksInFlight > 0) {
        endedEarly.set(e.agentId, e)
      }
      return next(e)
    }
    // The main turn has ended: a row that came after its last request waits
    // for a prompt.
    isMainTurnRunning = false
    const ended = await next(e)
    wakeLater($)
    return ended
  })

  on('turn.start', ($, e, next) => {
    if (e.agentId === undefined) {
      isMainTurnRunning = true
    }
    return next(e)
  })

  // A request of the main loop carries the conversation so far, so every row
  // appended before it is read.
  on('turn.step', async function* ($, e, next) {
    if (e.agentId === undefined) {
      for (const id of unreadRefusals) {
        wokenFor.delete(id)
      }
      unreadRefusals.clear()
    }
    yield* next(e)
  })

  on('tool.call', { tool: ASK }, async ($, e, next) => {
    if (e.agentId !== undefined) {
      return { deny: 'Only the main session asks the person. Send your question to whoever gave you your task.' }
    }
    if (e.tool !== ASK) {
      return next(e)
    }
    const entry: QuestionZoneEntry = { context: trimmed(e.context), question: trimmed(e.question) }
    if (entry.context === '' || entry.question === '') {
      return { deny: 'Both context and question are needed, and neither may be empty.' }
    }

    await update($, queue, state => ({ ...state, checking: [...state.checking, entry] }))
    checkInBackground($, entry)
    return {
      result:
        "Being checked. If the check passes, the question joins the queue above the person's prompt; if not, a note will say why, and a question rewritten or dropped because of it needs no word in chat. Do not write the question in chat or say you are waiting, and do not mention it unless the person asks where things stand or returns after a long absence.",
    }
  }).catch(($, e, next) => ({
    deny: `The question was not taken for checking (${failureOf(next.error)}).`,
  }))

  on('tool.call', { tool: WITHDRAW }, async ($, e, next) => {
    if (e.agentId !== undefined) {
      return { deny: 'Only the main session withdraws questions for the person.' }
    }
    if (e.tool !== WITHDRAW) {
      return next(e)
    }
    const question = trimmed(e.question)
    const matches = (entry: QuestionZoneEntry): boolean => entry.question === question
    const before = await read($, queue)
    if (![...before.checking, ...before.waiting, ...before.taken].some(matches)) {
      return { deny: 'No waiting question has exactly that text. The system prompt lists the questions still waiting.' }
    }

    await update($, queue, state => ({
      checking: state.checking.filter(entry => !matches(entry)),
      waiting: state.waiting.filter(entry => !matches(entry)),
      taken: state.taken.filter(entry => !matches(entry)),
    }))
    return { result: 'Withdrawn.' }
  }).catch(() => ({ deny: 'The question could not be withdrawn.' }))

  // Only the person's own Enter settles a taken entry: a notification or a
  // plugin's prompt can arrive while the entry sits in their box. An entry it
  // answers then waits for the row that keeps the prompt, to be cited.
  on('prompt.submit', async ($, e, next) => {
    if (await isCheckerReport($, e)) {
      return { drop: "question-zone: a checker's report; the question box has it" }
    }
    if (e.origin.kind !== 'composer') {
      return next(e)
    }
    if ((await read($, queue)).taken.length > 0) {
      let answered: QuestionZoneEntry[] = []
      await update($, queue, state => {
        answered = state.taken.filter(isAnsweredBy(e.text))
        return {
          ...state,
          waiting: [...state.taken.filter(entry => !isAnsweredBy(e.text)(entry)), ...state.waiting],
          taken: [],
        }
      })
      awaitingRecord = [...awaitingRecord, ...answered]
    }
    return next(e)
  })

  on('classic.SessionStart', ($, e, next) => {
    transcriptPath = e.transcript_path
    return next(e)
  })

  on('classic.UserPromptSubmit', ($, e, next) => {
    transcriptPath = e.transcript_path
    return next(e)
  })

  // The row that keeps the person's answer: once it is kept, its record is
  // looked for in the transcript file, and its citation given to the model.
  on('session.append', async ($, e, next) => {
    const answered = awaitingRecord.length > 0 && isPromptRow(e) ? awaitingRecord.filter(isAnsweredBy(textOf(e))) : []
    if (answered.length === 0) {
      return next(e)
    }
    awaitingRecord = awaitingRecord.filter(entry => !answered.includes(entry))
    const kept = await next(e)
    citeInBackground($, e.uuid, answered)
    return kept
  })

  // Composed for every prompt the engine sends (types: `$.prompt.compose`),
  // so the list is current each turn. Not in an in-process teammate's render
  // of the lead's prompt: only the main session may ask.
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (e.traits.includes('teammate')) {
      return composed
    }
    const section = { id: SECTION_ID, text: ruleText(await read($, queue)), scope: 'session' } as const

    return { sections: [...composed.sections.filter(s => s.id !== SECTION_ID), section] }
  })

  // One line of counts, so questions still being checked never look like an
  // empty box, and the button while any question waits.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { checking, waiting } = await read($, queue)
    if (e.props.hasSurvey || (waiting.length === 0 && checking.length === 0)) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    const waitingCount =
      waiting.length === 1 ? '1 question is waiting for you' : `${waiting.length} questions are waiting for you`
    const checkingCount =
      waiting.length > 0
        ? `${checking.length} being checked`
        : checking.length === 1
          ? '1 question is being checked'
          : `${checking.length} questions are being checked`

    // Each tag ends on a string prop: the repository's instruction-delivery
    // test scans this source, and reads a `/` straight after `}` as the start
    // of a regular expression.
    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={2}>
          {waiting.length > 0 ? (
            <Box key="waiting">
              <Text bold>{waitingCount}</Text>
            </Box>
          ) : null}
          {checking.length > 0 ? (
            <Box key="checking">
              <Text>{checkingCount}</Text>
            </Box>
          ) : null}
        </Box>
        {waiting.length > 0 ? (
          <Button key="take" onPress={() => take($)} hotkey="1" plain label="Take the next question into the prompt box" />
        ) : null}
      </Box>
    )
  })
}
