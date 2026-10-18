# Practices enforced by command

Lint and type gates catch defects in code. These failures pass them:

- tests that replace the code they claim to test;
- tests that check a sentence exists;
- error handlers that replace the real cause with one fixed message;
- CI that blocks merges forever, or turns green when re-run;
- local hooks so slow that people skip them;
- parallel work that collides on shared files and shared Git state;
- pins that rot unnoticed;
- lessons that live only in a document.

Each section states the rule, why it holds, what `scripts/verify-practices.py`
refuses, and what stays review work. All three workflows route here; the
templates make a new project comply from its first commit.

## Run the check

```console
python <package-root>/scripts/verify-practices.py --root . --rules AGENTS.md
python <package-root>/scripts/verify-practices.py --root . --watch
```

It needs Python 3.12+ and only the standard library. It reads the tree and
today's date, never writes, and never runs project code. It skips generated
and vendored directories (`node_modules`, `dist`, `build`, `target`, `vendor`,
virtual environments) and nested Git repositories, such as a pinned checkout
of this package in CI.

| Exit | Meaning |
|---|---|
| 0 | Every check ran and nothing was refused |
| 1 | Refused practices are listed by file, line, and check |
| 2 | The root, `upstreams.json`, or the pitfalls register cannot be read |

A project with no code files, no `upstreams.json`, or no pitfalls register
fails: missing input is never a pass. `--watch` asks each watched upstream for
its latest release and exits 1 when one moved since the last review; a failed
query exits 2. `--format json` emits the same findings for tooling.

## Tests run real code

Tests exercise real code only. No mock, stub, or spy replaces behavior. No
fake server answers with hand-written responses. No fake CLI, fake timer, or
in-memory stand-in replaces a store, keyring, or filesystem.

A stand-in needs no mocking library. A class written in the test that
implements a dependency's interface, a function or namespace passed where the
real client goes, a port scripted to return canned answers, and a local server
started by the test all pretend to be a dependency. Each is a double, and each
is refused like one.

A double encodes what someone believed the dependency does. The test then
passes against a world that does not exist, and keeps passing after the real
dependency changes: the service renames a field, the CLI changes its exit
code, the store rejects a value. Users meet the failure first.

The outside world is tested live, or not at all. Never test it through a
recording, a cassette, a fixture of its replies, or a local fake server. A
recording is a stand-in too: it keeps answering the old way after the service
changes, so the test stays green while users fail. A test that reaches an
outside service fails when the service is unreachable; it never skips.

When code cannot be tested without a double, change the code. Move decisions
out of the I/O path, so tests call them directly with inputs they construct to
exercise the code's own rules, such as malformed and boundary values. Exercise
the I/O itself against the real dependency in an integration run: a real
database engine in a disposable directory, the real CLI, the real API. Property
and fuzz generators are unaffected: they explore inputs to your own code for
invariants rather than standing in for what an outside system said.

| Check | Refuses | Allowance |
|---|---|---|
| `mock` | `unittest.mock`, `mock`, `pytest-mock` and `mocker`, `monkeypatch.setattr`; `vi`/`jest` `mock`, `fn`, `spyOn`; Sinon, testdouble; Moq, NSubstitute; mockall; gomock, testify `mock`; Mockito; Pester `Mock`; `__mocks__` | none |
| `fake-timer` | freezegun, time-machine, `useFakeTimers`, `@sinonjs/fake-timers`, `FakeTimeProvider`, fake Go clocks | none |
| `fake-server` | responses, respx, httpretty, `BaseHTTPRequestHandler` subclasses in tests, nock, msw, fetch-mock, `MockAgent`, WireMock, `httptest` or `createServer` with an inline handler | none |
| `stand-in` | fakeredis, mongomock, moto, pyfakefs, memfs, mock-fs, redis mocks, fake-indexeddb | none |
| `hand-written-double` | In test code, a class, struct, record, or object named `Fake…`, `Stub…`, `Mock…`, `Spy…`, `Dummy…`, `InMemory…`, `Scripted…`, or `Canned…`; a Python function, lambda, or `SimpleNamespace` bound to such a name; a JavaScript-family function or class bound to one | reviewed |

These apply to code and to dependency manifests (`package.json`,
`pyproject.toml`, requirements files, `Cargo.toml`, `.csproj`, `go.mod`): a
mocking library that is installed gets used.

## Tests that can fail a user

A test fails when a user would be harmed. A test that only checks that text, a
key, or a file exists is not a test: the product can break completely while it
passes. Assert the behavior a user depends on, through the product's real
entry point.

Write fewer, meaningful tests. A test per rule, per finding, or per checklist
item multiplies maintenance and still misses the behavior between items. Add
a case to the behavior's table-driven test instead.

Prove every new test and gate fires with the [red-drill procedure](RED-DRILLS.md).
Wait for the condition the test needs, never for a fixed delay. Keep the
repository's default timeouts; a raised timeout hides slow setup until it
grows past the new limit.

A UI change gets one small local look. CI runs no screenshot or frame
comparison: pixel diffs fail on fonts, drivers, and anti-aliasing, and teach
people to re-baseline instead of looking.

The proof that a product works is real use of the built or packed product.
Make claims in the README, changelog, help, and release notes only after that
use. A false claim is fixed in the code, never by rewording it.

| Check | Refuses | Allowance |
|---|---|---|
| `text-existence` | A Python or JavaScript-family test that only reads or lists files and asserts presence (`in`, `toContain`, `toMatch`, `toHaveProperty`, truthiness) | reviewed |
| `one-off` | Three or more tests in a file whose bodies differ only in literal values; a test named after a numbered finding, item, checklist entry, rule, lesson, pitfall, issue, ticket, or bug | reviewed |
| `fixed-delay` | `time.sleep`, `waitForTimeout`, a sleeping `setTimeout` promise, `Thread.Sleep`, `time.Sleep`, `Start-Sleep` in tests; `sleep` in workflow steps | reviewed |
| `timeout-override` | `@pytest.mark.timeout`, `jest.setTimeout`, `this.timeout`, `testTimeout`, a per-test timeout argument | reviewed |
| `rerun` | Retry and re-run settings in test code, runner configuration, package scripts, and workflows (`retries`, `--reruns`, `retryTimes`, flaky markers, retry actions, `gh run rerun`) | none |

## Errors name their cause

An error message names what actually went wrong. A handler that catches every
error and answers with one fixed sentence, such as "not available", turns a
usage limit, a network failure, and a bug into the same message. The user
retries what cannot succeed, and the maintainer debugs the wrong layer.

A handler that catches everything keeps the cause: it re-raises, chains the
caught error (`raise … from error`, `new Error(…, { cause })`, `%w`), logs it
with its trace, or includes it in the message. Catch the specific error you can
explain when you want a specific message. A handler that hides internals from
an outside caller still records the cause where the maintainer looks.

| Check | Refuses | Allowance |
|---|---|---|
| `error-cause` | In product code, a catch-all handler that never uses the caught error and raises a new one or emits text: Python bare, `Exception`, and `BaseException` handlers, including `from None`; every JavaScript-family `catch` and arrow `.catch` callback; C# `catch` and `catch (Exception)`; Java and Kotlin `Exception` and `Throwable`; C++ `catch (...)` and `std::exception`; Go `if err != nil` blocks; Rust `map_err` with a discarded argument | reviewed |

The Python template's Ruff rules `BLE001` and `B904` overlap this check; the
check also covers the other languages, and projects without that template.

## Hosted CI is the merge gate

Hosted CI is the gate for merges and releases, and it needs no secret or key:
forks and merge queues run it with read-only access. Publishing credentials
belong to tag- or dispatch-triggered release jobs, never to a merge gate.

A check is green on its first run. A red check is never re-run into green;
find the cause. A re-run that passes leaves the defect in place, now hidden.

Every required check reports on every change. A workflow skipped by a path or
branch filter leaves its required check
[Pending, which blocks the merge](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
A docs-only change is then blocked forever. Skip expensive work inside the
job instead, so the check still reports.

Design throughput in. Size runner capacity to the contributors and agents
working in parallel. A strict "branch must be up to date before merging" rule
serializes every merge behind one CI run each. A
[merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
gives the same protection without that queue of re-runs, and requires
workflows to run on `merge_group`. Use merge trains where the host offers
those instead of queues. Declaring `merge_group` is harmless before a queue is
enabled.

Local gates stay fast enough to run on every change: format, lint, typecheck,
build, and only the test suites the change touches, which means the
integration suite when it touches a hub file that many modules import. Hosted
CI is the full gate and runs every suite. A local hook that runs the whole
suite on every commit gets skipped with `--no-verify`, and then checks nothing.

Set `timeout-minutes` on every job from one repository default, as a ceiling
for a hung runner. Never raise it to make room for slow setup.

| Check | Refuses | Allowance |
|---|---|---|
| `ci-secret` | `secrets.*` other than `GITHUB_TOKEN`, or `secrets: inherit`, in a workflow triggered by `pull_request`, `pull_request_target`, or `merge_group` | none |
| `ci-merge-group` | A `pull_request` workflow without `merge_group` | reviewed |
| `ci-path-filter` | `paths` or `paths-ignore` on a merge-gate trigger | reviewed |
| `ci-continue-on-error` | `continue-on-error: true` in a merge gate | reviewed |
| `ci-timeout` | A job without `timeout-minutes` (reusable-workflow calls excepted) | reviewed |
| `local-full-suite` | A test runner started with options only, so it runs the whole suite: in a `.pre-commit-config.yaml` hook with `pass_filenames: false` or `always_run: true`, a Git hook script under `.husky/` or `.githooks/`, or a lefthook configuration | reviewed |

[`templates/ci/quality.yml`](../templates/ci/quality.yml) is a merge gate in
this shape.

## Parallel work

Several contributors, people or agents, change one repository at once. Work
stays parallel only while each change is small, owns its files, and touches no
state that another worktree depends on.

Cut work into small tasks with one outcome each and an observable "done": a
command, a test, or a behavior anyone can check. Order each task so a first
result shows early, while a wrong direction still costs minutes. Finish a task,
merged or explicitly abandoned, before starting the next: half-finished work
on several branches conflicts with everything and proves nothing. Merge small
and often; a change that waits for days drifts from its base and conflicts with
every change merged meanwhile. When several finished changes must ship
together, integrate them on one release-candidate branch and prove them there
together with the full gate.

A file that every change edits, such as a plan, a changelog, or an index,
conflicts between every pair of parallel changes. Split it into per-item files
(a plan per work unit, a changelog fragment per change, a file per registry
entry) and generate the combined file with a script, in CI or at release. Tools
such as towncrier, Changesets, and scriv do this for changelogs. Nobody
hand-edits the generated file.

Run parallel work in separate Git worktrees, one branch each. Never use
`git stash`: every worktree of a repository shares one stash list, so a `pop`
in one worktree can apply another's work, and a `drop` or `clear` loses it.
Commit unfinished work to its own branch instead. Never check out the shared
base branch (`main`, `trunk`, `develop`) in a worktree: Git lets a branch be
checked out in only one worktree, so it blocks the primary checkout and
invites commits straight onto the base. Create a branch with
`git worktree add -b <branch> <path> <base>`, or use `--detach` for a
read-only build.

| Check | Refuses | Allowance |
|---|---|---|
| `git-shared-state` | `git stash` other than `list` and `show`, and `git worktree add` that checks out `main`, `master`, `trunk`, or `develop` without `-b` or `--detach`: in shell scripts, Git hooks, workflow steps, task runners (`Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `.pre-commit-config.yaml`), PowerShell, and commands that Python or JavaScript-family code starts | reviewed |

## Upstream currency

Keep every pinned version in one place from day one: `upstreams.json`. Update
bots cover lockfile ecosystems. They do not cover a CLI downloaded in CI, an
API or protocol version a client sends, or a data or schema snapshot. Those rot
silently until the upstream removes them.

```json
{
  "schema_version": 1,
  "upstreams": [
    {
      "name": "gitleaks",
      "kind": "cli",
      "pinned": "8.30.1",
      "used_in": [".github/workflows/ci.yml"],
      "watch": {"type": "github-releases", "repository": "gitleaks/gitleaks"},
      "reviewed": "YYYY-MM-DD",
      "latest_seen": "8.30.1",
      "max_age_days": 30,
      "hold": null
    }
  ]
}
```

`kind` is one of `runtime`, `sdk`, `cli`, `tool`, `action`, `protocol`, `api`,
`snapshot`, or `service`. A `watch` is `github-releases` with an
`owner/name` repository, or `manual` with an https URL for a changelog or
release page. A `hold` is `{"reason": ..., "until": "YYYY-MM-DD"}`. Unknown fields,
duplicate keys, and future dates are input errors.

The staleness gate runs in the merge gate, offline and deterministic:

| Check | Fails when |
|---|---|
| `upstream-pin-drift` | The pinned string is missing from a `used_in` file: the one place and the code disagree |
| `upstream-review-overdue` | `reviewed` is older than `max_age_days`: nobody looked at releases or changelogs |
| `upstream-behind` | `latest_seen` differs from `pinned` with no hold |
| `upstream-hold-expired` | A hold's end date passed |

[`templates/ci/upstream-watch.yml`](../templates/ci/upstream-watch.yml) runs
`--watch` weekly and opens one incorporation issue when a release appears. A
detected change is incorporation work at once: adopt it, or record a hold with
a reason and an end date, then update `latest_seen` and `reviewed`.

## Pitfalls register

Keep a pitfalls register from day one, in the canonical rules file. Every
entry names the code that fails if the pitfall returns: a test, a gate script
that CI runs, or a check of this command. A rule enforced by a document, a
skill, or a suggestion is read once and then forgotten.

````markdown
```pitfalls-register
{
  "schema_version": 1,
  "pitfalls": [
    {
      "id": "PIT-1",
      "pitfall": "A path-filtered required check blocked docs-only pull requests",
      "rule": "Merge-gate workflows run on every change",
      "enforced_by": [{"check": "ci-path-filter"}, {"path": "tests/test_ci.py"}]
    }
  ]
}
```
````

| Check | Fails when |
|---|---|
| `register-missing` | The rules file has no register block |
| `register-unenforced` | An entry names nothing, a document, a missing file, a script that no workflow or gate runner (`.pre-commit-config.yaml`, `package.json`, `Makefile`, `justfile`, `Taskfile.yml`, `tox.ini`, `noxfile.py`, `pyproject.toml`) runs, or an unknown check |

## Allowances

A reviewed exception is a comment on the finding's line or the line above it:

```python
# verify-practices: allow fixed-delay -- the server documents a fixed 2 s backoff
time.sleep(2)
```

The reason after `--` is required. Only the checks marked "reviewed" above
accept one. An allowance on any other check is refused, an allowance with no
matching finding fails as stale, and accepted allowances are listed in every
report so they stay visible.

## What the command cannot see

The checks match imports, calls, names, and workflow text; they do not run
the tests. Test shape is analyzed for Python and the JavaScript family only. A
fake CLI on `PATH`, a saved fixture of an outside service's replies, a manual
re-run in the CI interface, a screenshot comparison, and a process rule built
into the product are found by review. A clean run proves only that these
forms are absent. Red drills and real use of the built product prove that the
tests and the product work.

These forms also stay review work:

- A hand-written double with a neutral name, an object literal or dictionary
  passed in place of a dependency, a stand-in defined in product code and
  imported by tests, and a test-started server whose handler is defined
  elsewhere.
- A narrow handler that still merges different causes into one message, a
  cause dropped by code outside a handler (a returned sentinel error, a
  logged string instead of the error), and handlers in PowerShell, shell, and
  other languages not listed above.
- Task size, an observable "done", finishing before starting, and merge
  cadence. These are plan and review judgment.
- Which files every change edits. That is a property of the history, not of
  one tree, so the command cannot tell a hot file from a quiet one.
- Git commands typed by hand or run from prose instructions, `git checkout` or
  `git switch` of a base branch inside an existing worktree, and base branches
  with other names.
- Which suites a change touches. That follows the import graph; a hook that
  selects a suite that is still too large, and hooks declared inside
  `package.json`, are not recognized.
