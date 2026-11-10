/**
 * One model loop's handover record: the main conversation (key `main`) or a
 * subagent (key: its agent id). Reset when that loop compacts.
 */
export type CompactNagLoop = {
  /** Context fill at the loop's last model request, 0 to 100. */
  percent: number
  /** When this compaction cycle began (ms since the epoch). */
  cycleStart: number
  /** When the first nag of this cycle went out (ms since the epoch). */
  nagAt?: number
  /** The fill the last nag was sent at. */
  lastNagPercent?: number
  /** The session's own instructions for its compaction summary. */
  brief?: string
  /** Handover files the session said it updated. */
  saved?: string[]
  /** The session called ready_to_compact and was accepted. */
  isReady?: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'denubis-hook-compact-nag': { loops: Shaped<Record<string, CompactNagLoop>> }
  }
}
