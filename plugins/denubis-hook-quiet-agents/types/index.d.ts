// Agent key -> hash of the last notice body seen under that key.
export type NoticeHashes = Record<string, string>

// What the main conversation has heard from its teammates, each named as the
// mailbox's verified `origin.teammate` stamps it.
export type TeammateReports = {
  // Teammate -> true once a non-idle message from it reached the main
  // conversation; the key is removed when the main conversation next sends
  // it a message.
  reported: Record<string, true>
  // Teammates whose idle notice was consumed and that the main conversation
  // has not messaged since: the names the status line shows. Sorted, no
  // repeats.
  idle: readonly string[]
  // Teammates whose idle notice was consumed since the last prompt.submit:
  // named once in that prompt's context, then cleared. In arrival order, no
  // repeats.
  pending: readonly string[]
  // The names found at the last main-loop turn end: idle teammates and every
  // idle, done or failed listed agent. Sorted, no repeats. A turn end nudges
  // the model only when its names differ from these; an empty set clears
  // them, so the same agents appearing again are named again.
  nudged: readonly string[]
}

declare module 'claude-code' {
  interface PluginState {
    'denubis-hook-quiet-agents': {
      lastNotice: Shaped<NoticeHashes>
      reports: Shaped<TeammateReports>
    }
  }
}
