import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { AgentSpawnResult, On, PromptComposeSection, PromptOrigin, RenderSurface } from 'claude-code'

const PLUGIN = 'denubis-hook-question-zone'
const ASK = 'mcp__denubis-hook-question-zone__ask'
const WITHDRAW = 'mcp__denubis-hook-question-zone__withdraw'
const SURFACES = ['terminal', 'desktop'] as const

type Entry = { context: string; question: string }

const RELEASE: Entry = {
  context:
    'The new version of the plugin is built and every test passes. Releasing it today gets the fix to people before the weekend; waiting a day leaves time for one more check by hand.',
  question: 'Should the new version go out today?',
}

const NAMING: Entry = {
  context: 'The new plugin needs the name people will type to install it. The draft name is question-zone.',
  question: 'Is question-zone the name you want?',
}

// How one check ends: the checker's answer, its run ending some other way,
// the engine refusing to start it, or the spawn call itself failing.
type CheckEnd = { answer: string } | { ended: 'error' | 'aborted' } | { refused: string } | { fails: true }

type Spawned = { prompt: string; subagentType: string }

type EngineOptions = {
  checkEnds?: (prompt: string) => CheckEnd
  draft?: string
  // Hold each checker's run until the test ends it with `endNextCheck`.
  isHolding?: boolean
  // The queue the session's state holds as the plugin loads: what an earlier
  // load of this version kept there, read through a reload.
  stored?: { checking: readonly Entry[]; waiting: readonly Entry[]; taken: readonly Entry[] }
}

const INTRO: PromptComposeSection = { id: 'intro', text: 'engine prompt', scope: 'shared' }

// Stands for the engine beneath the plugin. It starts the session, registers
// the plugin's tools and agent types, starts the checker and ends its run as
// `checkEnds` says (after the spawn has answered, as a real run ends after it
// started), keeps a prompt box, lets every prompt in, records the plugin's
// own prompts, and composes a system prompt of one section.
const engine = async (
  $: Engine,
  on: On,
  { checkEnds = () => ({ answer: 'CLEAR' }), draft = '', isHolding = false, stored }: EngineOptions = {},
) => {
  const agents: { agent: string; model: string | undefined; tools: readonly string[] | undefined }[] = []
  const spawned: Spawned[] = []
  const toasts: string[] = []
  const messages: { text: string; origin: PromptOrigin }[] = []
  const held: (() => Promise<unknown>)[] = []
  const box = { text: draft, cursor: draft.length }
  const clock = mock.clock(on)

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
    const subagentType = 'subagent_type' in e && typeof e.subagent_type === 'string' ? e.subagent_type : e.subagentType
    spawned.push({ prompt: e.prompt, subagentType })
    const end = checkEnds(e.prompt)
    if ('refused' in end) {
      return { deny: end.refused }
    }
    if ('fails' in end) {
      // Nothing answers beneath, so the plugin's spawn call rejects.
      return next(e)
    }
    const agentId = `a-check-${spawned.length}`
    const turn = { agentId, durationMs: 1, turnId: `t-${agentId}` }
    const endRun = () =>
      'answer' in end
        ? $.turn.complete({ ...turn, answer: end.answer, reason: 'answer', isAborted: false })
        : $.turn.complete({ ...turn, answer: '', reason: end.ended, isAborted: end.ended === 'aborted' })
    if (isHolding) {
      held.push(endRun)
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
  on('prompt.read', () => ({ value: { ...box } }))
  on('prompt.fill', (_, e) => {
    const kept = e.mode === 'replace' ? '' : box.text
    const at = e.mode === 'insert' ? box.cursor : kept.length
    box.text = kept.slice(0, at) + e.text + kept.slice(at)
    box.cursor = e.cursor ?? at + e.text.length
    return { isFilled: true }
  })
  on('prompt.submit', (_, e) => {
    if (e.origin.kind === 'plugin') {
      messages.push({ text: e.text, origin: e.origin })
    }
    return { text: e.text, context: e.context, origin: e.origin }
  })
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
  // What the session's start set going runs as far as it can.
  await clock.settle()

  // The model calls ask; the background check then runs as far as it can.
  const ask = async (entry: Entry, agentId?: string) => {
    const result = await $.tool.call({ tool: ASK, ...entry, ...(agentId === undefined ? {} : { agentId }) })
    await clock.settle()
    return result
  }

  // A held checker's run ends, and what follows it settles.
  const endNextCheck = async (): Promise<void> => {
    const endRun = held.shift()
    expect(endRun).toBeDefined()
    await endRun?.()
    await clock.settle()
  }

  return { agents, spawned, toasts, messages, box, ask, endNextCheck }
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
// drawing, or the plugin's count and the hotkey of its one button.
type BandView = { isEngine: boolean; count: number | undefined; hotkey: unknown }

const bandOn = async ($: Engine, surface: RenderSurface & (typeof SURFACES)[number]): Promise<BandView> => {
  const ui = await $.ui.mount({ ...BAND, surface })
  const texts = (await ui.findAll({ type: 'Text' })).map(found => found.text)
  const button = await ui.find({ type: 'Button' })
  await ui.unmount()
  const number = texts.join(' ').match(/\d+/)

  return {
    isEngine: texts.length === 1 && texts[0] === 'engine' && button === undefined,
    count: number === null ? undefined : Number(number[0]),
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

const ENGINE_BAND: BandView = { isEngine: true, count: undefined, hotkey: undefined }

const waitingBand = (count: number): BandView => ({ isEngine: false, count, hotkey: '1' })

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

test('ask returns at once; the entry is listed while it is checked and joins the queue when the check passes', async ($, on) => {
  const zone = await engine($, on, { isHolding: true })

  const result = await zone.ask(RELEASE)

  expect(result.deny).toBeUndefined()
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
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

test('the checker is a registered Sonnet agent that can only read and search; its objection comes back as one plugin message', async ($, on) => {
  const objection = 'The entry says "the L5d split" without saying what that is. Rewrite it.'
  const zone = await engine($, on, { checkEnds: () => ({ answer: objection }) })

  await zone.ask(RELEASE)

  expect(zone.agents).toEqual([{ agent: expect.any(String), model: 'sonnet', tools: expect.any(Array) }])
  expect([...(zone.agents[0]?.tools ?? [])].sort()).toEqual(['Bash', 'Read'])
  expect(zone.spawned).toHaveLength(1)
  expect(zone.spawned[0]?.subagentType).toBe(zone.agents[0]?.agent)
  expect(zone.spawned[0]?.prompt).toContain(RELEASE.context)
  expect(zone.spawned[0]?.prompt).toContain(RELEASE.question)
  expect(zone.messages).toHaveLength(1)
  expect(zone.messages[0]?.origin).toEqual(FROM_PLUGIN)
  expect(zone.messages[0]?.text).toContain(objection)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])
})

test('an answer the person already gave comes back with its source and words; a question never answered is queued', async ($, on) => {
  const found =
    'The person already answered this at docs/decisions/2026-11-01-release-day.md:14: "Ship it today, the weekend fix matters more." Use that answer instead of asking.'
  const zone = await engine($, on, {
    checkEnds: prompt => ({ answer: prompt.includes(RELEASE.question) ? found : 'CLEAR' }),
  })

  await zone.ask(RELEASE)
  await zone.ask(NAMING)

  expect(zone.messages).toHaveLength(1)
  expect(zone.messages[0]?.text).toContain('docs/decisions/2026-11-01-release-day.md:14')
  expect(zone.messages[0]?.text).toContain('"Ship it today, the weekend fix matters more."')
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([NAMING.question])
})

test('a check that cannot run comes back as one message each, and nothing is queued', async ($, on) => {
  const indexBusy =
    'The check could not be made: `cc-search-chats index --json` failed because the graphics card is busy. Stopping the program using it lets the index run.'
  const ends: CheckEnd[] = [
    { refused: 'past a host limit' },
    { ended: 'error' },
    { ended: 'aborted' },
    { answer: indexBusy },
    { fails: true },
  ]
  const zone = await engine($, on, { checkEnds: () => ends.shift() ?? { answer: 'CLEAR' } })

  for (let i = 0; i < 5; i += 1) {
    expect((await zone.ask(RELEASE)).deny).toBeUndefined()
  }

  expect(zone.messages).toHaveLength(5)
  expect(zone.messages[0]?.text).toContain('past a host limit')
  expect(zone.messages[3]?.text).toContain(indexBusy)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])
  expect(listed(await pluginSections($), [RELEASE])).toEqual([])
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

test('the checker is never offered to the model', async ($, on) => {
  const zone = await engine($, on)
  const checker = zone.agents[0]?.agent ?? ''

  const offer = await $.agent.offer({
    agent: checker,
    description: 'checks a question',
    source: 'plugin',
    provider: { plugin: PLUGIN, tier: 'user' },
  })

  expect(checker).not.toBe('')
  expect(offer.isOffered).toBe(false)
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
    checkEnds: prompt => ({ answer: prompt.includes(NAMING.question) ? objection : 'CLEAR' }),
  })

  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question, NAMING.question])
  expect(zone.spawned).toHaveLength(2)
  expect(await band($)).toEqual([ENGINE_BAND, ENGINE_BAND])

  await zone.endNextCheck()
  await zone.endNextCheck()
  expect(await band($)).toEqual([waitingBand(1), waitingBand(1)])
  expect(listed(await pluginSections($), [RELEASE, NAMING])).toEqual([RELEASE.question])
  expect(zone.messages).toHaveLength(1)
  expect(zone.messages[0]?.text).toContain(objection)
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
