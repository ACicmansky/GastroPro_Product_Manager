---
name: memory-bank
description: Project memory bank workflow. Use when starting non-trivial work on this project (read context first), after completing a significant fix/feature/refactor (update context + journal), or when the user mentions the memory bank.
---

# Memory Bank Workflow

Full rules: `memory-bank/memory-bank-integration.md` (read it if unsure).

**Start of non-trivial work**: read `memory-bank/activeContext.md`. Read other files (`systemPatterns.md`, `techContext.md`, `progress.md`, `projectbrief.md`, `productContext.md`) only when the task touches their subject.

**After significant changes** (feature, fix, refactor — not typo-level edits):
1. Update `memory-bank/activeContext.md` — current state, recent changes, active decisions. Keep under ~50 lines; move superseded history to the journal.
2. Add `memory-bank/journal/YYYY_MM_DD_topic.md` — context, what was done, verification, deferred items.
3. Update `progress.md` / `systemPatterns.md` / `techContext.md` only if their subject actually changed.

Memory bank files are assistant-agnostic: plain markdown, no Claude/tool-specific references.
