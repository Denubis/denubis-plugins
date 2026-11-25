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
// The clarity reader, and the search for an answer the person already gave.
const CHECKER = 'denubis-hook-question-zone:checker'
const SEARCHER = 'denubis-hook-question-zone:searcher'
const SECTION_ID = 'denubis-hook-question-zone:rule'

const ASK_DESCRIPTION = [
  "Puts one question for the person in a queue shown above their prompt. When they are ready, one key puts the question into their prompt box, and their answer arrives as their next message, quoting your question. Use this tool for every question to the person; never write a question to them in chat.",
  '',
  'The person will read the entry on its own, perhaps much later, without this conversation. Write it for someone who has not read the conversation:',
  '- context: what they need to know to answer, in plain full sentences, and what their answer will change.',
  '- question: exactly one question.',
  'Use no file names, ticket or record numbers, agent names, or labels coined in this conversation, unless you explain each in plain words.',
  '',
  "The call returns at once. A reader who has not seen this conversation then checks that the entry stands alone, and a clear entry joins the queue as soon as that read ends. Unless the reader judges the entry a go-ahead for something you are about to do, such as a commit, a push, or running an approved plan, the project's decision records and the chat logs are then searched for an answer the person already gave, while the entry waits in the queue; a failed or incomplete search adds a visible warning to the entry while it still waits and never holds it, and once the person has taken the entry into their prompt box the search's end changes nothing and no warning is shown. A note from this plugin, which the person does not see as typed, reaches you at your next request when the reader could not understand the entry (rewrite it and ask again); when the search found the person's existing answer while the entry still waited, so it left the queue (use that answer, given with where and in what words); or when the clarity check could not run (tell the person once what stopped it and what they can do, and do not ask that question again until they say the cause is fixed). Say nothing in chat about a question rewritten or dropped this way.",
].join('\n')

const WITHDRAW_DESCRIPTION =
  "Removes a question from the queue above the person's prompt when you no longer need its answer. Give the question exactly as you asked it; the system prompt lists the questions still waiting."

// The person's ruling of 2026-11-18: the chat index is not brought up to date
// while it is less than five minutes old, because live sessions keep writing
// and each refresh loads the embedding model onto the graphics card.
const INDEX_DEBOUNCE_MS = 5 * 60_000

// The clarity reader's system prompt. It sees the entry and nothing of the
// conversation the entry came from, and has no tools. Its reply reaches the
// model unchanged unless it is CLEAR, so each refusal says what the model
// should do. The reader, never the asking model, says whether the entry is a
// go-ahead (the person's ruling of 2026-11-23).
const CHECKER_PROMPT = [
  'You check one entry before it is shown to a person. An assistant working with that person wrote it: a context and a question. The person will read the entry on its own, perhaps hours later, without the conversation it came from. You have not seen that conversation. Judge from the entry alone: you have no tools, and need none.',
  '',
  'Does the entry stand alone? Read it as that person would, and decide whether they could understand what is asked and answer it from the entry alone. It fails when it:',
  '- uses a term, name, abbreviation or label it does not explain in plain words, such as a file name, a ticket or record number, an agent name, or a word coined in the conversation;',
  '- refers to something the entry does not give, such as "the earlier option" or "as discussed";',
  '- asks more than one question.',
  'If it fails, stop there: reply with what the reader could not understand, in one or two plain sentences that quote the words at fault, and ask for the entry to be rewritten.',
  '',
  'If it stands alone, decide also whether it is a go-ahead: a question asking the person to let the assistant go ahead with something it is about to do, such as a commit, a push, or running an approved plan. A go-ahead is shown to the person with no further check; any other entry is also searched, while the person has it, for an answer they already gave. So when you are unsure, it is not a go-ahead.',
  'Reply with the two words CLEAR GO-AHEAD if the entry stands alone and is a go-ahead, with the one word CLEAR if it stands alone and is not, and nothing else.',
].join('\n')

// The search's system prompt. It runs once the entry is already in the
// queue, so it decides nothing about clarity. Its reply is read by the
// plugin: only ANSWERED takes the entry out of the queue, and any other reply
// than NOT_ANSWERED leaves the entry with a warning, if it still waits untaken.
const SEARCHER_PROMPT = [
  'You search for an answer a person has already given to one question. An assistant working with that person asked it, and the question is already waiting for them in a queue above their prompt. If you find their earlier answer, the question leaves the queue and the assistant uses that answer instead. You have not seen the conversation the question came from.',
  '',
  'Search for an answer in their own words:',
  "- in the project's decision records: `git rev-parse --path-format=absolute --git-common-dir` names the main checkout's git folder, whose parent is the main checkout; search its `docs/architecture/decisions/` and `docs/decisions/` with `rg`. A project with neither has no records to search;",
  `- in the chat logs. First run \`cc-search-chats index --status --json\`. If its \`index_state.age_ms\` is an integer below ${INDEX_DEBOUNCE_MS}, the index is under ${INDEX_DEBOUNCE_MS / 60_000} minutes old: do not run \`cc-search-chats index\`, and search the index as it is. Otherwise, if it reports \`index_state.freshness\` other than \`no_source_changes\`, bring the index up to date with \`cc-search-chats index --json\`. Searching an index under ${INDEX_DEBOUNCE_MS / 60_000} minutes old without bringing it up to date is not a failed lookup or incomplete coverage, and needs no warning.` +
    ' A warning that some files were left out, such as an unknown record shape, does not stop the search. Then search with `cc-search-chats search "<words>" --semantic --json`, or `--literal` for exact words. Each result\'s `identity.canonical_locator` is its `ccchat:v1:` locator, and `cc-search-chats context <locator> --json` shows the messages around it. Its JSON carries `schema_version` 5.',
  "Only the person's own words count: a message they typed themselves, or their words quoted in a decision record. A message written by an assistant, a plugin, a tool or an agent does not count. A paraphrase by an assistant or a record is not an answer, and neither is a remark that does not settle this question.",
  '',
  'Apart from bringing the chat index up to date, use only commands that read and search; change nothing.',
  '',
  'Reply in exactly one of these forms, and nothing else:',
  "- ANSWERED: followed by where the answer is (the record's path and line, or the `ccchat:v1:` locator) and the person's words, quoted exactly.",
  '- HISTORY_WARNING: followed by a short plain warning naming the failed command or the coverage left unread, when a lookup failed or its coverage was incomplete and you found no answer. Run the searches that are still possible first. Never claim unread records were searched or that no earlier answer exists.',
  '- NOT_ANSWERED alone, when every search completed in its stated coverage and found no answer.',
].join('\n')

const RULE = [
  'Questions for the person go through the question zone, a queue shown above their prompt.',
  `Every question for the person goes through the ${ASK} tool. Never write a question to the person in chat.`,
  'Never say you are waiting for an answer.',
  'Never mention, list or remind the person of questions waiting in the queue, except when they ask where things stand or return after a long absence.',
  `Then describe, in plain words and without referring to earlier messages, each decision still open and what its answer will change. The questions themselves stay in the queue, where the person takes the first one next; one not yet in it goes through ${ASK}.`,
  'An answer arrives as the person\'s message, quoting the question it answers.',
  'A note from this plugin tells you when a question comes back from its clarity check, or leaves the queue because a search found an answer the person already gave. If a reader could not follow it, rewrite it and ask again; if the person has already answered it, use that answer. Say nothing in chat about either.',
  'A failed or incomplete search appears as a warning on the queued question. If the clarity check itself could not run, tell the person once what stopped it and how to resolve it; keep that question held until clarity can be checked.',
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
const boxText = (entry: QuestionZoneEntry): string =>
  [
    ...(entry.historyWarning === undefined ? [] : [quote('History warning: ' + entry.historyWarning), '>']),
    quote(entry.context),
    '>',
    quote(entry.question),
    '',
    '',
  ].join('\n')

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

// Each clarity read and each search waits for its agent's run to end: the
// run's turn.complete carries the agentId $.agent.spawn answered. The run's
// end can reach this module before the spawn's answer does (observed under
// `claude plugin test`: the turn.complete hook ran first), so an agent's end
// that finds no waiter while a run is in flight is kept for the waiter that
// follows, and dropped once no run is in flight.
const waiters = new Map<string, (turn: Frozen<TurnCompleteInput>) => void>()
const endedEarly = new Map<string, Frozen<TurnCompleteInput>>()
let runsInFlight = 0

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

// How a clarity read ends.
type Verdict = { kind: 'clear'; isGoAhead: boolean } | { kind: 'refused'; reply: string } | { kind: 'failed'; reason: string }

// How a search for an earlier answer ends. A failed or incomplete search
// warns on a question still waiting in the queue, and never holds it (the
// person's ruling of 2026-11-10). Once the question has been taken into the
// prompt box nothing shows the warning: the box's text is not rewritten.
type Found = { kind: 'none' } | { kind: 'warning'; warning: string } | { kind: 'answered'; found: string }

type Start = { kind: 'started'; agentId: string } | { kind: 'failed'; reason: string }

// An agent's run: its answer, or why there is none.
type Run = { kind: 'answered'; answer: string } | { kind: 'failed'; reason: string }

// The engine refuses a spawn while the session runs as many subagents as it
// allows (CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS), in these words in Claude
// Code 2.1.312 and 2.1.318: "Concurrent subagent limit reached. You can run 5
// subagents at once. Do not retry. ..." (observed 2026-11-08: two of six
// checks refused so). A run refused so waits for a slot.
const isAtSubagentLimit = (reason: string): boolean => reason.includes('Concurrent subagent limit reached')

// A run waiting for a slot asks again this often. It does not wait for a
// subagent's end instead: that end may reach this module before the engine
// gives the slot back (the slot is released as the run's completion is
// recorded), and a retry it set off could be refused with no end to follow.
const SLOT_RETRY_MS = 15_000

// A timer, not `$.clock.sleep`, which counts against a hook's budget.
const pause = ($: EngineInterface, ms: number): Promise<void> =>
  new Promise(resolve => {
    $.clock.after(ms, () => resolve())
  })

const entryText = (entry: QuestionZoneEntry): string => `Context:\n${entry.context}\n\nQuestion:\n${entry.question}`

// Starts an agent once a slot is free. Before each try it asks whether the
// run is still wanted: an entry withdrawn, or taken, while it waits starts
// no agent, and its end then finds nothing to act on. A run that may not try
// yet (`mayTry`) waits as one refused at the limit does.
const startAgent = async (
  $: EngineInterface,
  spawn: { subagentType: string; description: string; prompt: string },
  isWanted: () => Promise<boolean>,
  mayTry: () => boolean = () => true,
): Promise<Start> => {
  try {
    for (;;) {
      if (!(await isWanted())) {
        return { kind: 'failed', reason: 'no longer needed before it started' }
      }
      if (mayTry()) {
        const spawned = await $.agent.spawn(spawn)
        if (spawned.deny === undefined) {
          return spawned.agentId === undefined
            ? { kind: 'failed', reason: 'no agent started' }
            : { kind: 'started', agentId: spawned.agentId }
        }
        if (!isAtSubagentLimit(spawned.deny)) {
          return { kind: 'failed', reason: spawned.deny }
        }
      }
      await pause($, SLOT_RETRY_MS)
    }
  } catch (error) {
    return { kind: 'failed', reason: describeError(error) }
  }
}

// Jobs in a line run one at a time, in the order they joined it. The jobs
// here never reject (startAgent and run answer every failure they meet), so
// a line never stops.
const lineUp = (): (<T>(job: () => Promise<T>) => Promise<T>) => {
  let line: Promise<void> = Promise.resolve()
  return job => {
    const done = line.then(job)
    line = done.then(() => undefined)
    return done
  }
}
// Clarity reads start in the order asked, so a read waiting for a slot holds
// back each one asked after it; once started, reads run side by side.
const readLine = lineUp()
// Searches run whole, one at a time, in the order their questions joined the
// queue (as their clarity reads ended, which need not be the order asked), so
// they hold at most one subagent slot between them (the supervisor's design
// of 2026-11-23).
const searchLine = lineUp()

// Clarity reads not yet started. A search tries for a slot only while there
// are none, so no search takes a slot a clarity read is waiting for. With one
// search at a time, a read waits on a search only when every other slot is
// taken.
let readsToStart = 0

// Searches queued or running, not yet ended. The prompt that carries unread
// notes waits for them as it does for clarity reads.
let searchesPending = 0

const run = async (start: () => Promise<Start>): Promise<Run> => {
  runsInFlight += 1
  try {
    const started = await start()
    if (started.kind === 'failed') {
      return started
    }
    const turn = await runEnd(started.agentId)
    if (turn.reason !== 'answer') {
      return { kind: 'failed', reason: `the run ended without an answer (${turn.reason})` }
    }
    const answer = turn.answer.trim()
    return answer === '' ? { kind: 'failed', reason: 'it gave no answer' } : { kind: 'answered', answer }
  } finally {
    runsInFlight -= 1
    if (runsInFlight === 0) {
      endedEarly.clear()
    }
  }
}

const checkClarity = async ($: EngineInterface, entry: QuestionZoneEntry): Promise<Verdict> => {
  readsToStart += 1
  const ran = await run(() =>
    readLine(async () => {
      try {
        return await startAgent(
          $,
          { subagentType: CHECKER, description: 'Check a question for the person', prompt: entryText(entry) },
          async () => (await read($, queue)).checking.some(sameEntry(entry)),
        )
      } finally {
        readsToStart -= 1
      }
    }),
  )
  if (ran.kind === 'failed') {
    return ran
  }
  const clear = /^clear(\s+go[- ]ahead)?\.?$/i.exec(ran.answer)
  return clear === null ? { kind: 'refused', reply: ran.answer } : { kind: 'clear', isGoAhead: clear[1] !== undefined }
}

// The queued entry a search acts on: still waiting, and never taken since its
// search began.
const searchedAt = (state: QuestionZoneQueue, entry: QuestionZoneEntry): number =>
  state.waiting.findIndex(waiting => sameEntry(entry)(waiting) && waiting.isSearching === true)

// Entries a take has claimed and not yet seen into the box, as they were when
// claimed. While its entry is claimed so, a search still counts as wanted, and
// one that ends keeps its result here: if the box refuses the entry, the take
// puts it back and hands that result on, so an entry put back never keeps a
// search that will not act on it.
const entryKey = (entry: QuestionZoneEntry): string => JSON.stringify([entry.context, entry.question])
const takesUnderway = new Map<string, { entry: QuestionZoneEntry; held?: Found }>()
const searchUnderTake = (entry: QuestionZoneEntry): { entry: QuestionZoneEntry; held?: Found } | undefined => {
  const take = takesUnderway.get(entryKey(entry))
  return take?.entry.isSearching === true ? take : undefined
}

const cannotFinish = (reason: string): Found => ({
  kind: 'warning',
  warning: `The search for an answer you already gave could not finish (${reason}).`,
})

const search = async ($: EngineInterface, entry: QuestionZoneEntry): Promise<Found> => {
  const ran = await searchLine(() =>
    run(() =>
      startAgent(
        $,
        { subagentType: SEARCHER, description: 'Search for an answer the person already gave', prompt: entryText(entry) },
        async () => searchedAt(await read($, queue), entry) >= 0 || searchUnderTake(entry) !== undefined,
        () => readsToStart === 0,
      ),
    ),
  )
  if (ran.kind === 'failed') {
    return cannotFinish(ran.reason)
  }
  const found = /^ANSWERED:\s*(\S[\s\S]*)$/i.exec(ran.answer)?.[1]
  if (found !== undefined) {
    return { kind: 'answered', found }
  }
  const warning = /^HISTORY_WARNING:\s*(\S[\s\S]*)$/i.exec(ran.answer)?.[1]
  if (warning !== undefined) {
    return { kind: 'warning', warning }
  }
  return /^not_answered\.?$/i.test(ran.answer) ? { kind: 'none' } : cannotFinish('its reply could not be read')
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
        `question-zone: your question "${entry.question}" came back from its clarity check and is not in the queue. The reader's reply:`,
        verdict.reply,
        `If the reply says a reader could not follow the question, rewrite it and ask again, and say nothing in chat about it. If it says the check could not be made, ${COULD_NOT_RUN}.`,
      ].join('\n')
    : `question-zone: the clarity check of your question "${entry.question}" could not run (${verdict.reason}), so it is not in the queue. Nothing unchecked joins the queue: ${COULD_NOT_RUN}.`

const answeredText = (entry: QuestionZoneEntry, found: string): string =>
  [
    `question-zone: your question "${entry.question}" has left the queue before the person reached it: a search of their decision records and past chats found an answer they already gave. Where it is, and their words:`,
    found,
    'Use that answer instead of asking, and say nothing in chat about it.',
  ].join('\n')

// A note reaches the model as a row of the conversation the person does not
// see as typed, which starts no turn and is carried by the model's next
// request (observed 2026-11-08 under `claude -p`, Claude Code 2.1.318). A row
// the session's main loop has not yet sent in a request is unread. A row can
// settle after a turn's last request, or while the session is idle; then
// nothing would carry it, so once no main turn runs and no clarity read or
// search is queued or running (or this long has passed since the wait
// began), one short prompt starts a turn whose first request carries every
// unread row. The prompt carries none of their text, so each reaches the
// model once, and a burst of asks costs one prompt the person sees; a read or
// search still pending after the cap can add one more when it ends. Searches
// waiting their turn count as pending, so a line of searches that each find
// an answer sends one prompt when the last ends, not one each.
const WAKE_WAIT_CAP_MS = 5 * 60_000
const WAKE_TEXT =
  "question-zone: questions you asked came back from their checks or left the queue; the reasons are in this plugin's notes."

let isMainTurnRunning = false
const unreadNotes = new Set<string>()
// Rows a prompt has already been sent for: never a second, so a turn that
// failed before its first request cannot set off a run of prompts.
const wokenFor = new Set<string>()
let wakeWait: { cycle: number; isCapped: boolean } | undefined
let wakeCycles = 0

const needsWake = (): boolean => [...unreadNotes].some(id => !wokenFor.has(id))

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
  if (!wakeWait.isCapped && (searchesPending > 0 || (await read($, queue)).checking.length > 0)) {
    return
  }
  // Asked again after the read: a turn may have started, or read the rows.
  if (isMainTurnRunning || !needsWake()) {
    return
  }
  wakeWait = undefined
  for (const id of unreadNotes) {
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

const note = async ($: EngineInterface, text: string): Promise<void> => {
  const appended = await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] } })
  if (appended.deny === undefined) {
    unreadNotes.add(appended.uuid)
  } else {
    $.ui.log(`question-zone: a note for the model was refused: ${appended.deny}`, { to: 'debug' })
  }
}

// A clarity read's end: a clear entry moves from `checking` to the end of the
// queue, and unless it is a go-ahead its search begins; any other end leaves
// one hidden row for the model. An entry withdrawn meanwhile is no longer in
// `checking`, and its end does nothing.
const settleCheck = async ($: EngineInterface, entry: QuestionZoneEntry, verdict: Verdict): Promise<void> => {
  let wasChecking = false
  await update($, queue, state => {
    const at = state.checking.findIndex(sameEntry(entry))
    wasChecking = at >= 0
    if (!wasChecking) {
      return state
    }
    const checking = state.checking.filter((_, i) => i !== at)
    return verdict.kind === 'clear'
      ? { ...state, checking, waiting: [...state.waiting, { ...entry, isSearching: !verdict.isGoAhead }] }
      : { ...state, checking }
  })
  if (wasChecking && verdict.kind === 'clear' && !verdict.isGoAhead) {
    searchInBackground($, entry)
  }
  if (wasChecking && verdict.kind !== 'clear') {
    await note($, refusalText(entry, verdict))
  }
  // A read has ended: a wait for running reads may be over.
  await maybeWake($)
}

// A search's end acts only on the entry it was started for, while it still
// waits in the queue untaken: an earlier answer takes it out and tells the
// model, a warning is shown on it, and nothing found leaves it be. Once the
// person has taken it into the prompt box, or answered or withdrawn it, the
// search's end does nothing and says nothing.
const settleSearch = async ($: EngineInterface, entry: QuestionZoneEntry, found: Found): Promise<void> => {
  let isRemoved = false
  await update($, queue, state => {
    const at = searchedAt(state, entry)
    isRemoved = at >= 0 && found.kind === 'answered'
    if (at < 0) {
      const take = searchUnderTake(entry)
      if (take !== undefined) {
        take.held = found
      }
      return state
    }
    const waiting = isRemoved
      ? state.waiting.filter((_, i) => i !== at)
      : state.waiting.map((queued, i) =>
          i !== at
            ? queued
            : found.kind === 'warning'
              ? { ...queued, isSearching: false, historyWarning: found.warning }
              : { ...queued, isSearching: false },
        )
    return { ...state, waiting }
  })
  if (isRemoved && found.kind === 'answered') {
    await note($, answeredText(entry, found.found))
  }
  // A search has ended: a wait for running reads and searches may be over.
  await maybeWake($)
}

// A clarity read and a search each take longer than a hook's ten seconds of
// its own time (HookBudget), which waiting for a subagent's end counts
// against (observed 2026-11-08: both asks refused at 10.06 s). So they run
// after the ask has answered.
const checkInBackground = ($: EngineInterface, entry: QuestionZoneEntry): void => {
  void (async () => {
    let verdict: Verdict
    try {
      verdict = await checkClarity($, entry)
    } catch (error) {
      verdict = { kind: 'failed', reason: describeError(error) }
    }
    await settleCheck($, entry, verdict)
  })().catch((error: unknown) => {
    $.ui.log(`question-zone: a check could not be settled: ${describeError(error)}`, { to: 'debug' })
  })
}

const searchInBackground = ($: EngineInterface, entry: QuestionZoneEntry): void => {
  searchesPending += 1
  void (async () => {
    let found: Found
    try {
      found = await search($, entry)
    } catch (error) {
      found = cannotFinish(describeError(error))
    } finally {
      searchesPending -= 1
    }
    await settleSearch($, entry, found)
  })().catch((error: unknown) => {
    $.ui.log(`question-zone: a search could not be settled: ${describeError(error)}`, { to: 'debug' })
  })
}

// A checker's report also reaches the main conversation by itself: in a
// session in auto mode each subagent ends by handing its report back, and the
// engine delivers it as a hidden prompt from a peer whose text opens
// `<agent-message from="<agent id>">` (observed 2026-11-08 in
// agent-notice-log.jsonl: 16 hand-backs, every one at prompt.submit, none at
// session.receive). The plugin reads the reader's and the searcher's answers
// at turn.complete and tells the model what it needs, so their messages are
// dropped: a clear read or a search that finds nothing sends the model
// nothing, and a refusal or an earlier answer reaches it once.
const AGENT_MESSAGE = /^<agent-message from="([^"]+)">/
const CHECKERS: readonly string[] = [CHECKER, SEARCHER]

const isCheckerReport = async ($: EngineInterface, e: Frozen<PromptSubmitInput>): Promise<boolean> => {
  const from = e.origin.kind === 'peer' && e.isMeta === true ? AGENT_MESSAGE.exec(e.text)?.[1] : undefined
  if (from === undefined) {
    return false
  }
  // Only this plugin starts its checkers: the types are never offered to the model.
  return (await $.agent.list()).some(agent => agent.id === from && CHECKERS.includes(agent.type))
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
  // One entry is taken at a time. An earlier taken entry the person cleared
  // from the box goes back to the head of the queue, so another entry's text
  // that quotes its question never answers it. Once taken, an entry is out of
  // its search's reach for good (the proposal the person approved on
  // 2026-11-23: "if you have already pulled the question into your prompt
  // box, it is left alone"). The entry is claimed before the box is filled,
  // in one update, so a search that ends meanwhile either took it out first,
  // and the box stays empty, or finds it claimed and keeps its result on the
  // claim (`takesUnderway`) until the box answers.
  const claim: { entry?: QuestionZoneEntry; before: readonly QuestionZoneEntry[] } = { before: [] }
  await update($, queue, state => {
    const at = state.waiting.findIndex(sameEntry(head))
    const entry = state.waiting[at]
    claim.entry = entry
    claim.before = state.taken
    if (entry === undefined) {
      return state
    }
    takesUnderway.set(entryKey(entry), { entry })
    return {
      ...state,
      waiting: [...state.taken, ...state.waiting.filter((_, i) => i !== at)],
      taken: [{ ...entry, isSearching: false }],
    }
  })
  const { entry, before } = claim
  if (entry === undefined) {
    return
  }
  const filled = await $.prompt.fill({ text: boxText(entry), mode: 'replace' })
  if (filled.isFilled) {
    // Taken: a result kept on the claim is dropped, as the search's end would
    // have been.
    takesUnderway.delete(entryKey(entry))
    return
  }
  // Nothing reached the box, so the claim is undone: the entry is next again
  // with its search, and what was taken before is taken again. A search that
  // ended meanwhile acts now, as if the person had never pressed; one still
  // running acts when it ends.
  const wasTaken = (waiting: QuestionZoneEntry): boolean => before.some(sameEntry(waiting))
  await update($, queue, state =>
    state.taken.some(sameEntry(entry))
      ? { ...state, waiting: [entry, ...state.waiting.filter(w => !wasTaken(w))], taken: state.waiting.filter(wasTaken) }
      : state,
  )
  const held = takesUnderway.get(entryKey(entry))?.held
  takesUnderway.delete(entryKey(entry))
  if (held !== undefined) {
    await settleSearch($, entry, held)
  }
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
      description: 'Checks that a question for the person stands alone, and whether it is a go-ahead.',
      prompt: CHECKER_PROMPT,
      // It judges the entry alone, and searches nothing.
      tools: [],
      model: 'sonnet',
      effort: 'xhigh',
    })
    await $.agent.register({
      name: 'searcher',
      description: 'Searches the decision records and the chat logs for an answer the person already gave to a queued question.',
      prompt: SEARCHER_PROMPT,
      // Read and search the decision records and run cc-search-chats.
      tools: ['Read', 'Bash'],
      model: 'sonnet',
      effort: 'xhigh',
    })

    const started = await next(e)
    // session.start runs once per fresh load of the module, whose memory then
    // holds no waiter: a read or search that was running when the plugin last
    // loaded ended with that load. An entry still in `checking` is read
    // again, and joins the queue only if that read passes; a queued entry
    // whose search had not ended is searched again.
    const stored = await read($, queue)
    for (const entry of stored.checking) {
      checkInBackground($, entry)
    }
    for (const entry of stored.waiting) {
      if (entry.isSearching === true) {
        searchInBackground($, entry)
      }
    }
    return started
  })

  on('agent.offer', { agent: CHECKER }, () => ({ isOffered: false }))
  on('agent.offer', { agent: SEARCHER }, () => ({ isOffered: false }))

  on('turn.complete', async ($, e, next) => {
    if (e.agentId !== undefined) {
      const waiter = waiters.get(e.agentId)
      if (waiter !== undefined) {
        waiters.delete(e.agentId)
        waiter(e)
      } else if (runsInFlight > 0) {
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
      for (const id of unreadNotes) {
        wokenFor.delete(id)
      }
      unreadNotes.clear()
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
        "Being read for clarity. If the reader can follow it, the question joins the queue above the person's prompt, and unless it is a go-ahead a search for an answer they already gave runs while it waits; if the read fails, or the search finds their answer and takes the question out of the queue, a note will say so, and a question rewritten or dropped because of it needs no word in chat. Do not write the question in chat or say you are waiting, and do not mention it unless the person asks where things stand or returns after a long absence.",
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
        {waiting[0]?.historyWarning === undefined ? null : (
          <Text>{'History warning: ' + waiting[0].historyWarning}</Text>
        )}
        {waiting.length > 0 ? (
          <Button key="take" onPress={() => take($)} hotkey="1" plain label="Take the next question into the prompt box" />
        ) : null}
      </Box>
    )
  })
}
