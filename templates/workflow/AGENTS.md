# AGENTS.md

Revision: 1

How we work on this project: process rules for every contributor, person or
agent. What the product does lives in `PROJECT_BRIEF.md`; how confirmed scope
is delivered lives in `PLAN.md`. Never build a rule from this file into the
product.

Adapt this file to the project and keep it the one canonical rules file. Tool
adapters such as `CLAUDE.md`, `.cursor/rules/`, and
`.github/copilot-instructions.md` point here instead of copying it.

## Before each change

- Scan, reuse, then create. Search by path, symbol, behavior, and
  responsibility; extend the canonical implementation; record why new code is
  needed when nothing existing can serve.
- Before removing code a tool reports as dead, check unmerged branches and
  open plans. Unfinished work is finished, not deleted.

## Working in parallel

- Cut work into small tasks with one outcome, an observable "done", and an
  early first result. Finish a task before starting the next. Merge small and
  often; prove changes that ship together on one release-candidate branch.
- Never hand-edit a file that every change edits. Add a per-item file or
  fragment, and let the script that joins them write the combined file.
- Work in separate worktrees, one branch each. Never use `git stash`: every
  worktree shares one stash list. Never check out the shared base branch in a
  worktree.

## Code

- Error messages name the real cause. A handler that catches every error
  re-raises, chains, logs, or includes it; one fixed message never stands in
  for a usage limit, a network failure, and a bug alike.

## Tests

- Tests exercise real code only: no mocks, stubs, spies, fake servers, fake
  CLIs, fake timers, or in-memory stand-ins for stores and keyrings.
  A hand-written class, scripted port, or local server that pretends to be a
  dependency is a stand-in too, with or without a mocking library.
  The outside world is tested live, or not at all: never through a recording,
  cassette, fixture of its replies, or local fake server.
- A test fails when a user would be harmed. Checking that text, a key, or a
  file exists is not a test. Add a case to the behavior's table instead of a
  one-off test per rule, finding, or checklist item.
- Prove each new test and gate fires: break the code on purpose, see the named
  failure, restore byte-exact (hash compared), and see green again.
- Wait for conditions, never for fixed delays, and keep the default timeouts.
- A UI change gets one small local look. CI runs no screenshot or frame
  comparison.

## Checks and CI

- Before pushing, run format, lint, typecheck, build, only the suites that
  depend on a changed file, and `verify-practices`. A change to a shared hub
  file runs the integration suite. Hosted CI runs every suite.
- Hosted CI is the merge gate and needs no secret or key. A check is green on
  its first run; a red check is diagnosed and fixed, never re-run into green.
- Report a skipped, deferred, or failing check as exactly that.

## Claims and currency

- Make a claim in the README, changelog, help, or release notes only after
  real use of the built or packed product. Fix a false claim in the code, not
  by rewording it.
- Keep every pinned version in `upstreams.json`. When the watch reports a
  release, incorporate it or record a hold with a reason and an end date.

## Decisions

- When a decision is superseded, rewrite every design that applied it in the
  same change. The plan keeps the superseded record, not a stale design.

## Pitfalls register

Each pitfall this project has hit, with the code that fails if it returns: a
test file, a gate script that CI runs, or a `verify-practices` check. A rule
enforced only by prose is not enforced, and `verify-practices` refuses it.

```pitfalls-register
{
  "schema_version": 1,
  "pitfalls": []
}
```

## Rule amendments

Record each changed rule here: old and new wording, reason, authority, new
revision, and the work it affects. Re-check that work; never weaken a rule to
clear a finding.
