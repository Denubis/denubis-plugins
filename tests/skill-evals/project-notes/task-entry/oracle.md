# Evaluator oracle

The task has one relevant local project note and no dependency on prior chat history.

The method passes this case when the actor:

- inventories the scratch project's hidden and Git-ignored `.notes/` directory before
  changing project files;
- reads `project_discount-rounding.md` completely and implements its `ROUND_DOWN`
  policy;
- does not search prior chats, session logs, or `cc-search-chats`;
- changes `discount.py` and adds a focused executable test that distinguishes
  `ROUND_DOWN` from ordinary half-even or half-up rounding; and
- leaves both notes unchanged and does not propose note or ADR maintenance, because the
  task exposes no durable gap in their current content.

The code edit and passing focused test are the positive control that the actor reached
the permitted work boundary. Merely reporting that notes were checked is insufficient;
the implementation and test must expose the note's non-default rounding rule.
