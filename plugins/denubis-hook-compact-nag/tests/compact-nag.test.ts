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
// clock that moves only when told, files with the mtimes `files` holds, and a
// record of every compaction that reached the bottom.
const engine = async ($: Engine, on: On, files: Record<string, number> = {}) => {
  const clock = mock.clock(on, { now: 1_000 })
  const session = mock.session(on)
  const compactions: { instructions: string | undefined; agentId: string | undefined }[] = []
  let tokens = 0

  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.register', (_, e) => ({ value: { tool: `mcp__denubis-hook-compact-nag__${e.name}` } }))
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('session.usage', () => ({
    value: { startedAt: 0, context: { window: WINDOW, tokens, percent: Math.round((tokens / WINDOW) * 100) }, rateLimits: [] },
  }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
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
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('session.compact', (_, e) => {
    compactions.push({ instructions: e.instructions, agentId: e.agentId })
    return { messages: [{ role: 'user' as const, text: 'Summary.', toolUses: [] }] }
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
  // The main loop's turn ends; time passes for anything scheduled after it.
  const stop = async () => {
    await $.turn.complete({ turnId: 't', answer: '', reason: 'answer', isAborted: false, durationMs: 1 })
    await clock.advance(1_000)
  }
  const notes = (agentId?: string) => session.appended().filter(row => row.agentId === agentId).map(textOf)
  const ready = (saved: string[], brief = 'Keep the parser plan and the failing test name.') =>
    $.tool.call({ tool: TOOL, brief, saved })

  return { clock, compactions, notes, ready, request, stop }
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
