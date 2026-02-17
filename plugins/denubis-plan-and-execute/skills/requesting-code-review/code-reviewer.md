# Code Review Task

Review the diff between BASE_SHA and HEAD_SHA. The diff is your primary review surface — do not audit unchanged code.

## Scope

**What was implemented:** {WHAT_WAS_IMPLEMENTED}

**Description:** {DESCRIPTION}

**Requirements/Plan:** {PLAN_REFERENCE}

## Git Range

**Base:** {BASE_SHA}
**Head:** {HEAD_SHA}

```bash
git diff --stat {BASE_SHA}..{HEAD_SHA}
git diff {BASE_SHA}..{HEAD_SHA}
```

Start with these commands. Follow your review process from there.
