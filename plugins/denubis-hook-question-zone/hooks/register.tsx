import { atom, read, update } from 'claude-code'
import type { EngineInterface, Frozen, HookFailure, Register, TurnCompleteInput } from 'claude-code'

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
  "The call returns at once, and the entry is checked before it joins the queue: a reader who has not seen this conversation checks that it stands alone, and searches the project's decision records and the chat logs for an answer the person has already given. A clear entry joins the queue when its check ends. Otherwise one message from this plugin comes back with the reason: what the reader could not understand (rewrite the entry and ask again), the person's existing answer with where and in what words (use it instead of asking), or why the check could not run.",
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
  "Only the person's own words count: a message they typed themselves, not an assistant's, a plugin's, a tool's or an agent's, or their words quoted in a decision record. A paraphrase by an assistant or a record is not an answer, and neither is a remark that does not settle this question.",
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
  'Never mention, list or remind the person of questions waiting in the queue, and never say you are waiting for an answer.',
  'An answer arrives as the person\'s message, quoting the question it answers.',
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
  const spawned = await $.agent.spawn({
    subagentType: CHECKER,
    description: 'Check a question for the person',
    prompt: `Context:\n${entry.context}\n\nQuestion:\n${entry.question}`,
  })
  if (spawned.deny !== undefined) {
    return { kind: 'failed', reason: spawned.deny }
  }
  if (spawned.agentId === undefined) {
    return { kind: 'failed', reason: 'no checker started' }
  }

  const turn = await runEnd(spawned.agentId)
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

const refusalText = (entry: QuestionZoneEntry, verdict: Exclude<Verdict, { kind: 'clear' }>): string =>
  verdict.kind === 'refused'
    ? `question-zone: your question "${entry.question}" was not queued. The checker's reply:\n${verdict.reply}`
    : `question-zone: your question "${entry.question}" was not queued, because its check could not run (${verdict.reason}). Nothing unchecked joins the queue.`

// A check's end: a clear entry moves from `checking` to the end of the
// queue; any other ends it with one message to the model, which starts a turn
// once the session is idle. An entry withdrawn meanwhile is no longer in
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
    return verdict.kind === 'clear' ? { ...state, checking, waiting: [...state.waiting, entry] } : { ...state, checking }
  })
  if (!wasChecking || verdict.kind === 'clear') {
    return
  }
  // Not awaited: it resolves only as its own turn starts.
  void $.prompt.submit({ text: refusalText(entry, verdict) }).then(
    result => {
      if (result.drop !== undefined) {
        $.ui.log(`question-zone: the message about a refused question was dropped: ${result.drop}`, { to: 'debug' })
      }
    },
    (error: unknown) => {
      $.ui.log(`question-zone: could not send the message about a refused question: ${describeError(error)}`, {
        to: 'debug',
      })
    },
  )
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

  on('turn.complete', ($, e, next) => {
    if (e.agentId !== undefined) {
      const waiter = waiters.get(e.agentId)
      if (waiter !== undefined) {
        waiters.delete(e.agentId)
        waiter(e)
      } else if (checksInFlight > 0) {
        endedEarly.set(e.agentId, e)
      }
    }
    return next(e)
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
        "Being checked. If the check passes, the question joins the queue above the person's prompt; if not, one message will say why. Do not write the question in chat, mention it, or say you are waiting.",
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
  // plugin's prompt can arrive while the entry sits in their box.
  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind !== 'composer') {
      return next(e)
    }
    if ((await read($, queue)).taken.length > 0) {
      await update($, queue, state => ({
        ...state,
        waiting: [...state.taken.filter(entry => !isAnsweredBy(e.text)(entry)), ...state.waiting],
        taken: [],
      }))
    }
    return next(e)
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

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { waiting } = await read($, queue)
    if (e.props.hasSurvey || waiting.length === 0) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    const count = waiting.length === 1 ? '1 question is waiting for you' : `${waiting.length} questions are waiting for you`

    // The tag ends on a string prop: the repository's instruction-delivery
    // test scans this source, and reads a `/` straight after `}` as the start
    // of a regular expression.
    return (
      <Box flexDirection="column">
        <Text bold>{count}</Text>
        <Button key="take" onPress={() => take($)} hotkey="1" plain label="Take the next question into the prompt box" />
      </Box>
    )
  })
}
