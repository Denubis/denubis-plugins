import { expect, mock, test } from 'claude-code/testing'
import type { On, SessionAppendInput } from 'claude-code'
import type { Engine } from 'claude-code/testing'

const WINDOW = 1000
const TOOL = 'mcp__denubis-hook-compact-nag__ready_to_compact'
const WORKLOG = '.notes/project_worklog.md'
// What a compaction runs over, and what the stand-in engine leaves after it.
const TRANSCRIPT = [{ role: 'user' as const, text: 'Fix the parser.', toolUses: [] }]

const textOf = (row: SessionAppendInput) => {
  const content: unknown = row.message.content
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content
    .map(block => (typeof block === 'object' && block !== null && 'text' in block ? String(block.text) : ''))
    .join('')
}

// Stands for the engine beneath the mod: a context window of 1000 tokens, a
// clock that moves only when told, files with the mtimes `files` holds, a
// record of every compaction that reached the bottom and of every prompt the
// mod submitted that entered the session. While `refusal.isTurnRunning` is
// set, a compaction is refused as Claude Code refuses one while a turn runs;
// while `refusal.skip` is set, it is vetoed as a plugin's hook vetoes one.
//
// A plugin's prompt starts a turn of its own only once the session is idle:
// while a main turn runs, or while a message taken ahead of it waits for its
// turn, the prompt waits and enters when that turn ends. With
// `queue.isMessageWaiting` set, a message (a supervisor's, say) is waiting
// when the next compaction ends: it is taken first, and its turn is the next
// main `turn.start` the test raises.
const engine = async ($: Engine, on: On, files: Record<string, number> = {}) => {
  const clock = mock.clock(on, { now: 1_000 })
  const session = mock.session(on)
  const compactions: { instructions: string | undefined; agentId: string | undefined }[] = []
  const prompts: string[] = []
  const refusal: { isTurnRunning: boolean; skip?: string } = { isTurnRunning: false }
  const queue = { isMessageWaiting: false }
  let tokens = 0
  let mainTurn: string | undefined
  let isMessageAhead = false
  let held: (() => void)[] = []

  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.register', (_, e) => ({ value: { tool: `mcp__denubis-hook-compact-nag__${e.name}` } }))
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('session.usage', () => ({
    value: { startedAt: 0, context: { window: WINDOW, tokens, percent: Math.round((tokens / WINDOW) * 100) }, rateLimits: [] },
  }))
  on('turn.start', (_, e) => {
    if (e.agentId === undefined) {
      mainTurn = e.turnId
      isMessageAhead = false
    }
    return { turnId: e.turnId }
  })
  on('turn.step', async function* (_, e) {
    return {
      turnId: e.turnId,
      index: e.index,
      answer: '',
      toolUses: [],
      stopReason: 'end_turn' as const,
      usage: { input_tokens: tokens, output_tokens: 0, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, model: 'claude-opus-5-5' },
    }
  })
  on('turn.complete', (_, e) => {
    if (e.agentId === undefined && e.turnId === mainTurn) {
      mainTurn = undefined
      const waiting = held
      held = []
      for (const enter of waiting) enter()
    }
    return { text: e.answer }
  })
  on('session.compact', (_, e) => {
    if (refusal.isTurnRunning) throw new Error('$.session.compact: a turn is running; the conversation compacts between turns')
    if (refusal.skip !== undefined) return { skip: refusal.skip }
    compactions.push({ instructions: e.instructions, agentId: e.agentId })
    if (queue.isMessageWaiting) {
      queue.isMessageWaiting = false
      isMessageAhead = true
    }
    return { messages: [{ role: 'user' as const, text: 'Summary.', toolUses: [] }] }
  })
  on('prompt.submit', (_, e) => {
    const enter = () => {
      prompts.push(e.text)
      return { text: e.text, origin: e.origin }
    }
    if (e.origin.kind !== 'plugin' || (mainTurn === undefined && !isMessageAhead)) return enter()
    return new Promise<ReturnType<typeof enter>>(resolve => held.push(() => resolve(enter())))
  })
  on('fs.stat', (_, e) => {
    // The engine hands the path on made absolute under the working directory.
    const known = Object.keys(files).find(path => e.path === path || e.path.endsWith(`/${path}`))
    const mtimeMs = known === undefined ? undefined : files[known]
    if (mtimeMs === undefined) throw new Error(`ENOENT: ${e.path}`)
    return { value: { kind: 'file' as const, size: 1, mtimeMs, isLink: false } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.log', () => ({ value: undefined }))

  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })

  // One model request of a loop, its context filled to `percent`.
  const request = async (percent: number, agentId?: string) => {
    tokens = (percent * WINDOW) / 100
    const stream = $.turn.step({
      turnId: 't',
      index: 0,
      model: 'claude-opus-5-5',
      messageCount: 1,
      ...(agentId === undefined ? {} : { agentId }),
    })
    for await (const _piece of stream) {
      // drained: only the result matters here
    }
  }
  // The main loop's turn ends with `answer`; `ms` of time pass for anything scheduled after it.
  const stop = async (answer = '', ms = 5_000) => {
    await $.turn.complete({ turnId: 't', answer, reason: 'answer', isAborted: false, durationMs: 1 })
    await clock.advance(ms)
  }
  const notes = (agentId?: string) => session.appended().filter(row => row.agentId === agentId).map(textOf)
  const ready = (saved: string[], brief = 'Keep the parser plan and the failing test name.') =>
    $.tool.call({ tool: TOOL, brief, saved })

  return { clock, compactions, notes, prompts, queue, ready, refusal, request, stop }
}

test('a session is told to prepare for compaction once it passes 40%, again 5 points later, not in between', async ($, on) => {
  const world = await engine($, on)

  await world.request(39)
  expect(world.notes()).toHaveLength(0)

  await world.request(40)
  expect(world.notes()).toHaveLength(1)
  expect(world.notes()[0]).toContain(TOOL)

  await world.request(43)
  expect(world.notes()).toHaveLength(1)

  await world.request(45)
  expect(world.notes()).toHaveLength(2)
})

test("a subagent's note goes into its own conversation, and the main conversation hears which subagent it was", async ($, on) => {
  const world = await engine($, on)

  await world.request(45, 'a1')

  expect(world.notes('a1')).toHaveLength(1)
  expect(world.notes('a1')[0]).toContain(TOOL)
  expect(world.notes()).toHaveLength(1)
  expect(world.notes()[0]).toContain('a1')
  expect(world.notes()[0]).not.toContain(TOOL)
})

test('the main session is never compacted unready; past 50% every stop leaves another note', async ($, on) => {
  const world = await engine($, on)

  await world.request(48)
  const before = world.notes().length
  await world.stop()
  expect(world.notes()).toHaveLength(before)

  await world.request(55)
  const afterRequest = world.notes().length
  await world.stop()
  await world.stop()

  expect(world.notes()).toHaveLength(afterRequest + 2)
  expect(world.compactions).toHaveLength(0)
})

test('a handover file unchanged since the note is refused; once changed, the session compacts at its stop with its own brief', async ($, on) => {
  const files: Record<string, number> = { [WORKLOG]: 500 }
  const world = await engine($, on, files)
  await world.request(42)

  await world.ready([WORKLOG])
  await world.stop()
  expect(world.compactions).toHaveLength(0)

  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG], 'Keep the parser plan.')
  expect(world.compactions).toHaveLength(0)
  await world.stop()

  expect(world.compactions).toHaveLength(1)
  expect(world.compactions[0]?.instructions).toContain('Keep the parser plan.')
  expect(world.compactions[0]?.instructions).toContain(WORKLOG)
})

test('once its own compaction is done, the session gets a turn quoting its handover reply and its brief, and naming its handover files', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG], 'Keep the parser plan.')

  await world.stop('Stopped for compaction. Next: rerun the parser tests, then fix the tokenizer.')

  expect(world.compactions).toHaveLength(1)
  expect(world.prompts).toHaveLength(1)
  expect(world.prompts[0]).toContain('Stopped for compaction. Next: rerun the parser tests, then fix the tokenizer.')
  expect(world.prompts[0]).toContain('Keep the parser plan.')
  expect(world.prompts[0]).toContain(WORKLOG)
})

test('a compaction that runs a turn late still quotes the reply the session handed over with, not the later one', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG])
  world.refusal.isTurnRunning = true
  await world.stop('Handed over. Next: fix the tokenizer.')
  world.refusal.isTurnRunning = false

  await world.stop('Answered the teammate about the fixtures.')

  expect(world.compactions).toHaveLength(1)
  expect(world.prompts).toHaveLength(1)
  expect(world.prompts[0]).toContain('Handed over. Next: fix the tokenizer.')
  expect(world.prompts[0]).not.toContain('Answered the teammate about the fixtures.')
})

test('a message waiting when its own compaction ends takes the next turn, and no resume prompt comes after that turn', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG])
  world.queue.isMessageWaiting = true

  // The compaction runs 500 ms after the stop; the supervisor's message, taken
  // ahead of anything submitted after it, starts its turn 300 ms later.
  await world.stop('Handed over. Next: fix the tokenizer.', 800)
  await $.turn.start({ turnId: 'lead', text: 'Carry on from your notes.' })
  await world.clock.advance(5_000)
  await $.turn.complete({ turnId: 'lead', answer: 'Carried on from the notes.', reason: 'answer', isAborted: false, durationMs: 1 })
  await world.clock.advance(5_000)

  expect(world.compactions).toHaveLength(1)
  expect(world.prompts).toHaveLength(0)
})

test('a compaction refused because a turn is running gives the session no turn', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG])
  world.refusal.isTurnRunning = true

  await world.stop()

  expect(world.compactions).toHaveLength(0)
  expect(world.prompts).toHaveLength(0)
})

test('a compaction the session did not ask for gives it no turn', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG])

  await $.session.compact({ trigger: 'manual', messages: TRANSCRIPT })
  await world.stop('The first reply after /compact.')

  expect(world.compactions).toHaveLength(1)
  expect(world.prompts).toHaveLength(0)
})

test('a compaction a plugin vetoes gives the session no turn', async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG])
  world.refusal.skip = 'vetoed'

  await world.stop()

  expect(world.compactions).toHaveLength(0)
  expect(world.prompts).toHaveLength(0)
})

test('a missing handover file is refused', async ($, on) => {
  const world = await engine($, on)
  await world.request(42)

  await world.ready(['.notes/never-written.md'])
  await world.stop()

  expect(world.compactions).toHaveLength(0)
})

test("a compaction the session did not start still carries its brief, after the person's own words", async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42)
  files[WORKLOG] = world.clock.now() + 1
  await world.ready([WORKLOG], 'Keep the parser plan.')

  await $.session.compact({ trigger: 'manual', messages: TRANSCRIPT, instructions: 'Focus on the API notes.' })

  const instructions = world.compactions[0]?.instructions ?? ''
  expect(instructions).toContain('Focus on the API notes.')
  expect(instructions).toContain('Keep the parser plan.')
  expect(instructions.indexOf('Focus on the API notes.')).toBeLessThan(instructions.indexOf('Keep the parser plan.'))
})

test("a subagent that said it is ready has its brief used when Claude Code compacts it", async ($, on) => {
  const files: Record<string, number> = {}
  const world = await engine($, on, files)
  await world.request(42, 'a1')
  files[WORKLOG] = world.clock.now() + 1
  await $.tool.call({ tool: TOOL, brief: 'Keep the three failing fixtures.', saved: [WORKLOG], agentId: 'a1' })

  await $.session.compact({ trigger: 'auto', messages: TRANSCRIPT, agentId: 'a1' })

  expect(world.compactions[0]?.agentId).toBe('a1')
  expect(world.compactions[0]?.instructions).toContain('Keep the three failing fixtures.')
})
