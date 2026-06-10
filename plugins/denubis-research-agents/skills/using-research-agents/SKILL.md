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

When research involves academic papers, technical standards, or scholarly sources, follow this protocol. The user is an academic -- proper citations and DOIs are non-negotiable.

### Step 1: Build a bibliography

The research agent searches for relevant papers and produces a bibliography. For each paper:

```
Author(s). (Year). Title. *Journal/Venue*, volume(issue), pages.
https://doi.org/10.xxxx/xxxxx

Access: Open access / Institutional access required
curl: curl -L -o docs/papers/author-year-slug.pdf "https://doi.org/10.xxxx/xxxxx"
      (only if open access)
```

**Requirements:**
- Full citation (author, year, title, journal/venue, volume, pages)
- DOI as a URL (`https://doi.org/...`), never bare (`DOI: 10.xxxx`)
- Access note (open access or institutional)
- `curl` command if open access (so the human can fetch without browser)

### Step 2: Human fetches PDFs

Present the bibliography to the human. They fetch papers via DOIs -- institutional access, library proxies, or open access. PDFs go into `docs/papers/` (which should be gitignored).

**Do not** try to fetch papers yourself. **Do not** summarise based on abstracts alone. **Do not** route around access restrictions.

### Step 3: Agent reads full paper

Once PDFs are available, an agent reads the FULL paper -- not the abstract, not a web summary, the actual document. Use the Read tool on the PDF.

### Step 4: Agent writes discussion

For each paper read, write a discussion file:

```
docs/papers/{author-year-slug}.md
```

**Format:**

```markdown
# {Author} ({Year}) -- {Short Title}

**Full citation:** {complete citation with DOI URL}

## Summary
{What the paper argues, in 2-3 paragraphs}

## Key Claims
{Numbered list of the paper's main claims or contributions}

## Relevance
{How this paper relates to the current work -- be specific}

## Limitations
{What the paper doesn't cover, methodological concerns, scope constraints}

## Quotes
{Direct quotes with page numbers for anything you might cite}
```

### Anti-patterns

| Anti-pattern | Why it's wrong | What to do instead |
|--------------|---------------|-------------------|
| Citing a paper from its abstract | You don't know what it actually says | Build bibliography, human fetches, read full paper |
| "Based on Smith (2023)..." without reading | Academic misconduct dressed as research | Only cite papers you've read in full |
| Summarising web summaries of papers | Telephone game -- errors compound | Read the primary source |
| Skipping DOIs | DOIs are permanent; URLs rot | Always include DOI URL |
| Bare DOI format (`DOI: 10.xxxx`) | Not clickable, harder to use | Use `https://doi.org/10.xxxx` |

### When this protocol applies

- Any time a research agent finds academic papers relevant to the work
- When the user asks for scholarly sources or citations
- When design decisions need theoretical grounding (e.g. Popper, Lakatos, Haraway references in other skills)
- When evaluating claims that reference academic literature

### When this protocol does NOT apply

- Looking up API documentation (just use internet-researcher)
- Finding blog posts or tutorials (not academic sources)
- Stack Overflow answers and GitHub issues (not scholarly)
