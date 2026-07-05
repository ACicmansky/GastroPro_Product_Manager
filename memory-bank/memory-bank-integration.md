# Memory Bank — Usage Rules

The memory bank is the project's persistent knowledge base. It must be self-contained: plain markdown, no references to any specific AI tool, readable by any assistant or human.

## Files

| File | Contains | Update when |
|------|----------|-------------|
| `projectbrief.md` | Scope, core requirements | Scope changes (rare) |
| `productContext.md` | Why the project exists, user goals | Product direction changes (rare) |
| `activeContext.md` | Current state, recent changes, active decisions | After every significant work session |
| `systemPatterns.md` | Architecture, key design patterns | Architecture changes |
| `techContext.md` | Stack, file structure, integrations | Stack/structure changes |
| `progress.md` | Feature completion history | Feature completed |
| `journal/` | One file per significant session: `YYYY_MM_DD_topic.md` | Significant fix/feature/refactor |

Hierarchy: `projectbrief` grounds everything → `productContext` / `systemPatterns` / `techContext` inform → `activeContext` reflects now → `progress` records history.

## Reading (keep it cheap)

- **Before non-trivial work**: read `activeContext.md` only.
- **On demand**: read the specific file relevant to the task (architecture question → `systemPatterns.md`, stack question → `techContext.md`, etc.).
- Do **not** read all files for every task.

## Writing

- After significant changes: update `activeContext.md` (rewrite stale parts, keep it short — history belongs in `journal/`) and add a journal entry.
- Journal entry format: Context → what was done → verification → deferred items. Facts over narrative.
- Update other files only when their subject actually changed. Fix stale content on sight.
- Keep `activeContext.md` under ~50 lines; prune superseded "recent changes" into the journal.
