// One question for the person: the background a reader needs to answer it,
// and the question itself. Both are stored trimmed.
export type QuestionZoneEntry = {
  context: string
  question: string
}

// Every question not yet answered.
export type QuestionZoneQueue = {
  // Entries being checked, in the order asked; each leaves when its check
  // ends: for the end of `waiting` if the check passed, else for good.
  checking: readonly QuestionZoneEntry[]
  // The queue, in the order checks passed; the head is the next the band
  // hands over.
  waiting: readonly QuestionZoneEntry[]
  // Entries the band put into the prompt box that the person has not yet
  // sent, in the order taken. The person's next prompt settles them: an entry
  // whose quoted question it carries is answered and leaves; the rest go back
  // to the head of `waiting`, in this order. Taking an entry first returns any
  // here to the head of `waiting`, so it holds at most one.
  taken: readonly QuestionZoneEntry[]
}

declare module 'claude-code' {
  interface PluginState {
    'denubis-hook-question-zone': {
      queue: Shaped<QuestionZoneQueue>
    }
  }

  // The inputs of the two tools the plugin registers, as their schemas give
  // them, so a `tool.call` hook's `e` narrows on the tool's name.
  interface McpToolInputs {
    'mcp__denubis-hook-question-zone__ask': { context: string; question: string }
    'mcp__denubis-hook-question-zone__withdraw': { question: string }
  }
}
