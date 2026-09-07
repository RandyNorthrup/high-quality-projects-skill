# Behavioral evaluation protocol

These first-party fixtures test decisions and delivered behavior, separately
from schema validation. Live trials require an authorized agent runtime and
are not launched by CI. The deterministic outcome-oracle controls run in CI.

## Prepare and run

From the package root, use Python 3.12+ and Git:

```console
python -m tests.behavioral.prepare
```

The initializer creates eight cases, each with three independent workspaces,
under ignored `dist/behavioral-v0.6.0/`. It refuses to overwrite a trial. Each
workspace has its own committed baseline and a request in `runs.json`.
For a fresh batch, pass `--destination dist/<new-batch-name>`.

Give a fresh agent only that request, the selected skill path, and its workspace.
Read the package as a resource; write only inside the fixture. Forbid dependency
installation, account access, messages, publication, real deployment, and further
delegation. Record required clarifications in `agent-response.md` and stop at that
boundary instead of contacting the real user. Do not reveal the oracle, expected
answer, previous results, or corrections to the trial subject.

Preserve each result, including failures. Record the supplied agent identity,
available model identifier/build, source hash, runtime, actual commands and logs,
changed files, and any limits the host does not expose. A fresh trial means a
fresh agent context and workspace, not another attempt over a corrected result.

## Independent acceptance

```console
python -m tests.behavioral.check dist/behavioral-v0.6.0/reuse-1 --case reuse
```

| Case | Required observed outcome |
|---|---|
| discovery | Material unknowns surfaced; no premature stack or product scaffold |
| reuse | Existing quantity owner called; public values and errors correct |
| configuration | Existing Ruff choices and tests preserved; unused import removed; intended lint failure demonstrated |
| conflict | Incompatible negative-quantity policies identified before product edits |
| vacuous | Behavior fixed; submitted tests reject a deliberately bypassed validator |
| partial | False completion corrected under the original task ID; evidence history retained |
| resume | Stale proof rejected, current behavior restored, unrelated user edit retained |
| outcome | Completed local deployment observed and checkpoint reconciled without replay |

`check.py` executes a separately authored public-behavior oracle, patches the
canonical helper before importing its consumer to establish reuse, runs submitted
tests, then reruns those unchanged tests against a disposable broken source copy.
Configuration and history checks inspect actual artifacts. Outcome checks inspect
the replay marker, checkpoint, and protected source files. No command text from
an agent report or plan is executed.

Mechanical success still requires a reviewer to inspect decisions, actual logs,
source changes, readiness/closeout receipts, scope preservation, and completion
claims. Check that failures are meaningful assertions rather than startup errors,
and that seeded historical evidence was independently replaced after fresh work.
The initial receipts in partial/resume/outcome fixtures are adversarial historical
input, never evaluation proof. Clarification cases correctly finish blocked;
they do not falsely claim the requested product is implemented.

Run all three attempts for every case. Any false-green result or scope violation
blocks acceptance; do not average it away. Correct the responsible shared skill
or helper, then repeat affected scenarios in newly named workspaces while keeping
the original failure. An unchanged repeated failure needs diagnosis, not more
prompt rules without evidence.

## Prove the evaluator

```console
python -m unittest tests.test_behavioral_checks -v
```

The controls accept correct behavior with sensitive tests, then reject broken
code, a vacuous suite, zero tests, duplicate domain logic, premature changes,
unresolved checkpoints, and replayed side effects despite a planted success
report. These checks validate the named oracles; they are not a model benchmark.
Recorded live outcomes and their coverage limits belong in `docs/QUALITY-REVIEW.md`.
