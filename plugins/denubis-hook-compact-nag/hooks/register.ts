import { atom, read, update } from 'claude-code'
import type { EngineInterface, ModelUsage, Register } from 'claude-code'

import type { CompactNagLoop } from '../types'

// Thresholds, as whole percentages of the session model's context window.
// The mod never compacts on a threshold: a session compacts when it says it
// is ready. Past URGENT_AT the note turns urgent, and the main session gets
// one at every stop until it is ready.
const NAG_AT = 40
const RENAG_EVERY = 5
const URGENT_AT = 50

const MAIN = 'main'
const TOOL_NAME = 'ready_to_compact'
// Spelled whole: the tool.call matcher must be a literal the engine can read.
const TOOL = 'mcp__denubis-hook-compact-nag__ready_to_compact'

// Change the tag when CompactNagLoop's fields change: a reload then reads an
// older stored value as empty instead of misreading it.
const loops = atom(
  { plugin: 'denubis-hook-compact-nag', key: 'loops' } as const,
  {} as Record<string, CompactNagLoop>,
  { shape: 'loops-1' },
)

const keyOf = (agentId: string | undefined) => agentId ?? MAIN

const fresh = (now: number): CompactNagLoop => ({ percent: 0, cycleStart: now })

const say = (text: string) => ({
  type: 'user' as const,
  content: [{ type: 'text' as const, text }],
})

const opening = (percent: number) =>
  percent >= URGENT_AT
    ? `[compact-nag] URGENT: context is at ${percent}% of the window, past ${URGENT_AT}%. Stop taking on work and hand over now.`
    : `[compact-nag] Context is at ${percent}% of the window. Prepare for compaction.`

const mainNag = (percent: number) =>
  [
    opening(percent),
    'Hand over before detail is lost. Finish the step you are on; start nothing new. Then:',
    '1. Update the TODO list and any plan file: done, in progress, next.',
    "2. Write or update your worklog note under the main repository's .notes/ (no approval needed for it):",
    '   what you did, decisions and their evidence, open questions, the exact next step.',
    '3. Record decisions as the project rules allow: a ruling the human already made goes in the decision register;',
    '   an ADR or note change that needs approval is written as a proposal or an open-question ticket, not applied.',
    `4. Call ${TOOL} with \`brief\` (what the compaction summary must keep, drop, and tell your next self to re-read first)`,
    '   and `saved` (the paths of the files you updated). The session compacts when that turn ends.',
  ].join('\n')

const agentNag = (percent: number) =>
  [
    opening(percent),
    'Best: finish now and report back. If you must go on, hand over first:',
    "write your progress (done, findings with evidence, next step) to the file your task names, or else your",
    "worklog note under the main repository's .notes/ (no approval needed for it),",
    `then call ${TOOL} with \`brief\` (what your compaction summary must keep) and \`saved\` (those paths).`,
    'Claude Code compacts subagents only at its own threshold; your brief is used then.',
  ].join('\n')

const heardFrom = (agentId: string, percent: number) =>
  `[compact-nag] Subagent ${agentId} is at ${percent}% of its context and was told to ${
    percent >= URGENT_AT ? 'hand over urgently' : 'prepare for compaction'
  }. Subagents are not compacted early; consider telling it to finish and report back.`

// Instructions for a compaction: the person's own words first, then the
// loop's brief and its handover files.
const instructionsFor = (loop: CompactNagLoop | undefined, typed?: string) => {
  const parts = [typed, loop?.brief]
  if (loop?.saved?.length)
    parts.push(
      `Handover files, which the session must re-read first after this compaction: ${loop.saved.join(', ')}.`,
    )
  const text = parts.filter(part => part !== undefined && part.trim() !== '').join('\n\n')
  return text === '' ? undefined : text
}

const tokensOf = (usage: ModelUsage) =>
  usage.input_tokens +
  usage.cache_read_input_tokens +
  usage.cache_creation_input_tokens +
  usage.output_tokens

// Records one loop's fill after a model request; nags when due.
async function measure($: EngineInterface, agentId: string | undefined, usage: ModelUsage) {
  const key = keyOf(agentId)
  const { context } = await $.session.usage()
  if (context.window <= 0) return
  const percent = Math.round((tokensOf(usage) / context.window) * 100)
  const now = await $.clock.now()
  let isDue = false
  await update($, loops, all => {
    const loop = all[key] ?? fresh(now)
    isDue =
      percent >= NAG_AT &&
      loop.isReady !== true &&
      (loop.lastNagPercent === undefined || percent >= loop.lastNagPercent + RENAG_EVERY)
    const nagged = isDue ? { lastNagPercent: percent, nagAt: loop.nagAt ?? now } : {}
    return { ...all, [key]: { ...loop, percent, ...nagged } }
  })
  if (!isDue) return
  if (agentId === undefined) {
    await $.session.append({ message: say(mainNag(percent)) })
    $.ui.status(`context ${percent}%: handover asked`)
    return
  }
  await $.session.append({ message: say(agentNag(percent)), agentId })
  // The main conversation hears of it too, so whoever dispatched the
  // subagent can tell it to wrap up.
  await $.session.append({ message: say(heardFrom(agentId, percent)) })
}

async function resetLoop($: EngineInterface, key: string) {
  const now = await $.clock.now()
  await update($, loops, all => ({ ...all, [key]: fresh(now) }))
}

async function compactMain($: EngineInterface) {
  const instructions = instructionsFor((await read($, loops))[MAIN])
  try {
    const result = await $.session.compact(instructions === undefined ? {} : { instructions })
    if (result.skip !== undefined) {
      $.ui.log(`compact-nag: compaction skipped: ${result.skip}`)
      return
    }
    await resetLoop($, MAIN)
    $.ui.status(undefined)
  } catch (error) {
    // Rejects while a turn runs (a prompt queued during the last one); the
    // record stays as it is, so the next turn's end tries again.
    $.ui.log(`compact-nag: compaction deferred: ${String(error)}`)
  }
}

const stringList = (value: unknown) =>
  Array.isArray(value) && value.every(item => typeof item === 'string' && item.trim() !== '')
    ? (value as string[])
    : undefined

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.tool.register({
      name: TOOL_NAME,
      description: [
        'Say you are ready to compact, after saving handover state (TODOs, worklog, decision',
        'proposals). `brief`: your own instructions for the compaction summary. `saved`: the',
        'paths of the handover files you updated; each must have changed since the context',
        'reminder. In the main session, compaction runs when this turn ends.',
      ].join(' '),
      inputSchema: {
        type: 'object',
        properties: {
          brief: {
            type: 'string',
            description:
              'What the compaction summary must keep verbatim, what it may drop, and what your next self should re-read first.',
          },
          saved: {
            type: 'array',
            items: { type: 'string' },
            description: 'Paths of the handover files you updated (TODO list or plan, worklog, proposals).',
          },
        },
        required: ['brief', 'saved'],
      },
      isDeferred: false,
    })
    await $.command.register({
      name: 'compact-nag',
      description: 'Show context fill and handover state per loop (main and subagents)',
    })
    return started
  })

  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    if (result.usage !== null) {
      try {
        await measure($, e.agentId, result.usage)
      } catch (error) {
        $.ui.log(`compact-nag: could not measure context: ${String(error)}`)
      }
    }
    return result
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    const key = keyOf(e.agentId)
    const brief = 'brief' in e && typeof e.brief === 'string' ? e.brief.trim() : ''
    const saved = 'saved' in e ? stringList(e.saved) : undefined
    if (brief === '' || saved === undefined || saved.length === 0)
      return { result: 'Not accepted: give a non-empty `brief` and at least one path in `saved`.' }

    const now = await $.clock.now()
    const loop = (await read($, loops))[key] ?? fresh(now)
    const since = loop.nagAt ?? loop.cycleStart
    const stale: string[] = []
    for (const path of saved) {
      const stat = await $.fs.stat(path).catch(() => undefined)
      if (stat === undefined) stale.push(`${path} (missing)`)
      else if (stat.mtimeMs < since) stale.push(`${path} (not changed since the reminder)`)
    }
    if (stale.length > 0)
      return {
        result: `Not accepted. Update these first, then call again: ${stale.join('; ')}.`,
      }

    await update($, loops, all => ({
      ...all,
      [key]: { ...(all[key] ?? loop), brief, saved, isReady: true },
    }))
    return {
      result:
        key === MAIN
          ? 'Accepted. This session compacts with your brief when this turn ends. Finish your reply now; start no new work.'
          : 'Accepted. Your brief is kept for when Claude Code compacts you. Finish and report back if you can.',
    }
  })

  // Main loop, at each stop: compact once the session said it is ready
  // (between turns, the only time a mod can); past URGENT_AT and not ready,
  // leave an urgent note it reads at its next turn.
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined || e.isAborted) return done
    const loop = (await read($, loops))[MAIN]
    if (loop?.isReady === true) {
      $.clock.after(500, () => void compactMain($))
      return done
    }
    const percent = loop?.percent ?? 0
    if (percent >= URGENT_AT) {
      await $.session.append({ message: say(mainNag(percent)) })
      $.ui.status(`context ${percent}%: handover overdue`)
    }
    return done
  })

  // Every other compaction (/compact, Claude Code's own, a subagent's) gets
  // the loop's brief; a compaction that stands starts a new cycle.
  on('session.compact', async ($, e, next) => {
    const key = keyOf(e.agentId)
    const loop = (await read($, loops))[key]
    const instructions = instructionsFor(loop, e.instructions)
    const result = await next(instructions === undefined ? e : { ...e, instructions })
    if (e.trigger !== 'precompute' && result.skip === undefined) await resetLoop($, key)
    return result
  })

  on('command.run', { command: 'compact-nag' }, async $ => {
    const all = await read($, loops)
    const rows = Object.entries(all).map(([key, loop]) => {
      const state = loop.isReady === true ? 'ready' : loop.nagAt !== undefined ? 'nagged' : 'ok'
      const files = loop.saved?.length ? ` saved: ${loop.saved.join(', ')}` : ''
      return `${key}: ${loop.percent}% ${state}${files}`
    })
    const head = `note at ${NAG_AT}%, again every ${RENAG_EVERY}%, urgent from ${URGENT_AT}% (main: at every stop); compaction only when a session is ready`
    return { text: [head, ...(rows.length ? rows : ['no model requests measured yet'])].join('\n') }
  })
}
