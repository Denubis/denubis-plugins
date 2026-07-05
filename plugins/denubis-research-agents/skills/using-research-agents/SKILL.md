---
name: using-research-agents
description: Use when dispatching research agents - covers agent selection across internet/codebase/combined/remote-code, academic research protocol with DOI citations, and anti-patterns
user-invocable: false
---

# Using Research Agents

## Agent Selection

| Agent | Model | Use When |
|-------|-------|----------|
| `internet-researcher` | Haiku | Need current API docs, library comparisons, community consensus. External info only |
| `codebase-investigator` | Haiku | Need to understand existing code, verify assumptions, find patterns. Local info only |
| `combined-researcher` | Haiku | Need both external and local info together (e.g. "do we use Stripe? what's the current API?") |
| `remote-code-researcher` | Haiku | Need to read actual source code of external libraries. Clones repos to temp dir |

**Decision flow:**

```
Need external info? ----No----> codebase-investigator
       |
      Yes
       |
Need local info too? ---No----> internet-researcher
       |
      Yes
       |
Need to read library
source code? -----------Yes---> remote-code-researcher
       |
      No
       |
       v
combined-researcher
```

**Common mistakes:**

| Mistake | Fix |
|---------|-----|
| Using combined-researcher for pure web search | Use internet-researcher (simpler, faster) |
| Using internet-researcher when answer is in codebase | Use codebase-investigator |
| Guessing library internals | Use remote-code-researcher to read the actual code |
| Running multiple agents sequentially when combined would do | Use combined-researcher |

## Academic Research Protocol

The user is an academic, so citations and DOIs are non-negotiable, and a claim is
citable only once its primary source has been read in full. Reading happens
through the user's Zotero corpus and the `using-bibliography` pipeline, never from
an abstract or a web summary. Discovery's job is therefore to *identify* papers so
they can be loaded into Zotero and read, not to fetch, summarise, or stockpile
them from the web. The flow has three stages: identify, load, read.

### Stage 1: Identify (the research agent's job)

A research agent (usually `internet-researcher`) searches for relevant work and
returns, for each candidate, a locator the loader can act on:

- a DOI as a URL (`https://doi.org/10.xxxx/xxxxx`), preferred
- failing a DOI, another stable identifier (ISBN, PMID, arXiv id)
- only as a last resort, an unstable locator (a landing-page URL, or a plausible
  author, title, and year), flagged as unverified so a human can find and add it

Give the full citation and a one-line reason each candidate is relevant, then
stop. Do not fetch the PDF, do not write a summary from the abstract, and do not
build a parallel `docs/papers/` library, because the corpus is Zotero and a
second pile of PDFs outside it only invites hand-rolled extraction.

### Stage 2: Load into Zotero (orchestrator, behind confirmation)

The identified papers are brought into Zotero with their PDFs and then rendered.
The mechanics live in `using-bibliography` ("Fetching a missing paper"); in brief:

- **Already in the corpus?** Resolve first with `resolve.py`. A present paper is
  loaded, so skip fetching it: the fetch endpoint does not dedup, and a second add
  creates a duplicate.
- **Fetchable?** Use `fetch.py` (the `zotero-api-plus` path). It writes to the
  library, so it HALTs for explicit confirmation of the exact items and target
  collection, then attaches the PDF and renders.
- **Paywalled with no open-access copy?** `fetch.py` returns metadata only. The
  Zotero connector with an institutional session is the path, taken by the human
  or a human-supervised step. Wait for the paper to appear, then render.

Loading writes to the user's library, so it is never silent and never inferred
from an earlier "research this" instruction.

### Stage 3: Read (the using-bibliography fan-out)

Once papers are in Zotero with rendered markdown, read them with the reader
fan-out in `using-bibliography` ("Fanning out readers over a rendered corpus"):
the orchestrator resolves and renders each paper once, then dispatches one reader
per paper given only the rendered markdown path. Page-keyed citations come from
the markers in the rendered text and are verified with `blockquote.py`.

### Anti-patterns

| Anti-pattern | Why it's wrong | Instead |
|--------------|---------------|---------|
| Citing a paper from its abstract or a web summary | You do not know what it says, and the telephone game compounds errors | Load it into Zotero, render it, read the primary source |
| "Based on Smith (2023)..." without reading the full text | Academic misconduct dressed as research | Cite only papers read in full via the rendered text |
| Fetching PDFs into a `docs/papers/` dump and reading them ad hoc | Forks a second corpus outside Zotero and invites hand-rolled extraction | Load with `fetch.py`, read the render |
| Reaching for `pdftotext` or another extractor | The render cascade already produced better text | Read the rendered markdown; PDF to text is always the cascade |
| Skipping DOIs or writing them bare (`DOI: 10.xxxx`) | DOIs are permanent and a bare one is not clickable | Always `https://doi.org/10.xxxx` |
| Routing around access restrictions for a paywalled PDF | Not the agent's call to make | Identify it and leave the connector and institutional session to the human |

### When this protocol applies

- Any time research surfaces academic papers relevant to the work.
- When the user asks for scholarly sources or citations.
- When a design decision needs theoretical grounding (Popper, Lakatos, Haraway, and the like).
- When evaluating claims that reference academic literature.

### When it does NOT apply

- API documentation, blog posts, tutorials, Stack Overflow, or GitHub issues. Those are not scholarly sources, so use `internet-researcher` directly without this protocol.
