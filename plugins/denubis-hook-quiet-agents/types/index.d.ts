// Agent key -> hash of the last notice body seen under that key.
export type NoticeHashes = Record<string, string>

// What the main conversation has heard from its teammates, each named as the
// mailbox's `origin.teammate` stamps it: verified, or a name this session's
// agent list holds.
export type TeammateReports = {
  // Teammate -> true once a non-idle message from it reached the main
  // conversation, or its own send to the main conversation was delivered;
  // the key is removed when the main conversation next sends it a message.
  reported: Record<string, true>
  // Teammates whose idle notice was consumed and that the main conversation
  // has not messaged since: the names the status line shows. Sorted, no
  // repeats.
  idle: readonly string[]
  // Teammates whose idle notice was consumed since the last prompt.submit:
  // named once in that prompt's context, then cleared. In arrival order, no
  // repeats.
  pending: readonly string[]
  // The ids of the agents a main-loop turn end has named for the reminder,
  // in the order named, no repeats. A turn end names only agents not in this
  // list, and the status line names each listed idle agent in it. An id
  // leaves it when the main conversation next sends that agent a message, so
  // its next stop is named again.
  nudgedIds: readonly string[]
}

// The ids of the agents the person muted with `/quiet-agents mute`, in the
// order muted, no repeats. An id leaves it at `/quiet-agents unmute`, or once
// its agent is stopped: at a main-loop turn end whose agent list lists it as
// `killed` or no longer holds it.
export type MutedAgents = readonly string[]

// An agent a turn end named, by its id and the name the reminder gives it.
export type NoteEntry = { id: string; name: string }

// The agents a main-loop turn end named that the reminder has not yet named
// to the model, in the order named, no repeated id. An entry leaves when the
// reminder names it on a message that went in, or at a main-loop turn end
// whose agent list no longer holds its id or whose record (`nudgedIds`) no
// longer does.
export type ReminderNote = readonly NoteEntry[]

declare module 'claude-code' {
  interface PluginState {
    'denubis-hook-quiet-agents': {
      lastNotice: Shaped<NoticeHashes>
      reports: Shaped<TeammateReports>
      muted: Shaped<MutedAgents>
      note: Shaped<ReminderNote>
    }
  }
}
