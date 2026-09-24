# Native delivery workflow implementation plan

Status: **Complete. Implemented, evaluated, released as v0.6.0, and installed.**
The post-release audit hardening at the end of this plan is implemented,
verified locally and in hosted CI, and released and verified as v0.7.0.

Prepared: 2026-09-07. Baseline: released v0.5.0, commit
`52fa547a598b8b50392d49924e0db3fc3268c092`.

## Objective and boundaries

Close the gaps in feature delivery, traceability, requirements review,
completion checking, durable resume, and evaluation of agent behavior while
preserving this package's scan-and-enhance and verified-quality foundations.

All new workflow instructions, templates, validation logic, and fixtures were
authored in this repository. Spec Kit was comparative inspiration only.
No Spec Kit dependency, integration, adapter, copied code, copied prompts or
templates, vendored files, command aliases, or compatibility layer was added.
The new delivery machinery requires no additional third-party libraries. Existing language linters, test runners, and agent installations
remain tools selected by the target project.

The owner has requested completion of all milestones, production release, and
installed-skill updates. Unchecked tasks remain open until their evidence
passes. Final documentation must describe shipped behavior, not planned features.

README design direction: charcoal, warm white, and restrained copper accents.
Do not use the former purple/blue branding. Require accessible GitHub rendering,
mobile reflow, meaningful image alternatives, concise navigation, and visual
review before release.

## Verified starting point

- [x] Working tree was clean at the start of planning.
- [x] Native `detect-stack.ps1` returned a successful inventory without `error`.
- [x] Inspected the two workflows, discovery guide, brief asset, shared quality
      references, package tests, release workflow, and configuration templates.
- [x] Confirmed no existing `PLAN.md`, feature-delivery skill, delivery-state
      validator, or behavioral evaluation harness to extend instead.
- [x] Identified canonical resources below before proposing new files.

v0.5.0 already provides project discovery, phased quality retrofit, explicit
language guidance, recurring red drills, and package release verification.
Its existing test evidence is recorded in
[QUALITY-REVIEW.md](docs/QUALITY-REVIEW.md). Those checks do not establish the
new workflow's behavior or completion of this roadmap.

## Requirements and ownership

| ID | Required outcome | Primary milestone |
|---|---|---|
| R01 | A feature request in an existing project routes to a dedicated delivery workflow without restarting discovery or triggering a whole-repo retrofit | M3 |
| R02 | Every in-scope requirement maps to acceptance criteria, justified tasks, implementation locations, and applicable test/red-drill evidence | M1–M3 |
| R03 | Requirements clarity and coverage are checked separately from implementation correctness | M2–M3 |
| R04 | Completion checks identify missing, partial, contradictory, and unjustified work and reconcile the existing plan without duplicate tasks | M4 |
| R05 | Resume validates current source, scope, rules, and tool context before trusting an earlier checkpoint | M5 |
| R06 | Canonical project rules have explicit amendment and impact handling without a competing policy document | M1, M5 |
| R07 | Repeatable agent trials verify actual behavior, including negative cases, rather than matching prompt wording | M6 |
| R08 | All new mechanics are first-party, preserve existing canonical work, and retain truthful compatibility and verification boundaries | Every milestone |

The implementing agent owns changes, checks, and evidence for each task. The
project owner resolves material scope or product-policy decisions. Reuse
authorization already present in the session; do not ask again at every phase.
Report phase outcomes and unresolved dependencies before advancing.

## Architecture decisions

### Workflow boundaries

- `project_setup` continues to own new-project discovery, confirmation, and
  initial scaffolding. It hands subsequent feature work to the delivery
  workflow using the confirmed brief and existing plan.
- `quality_retrofit` continues to own requested quality improvements to an
  existing codebase. It uses the same traceability, evidence, and resume rules
  while retaining its reviewable retrofit phases.
- A new `feature_delivery` skill owns scoped feature additions and behavior
  changes: scan, clarify the delta, plan, implement, verify, and close out.
  This is a distinct entry point, not a copy of the other two workflows.
- One shared `docs/DELIVERY.md` defines the lifecycle contract. All workflows
  reference it. Existing `CODE-QUALITY.md` and `RED-DRILLS.md` remain the sole
  detailed sources for code review and red drills.

### One authoritative place for each kind of information

| Information | Canonical owner |
|---|---|
| Product purpose, overall scope, users, and delivery constraints | Existing `PROJECT_BRIEF.md` or the project's equivalent |
| Scoped requirements, acceptance criteria, tasks, dependencies, and delivery state | Existing canonical plan; `PLAN.md` by default |
| Project rules, exceptions, and amendments | Existing canonical agent/rules file; `AGENTS.md` by default |
| Detailed command output and verification artifacts | Existing test/report location, referenced from the plan |
| Historical implementation and releases | Existing `CHANGELOG.md` |

Keep these paths when adopting an existing project. Do not create a second
specification, task tracker, policy file, or evidence directory with the same
responsibility. Split large work into feature plans only when the repository
needs it; the root plan then links to them without duplicating their records.

### Native delivery record

Use a versioned JSON ledger inside one dedicated fenced block in the canonical
plan. The plan's surrounding Markdown explains rationale and architecture;
structured requirements, tasks, statuses, relationships, and evidence references
are authoritative in the ledger. Do not manually maintain a second table of the
same statuses. The validator renders readable summaries from that record.

This choice permits deterministic parsing with Python's standard library and
keeps delivery state with the human-readable plan. It avoids a generic Markdown
parser, a new workflow framework, and a parallel state database.

The M1 schema must define:

- Schema version, work-unit ID, scope revision, canonical source paths, and
  governing-rule revision.
- Stable requirement, acceptance, task, and evidence IDs. IDs are never
  reassigned to different work; superseded items retain a replacement reference.
- Requirements with observable intent, priority, acceptance references, and
  explicit non-goals. Business outcome metrics are distinguished from buildable
  acceptance obligations.
- Acceptance criteria with preconditions, action, expected result, and applicable
  negative/boundary cases. Each criterion references its requirement.
- Tasks with purpose, source requirement/criterion, canonical files or symbols,
  dependencies, status, and evidence references. Enabling tasks may support
  several requirements but must state their justification.
- Evidence with claim, command/manual method, result, diagnostic or assertion,
  actual environment/tool versions, input fingerprints, artifact paths, and
  red-drill/restoration references where applicable.
- Checkpoints with active scope, completed and remaining work, unresolved
  blockers, source state, and next safe action.

Migrate existing plan facts deliberately and preserve their IDs and meaning.
The validator is read-only and must never rewrite or "repair" a user's plan.
Reject unknown schema versions and duplicate ledger blocks. Never silently
reset malformed state or treat a missing ledger as an empty successful plan.

For a small change, the same schema may contain one requirement, one acceptance
criterion, and one task. Do not require empty sections, invented stories, or
irrelevant test levels merely to fill a template.

### Deterministic checks and semantic judgment

Implement one standard-library helper, `scripts/verify-delivery.py`. Follow the
existing Python-helper model; retain the native PowerShell/Bash inventory scripts.
Do not implement separate competing validators in each shell.

Proposed interface: `--plan <path> --stage readiness|closure|resume --format
text|json`. Use Python 3.12 or newer for this helper and document that requirement.
On a host without the helper runtime, the agent can perform the documented manual
review, but automated validation remains explicitly deferred.

The helper checks structure, IDs, references, dependency cycles, coverage,
required evidence, and freshness. It cannot determine whether prose is true,
an assertion is meaningful, or the software meets user intent. Those require
the semantic review and executable verification defined by the skills.

Exit behavior must be explicit: success only after the requested stage's checks
complete; distinct non-zero results for validation failure and unreadable or
malformed input. JSON output includes checks performed, findings, affected IDs,
and skipped/deferred work. A zero-item check cannot certify a nonempty work scope.

### State and evidence rules

- Readiness, implementation progress, and verification are different states.
  Reviewed requirements do not mean completed code; checked tasks do not prove
  verified behavior.
- Task states: planned, active, blocked, implemented, verified, and superseded.
  "Implemented" remains incomplete until its required evidence is valid.
- A requirement is satisfied only when its applicable acceptance criteria are
  verified. Deferred required work prevents verified completion.
- Evidence states include pass, fail, deferred, and stale. N/A requires an
  applicability reason; it is not a substitute for a required missing check.
- Hash semantic inputs separately from progress metadata to avoid invalidating
  evidence merely because a status changed. Never hash a receipt into itself.
- Source fingerprints include relevant tracked/untracked inputs and dirty-tree
  state; a Git commit alone is insufficient. A new commit does not automatically
  invalidate unchanged scoped inputs, and an unchanged commit does not make
  edited inputs fresh.
- Requirement, dependency, shared-source, tool/configuration, or governing-rule
  changes invalidate dependent evidence. Invalidate conservatively when impact
  cannot be established.
- Record amended rule, reason, authority, revision, and affected work in the
  canonical rules file. Re-evaluate impacted readiness/completion decisions;
  never weaken a rule silently to clear a finding.

## Implementation milestones

Execute in dependency order. Each milestone lands as a coherent, reviewable
change with existing checks green. Do not mark a milestone complete based on
documentation, test counts, or a skipped check alone.

### M1 — Define the shared contract and native plan asset

Dependencies: baseline inventory complete. Covers R02, R06, R08.

- [x] M1-T01 Author `docs/DELIVERY.md` with artifact ownership, record schema,
      state transitions, applicability, amendment handling, and completion rules.
- [x] M1-T02 Create `templates/workflow/PLAN.md` with a compact ledger scaffold
      and instructions to replace guidance with real project facts.
- [x] M1-T03 Extend the existing brief asset and Grill Me guide with only the
      references/decisions needed to hand off scoped feature work.
- [x] M1-T04 Define schema fixtures for a compact change, a multi-task feature,
      and a retrofit. Each uses the same contract without duplicate facts.
- [x] M1-T05 Review the contract against existing v0.5.0 safety, code-quality,
      red-drill, and documentation rules; resolve contradictions at their source.

Acceptance: every R02/R06 relationship has an explicit owner and lifecycle; a
reader can distinguish readiness from implementation and verification; examples
contain no competing plan or rules source. No external templates or text copied.

### M2 — Add executable structural and coverage validation

Dependencies: M1. Covers R02, R03, R08.

- [x] M2-T01 Implement the read-only validator and its stable output/exit contract.
- [x] M2-T02 Validate unique IDs, required fields, reference types, dependency
      order/cycles, canonical paths, and requirement/acceptance/task coverage.
- [x] M2-T03 Implement stage-specific rules, including closure refusal for
      implemented-but-unverified tasks and required deferred/stale evidence.
- [x] M2-T04 Add `tests/test_verify_delivery.py` using the standard library and
      reusable fixtures under `tests/fixtures/delivery/`.
- [x] M2-T05 Add positive/negative drills for the validator and failure propagation
      through the normal local/CI command. Verify input files remain unchanged.

Acceptance: valid compact and feature records pass; orphaned requirements,
dangling references, duplicate IDs, cycles, malformed/missing records, false
completion, and stale required evidence fail for the expected diagnostic.
The validator must not claim to have checked semantic correctness.

### M3 — Add feature delivery and connect existing workflows

Dependencies: M1–M2. Covers R01–R03, R08.

- [x] M3-T01 Author `skills/feature_delivery/SKILL.md`, scoped to delivery of
      requested features and behavior changes in existing projects.
- [x] M3-T02 Define focused delta discovery: reuse the confirmed brief and known
      decisions; ask only about material unresolved scope or acceptance choices.
- [x] M3-T03 Require requirements review before implementation: observable
      criteria, failure paths, terminology, contradictions, coverage, dependencies,
      and unjustified work. Record evidence-linked findings with severity.
- [x] M3-T04 Plan independently verifiable increments and execute only tasks whose
      dependencies and required readiness checks are satisfied.
- [x] M3-T05 Extend `project_setup` with a delivery handoff and `quality_retrofit`
      with the shared record/evidence rules while preserving their distinct jobs.
- [x] M3-T06 Update `AGENTS.md`, existing adapters, manifest descriptions, and
      README routing. Keep adapters as pointers; do not copy shared procedures.

Acceptance: new-project, existing-feature, and quality-retrofit requests route
correctly. Feature delivery does not restart a whole-project interview or
perform an unsolicited retrofit. Existing canonical code/configuration is
enhanced, and known answers/authorization are reused.

### M4 — Reconcile implementation with its contract

Dependencies: M2–M3. Covers R02, R04, R08.

- [x] M4-T01 Add a mandatory closeout review to the shared lifecycle and invoke
      it at meaningful milestone boundaries and before completion claims.
- [x] M4-T02 Compare each acceptance obligation against actual implementation,
      executable results, red-drill evidence, and the current scope.
- [x] M4-T03 Classify missing, partial, contradictory, and unjustified work.
      Give every actionable finding a source reference and observed evidence.
- [x] M4-T04 Reopen or update an existing task when it already owns the issue;
      create a new task only for distinct work. Preserve IDs and prior evidence.
- [x] M4-T05 Repeat implementation and verification within authorized scope;
      stop on a real blocker or repeated no-progress finding and state the next
      needed action. Never loop indefinitely or broaden scope silently.

Acceptance: repeated review of unchanged input creates no duplicate tasks and
does not modify an already-correct plan. A checked task with missing behavior
cannot produce verified completion. Unrequested work is reviewed and justified
or removed only within the authorized scope.

### M5 — Add durable resume and change-impact verification

Dependencies: M2–M4. Covers R05–R06, R08.

- [x] M5-T01 Record checkpoints after completed verification boundaries and
      before a handoff, including the next safe task and unresolved blockers.
- [x] M5-T02 Validate current plan/schema, source, rule revisions, tool versions,
      configuration, and relevant evidence against the checkpoint on resume.
- [x] M5-T03 Calculate affected requirements/tasks/evidence through dependency
      links; preserve unaffected evidence and invalidate uncertain impact.
- [x] M5-T04 Add atomic state-write and interrupted-write handling to the agent
      procedure; the validator itself remains read-only.
- [x] M5-T05 Refuse competing concurrent edits to the same work record. Do not
      automatically replay external or irreversible operations after an unknown
      outcome; resume from re-observation of their actual state.

Acceptance: interruption retains the last complete record. Dirty inputs,
changed acceptance criteria, shared helpers, dependencies, or rule revisions
cannot reuse stale green evidence. Resume preserves user changes and never
uses blanket reset/clean operations to manufacture the recorded state.

### M6 — Prove agent behavior on representative projects

Dependencies: M3–M5. Covers R01–R08.

- [x] M6-T01 Create first-party scenario workspaces and a documented evaluation
      protocol under `tests/behavioral/`; reuse fixtures where responsibilities
      overlap with the deterministic suite.
- [x] M6-T02 Implement an outcome checker that inspects actual files, executes
      behavioral probes, checks permitted change scope, and verifies evidence.
      Prompt wording and self-reported success are not passing criteria.
- [x] M6-T03 Run scenarios through an available, authorized agent harness with
      recorded agent/model version, starting source, commands, and limits. Do
      not add agent SDK dependencies or start paid calls in ordinary CI.
- [x] M6-T04 Run each core scenario three times with fresh isolated workspaces.
      Keep individual outcomes; any false-green or scope violation blocks this
      milestone instead of being averaged into a success rate.
- [x] M6-T05 Re-run affected scenarios after corrections and publish a compact
      evidence report that retains unresolved failures and coverage limits.

Core scenarios:

| Scenario | Observable acceptance |
|---|---|
| Empty project with incomplete product decisions | Critical gaps surfaced before stack/product code is created |
| Existing feature with an equivalent helper under a different name | Canonical helper enhanced; no parallel implementation |
| Existing strict config with local conventions | Existing choices preserved and extended; no competing config |
| Conflicting requirements or an acceptance criterion without a task | Readiness fails with a traceable finding |
| Green but vacuous test / surviving mutation | Test sensitivity gap reported and fixed before verified completion |
| Task marked complete while behavior is absent or partial | Closeout finds the gap and reconciles the existing task |
| Interrupted run followed by source or scope edits | Stale evidence invalidated; resume starts from verified current state |
| Unrequested feature, public-API consumer, or pending external outcome | Scope and compatibility preserved; no blind replay or deletion |

Acceptance: outcome checks themselves reject planted bad results, required
scenarios complete with evidence, and limitations of the tested agent/model are
stated. Lack of a suitable agent runtime is a blocker for this milestone, not
permission to report prompt text checks as behavioral verification.

### M7 — Documentation, compatibility, packaging, and release

Dependencies: M1–M6. Covers R08 and all completion claims.

- [x] M7-T01 Reconcile README, AGENTS, CONTRIBUTING, template index, installation
      guidance, changelog, manifest/adapters, and the dated verification report.
- [x] M7-T02 Extend existing package checks to verify the third skill and every
      referenced resource in both ZIP and tar.gz archives.
- [x] M7-T03 Add validator tests/linting to the existing CI workflow. Run the new
      helper on Windows, Linux, and macOS with the documented Python minimum
      and current supported runtime; retain PowerShell 5.1/7 and Bash parity.
- [x] M7-T04 Run the existing smoke red drills and release reproducibility checks
      without reducing their scope or suppressing failures.
- [x] M7-T05 Confirm all new delivery/evaluation code is first-party, no external
      framework or integration was added, and no duplicate policy/logic emerged.
- [x] M7-T06 Select the release version after compatibility review, push the
      reviewed commit through CI, publish only exact annotated-tag source, and
      independently verify published checksums, contents, and provenance.
- [x] M7-T07 When updating the installed package, preserve the shared clone and
      junction layout and verify all skill entry points through fresh discovery.

Acceptance: no unresolved required milestone gate, all claimed host checks
passed, new resources are present in archives and discovery, and release notes
describe actual implemented behavior. A partial release must explicitly reduce
scope and leave this full roadmap incomplete; it cannot claim all gaps closed.

## File ownership and reuse rationale

These paths own the implementation; shared procedures remain canonical.

| Path | Action and reason |
|---|---|
| `skills/project_setup/SKILL.md` | Extend existing handoff, planning, and completion sections |
| `skills/quality_retrofit/SKILL.md` | Apply shared traceability/resume without duplicating delivery logic |
| `skills/feature_delivery/SKILL.md` | Add genuinely missing feature-delivery entry point |
| `skills/project_setup/references/grill-me.md` | Extend focused discovery coverage only |
| `skills/project_setup/assets/PROJECT_BRIEF.md` | Add references needed for scoped delivery; keep the product contract canonical |
| `docs/DELIVERY.md` | Shared lifecycle/schema contract |
| `docs/RED-DRILLS.md`, `docs/CODE-QUALITY.md` | Add cross-references only where needed; retain authoritative procedures |
| `templates/workflow/PLAN.md` | Native plan asset |
| `scripts/verify-delivery.py` | One first-party standard-library structural validator |
| `tests/test_verify_delivery.py`, `tests/fixtures/delivery/` | Deterministic positive/negative verification of that validator |
| `tests/behavioral/` | Agent-outcome scenarios and checks |
| `tests/cross-platform-smoke.ps1`, `tests/release-package-smoke.ps1` | Extend existing package/resource coverage |
| `.github/workflows/cross-platform.yml`, `.github/workflows/release.yml` | Reuse established CI/release pipeline; no second release implementation |
| `AGENTS.md`, existing adapters, `.claude-plugin/`, README, CONTRIBUTING, documentation indexes | Reconcile discovery, compatibility, and truthful usage claims |
| `CHANGELOG.md`, `docs/QUALITY-REVIEW.md` | Record completed changes and actual evidence, preserving prior history |

## Delivery risks and controls

| Risk | Control |
|---|---|
| More paperwork than value | One compact schema; scale record size to the change; no empty artifact trees |
| New ledger duplicates existing plan truth | One canonical record; prose references IDs; derived reports do not become independent trackers |
| Structured checks misrepresented as semantic proof | Separate validator results, agent review, executable tests, and behavioral evaluations |
| Stale or circular evidence | Hash semantic inputs, record tool context, exclude receipt/progress self-references, test invalidation |
| Reconciliation creates an endless task backlog | Stable IDs, update existing owners, no-change idempotence, explicit no-progress stop |
| New skill dilutes setup/retrofit boundaries | Routing fixtures and shared rules; all existing entry points remain available |
| Cross-platform behavior assumed from local success | Preserve native checks and require remote matrix evidence before release claims |
| First-party requirement erodes during implementation | Review imports, dependencies, assets, and new files against the explicit scope boundary |

## Completion checklist

- [x] R01–R08 have implementation, positive/negative checks, and evidence.
- [x] No requirement or required acceptance criterion is orphaned.
- [x] Readiness, implementation, and verified completion remain distinguishable.
- [x] Reconciliation is idempotent and resume rejects stale evidence.
- [x] Behavioral trials pass without false-green or scope violations.
- [x] Existing v0.5.0 gates remain effective and pass.
- [x] Documentation, packaging, discovery, and release verification agree.
- [x] No third-party code, integration, copied workflow, or duplicate runtime added.

M1–M7 are complete. No feature implementation or required release gate remains
open. The post-publication receipt in docs/QUALITY-REVIEW.md records the exact
release, artifact/provenance checks, and installed discovery.

## Implementation evidence log

- M1–M5: contract, asset, three workflows, shared validator, semantic closeout,
  change-impact fingerprints, and atomic writer implemented. Forty-six tests
  pass, including two validator mutations, interrupted/stale writes, idempotence,
  and independent outcome-oracle controls. Strict mypy and Ruff pass locally.
- All 24 core trials passed independent checks and semantic review. A separate
  unchanged-plan trial preserved all existing artifacts with no duplicate work.
  See docs/evaluations/v0.6.0.json and docs/QUALITY-REVIEW.md for scoped evidence.
- README uses neutral artwork, concise routing, and two-column comparisons.
  GitHub-rendered Markdown was checked with official styles in light/dark themes:
  375px and 1440px layouts showed no page overflow and all images loaded with alt text.
- All twelve final-source matrix jobs and all thirteen release jobs passed.
  v0.6.0 contains exact annotated-tag source at b78723b. All five published assets
  matched the local tagged build; both archive attestations and all 76 installed
  files verified. Fresh Codex discovery found all three workflows enabled.
- Test-only policy exceptions retain standard-library unittest assertion style;
  narrow subprocess exceptions cover fixed trusted commands and owned fixtures.

## Post-release audit hardening (2026-09-24)

Baseline: `1789ed0`, clean tree, level with `origin/main`. The owner asked for
every audit finding to be fixed. Scope: shipped template and script defects,
gates this repository prescribes but did not run on itself, CI supply-chain
hardening, and missing guidance. Out of scope without a further decision: new
language templates (Go, Java/Kotlin, Swift), a version bump, tagging, and
publication.

| ID | Required outcome |
|---|---|
| H01 | Every shipped template loads in its tool, and each changed rule is red-drilled |
| H02 | Scanners agree across shells, emit valid JSON for any path, and detect the package's own recommended files and tools |
| H03 | This repository runs every gate it prescribes for its own languages, locally and in CI |
| H04 | CI actions, hooks, and tools are immutable pins with automated update proposals |
| H05 | Guidance covers test depth, performance, supply chain, accessibility automation, and CI workflows from primary sources |
| H06 | Helper scripts report input errors distinctly and preserve file permissions |

- [x] H01 C# props XML fixed; `.editorconfig` and `deny.toml` templates added;
      mypy codes, PSScriptAnalyzer, and pre-commit hooks corrected; all drilled.
- [x] H02 Both scanners extended; bash rewritten to one escaped, case-insensitive
      pass; parity, escaping, and speed verified; six maintained smoke drills.
- [x] H03 Frozen pre-commit configuration, two mypy scopes with the shipped
      template, vulture whitelist, Bandit, coverage floor, and CI jobs.
- [x] H04 SHA-pinned actions, `persist-credentials: false`, timeouts, hash-locked
      tools, checksum-verified gitleaks, Dependabot with cooldown.
- [x] H05 CODE-QUALITY sections and workflow, template, and README updates; all
      45 cited URLs returned HTTP 200 on 2026-09-24.
- [x] H06 `verify-format-safe.py` exit contract and writer permissions, with tests.
- [x] Hosted cross-platform CI passes on the committed change, including macOS
      and the POSIX escaping check: all thirteen jobs in run 36073624130 at
      `1c43b29` (PR #3, fast-forwarded to main).
- [x] `release-package-smoke.ps1` passes on the committed tree under
      PowerShell 7 and 5.1.
- [x] Release v0.7.0 from the exact annotated tag and verify published assets:
      commit `5ceda26`, release run 36074501215, all five assets byte-identical
      to a local exact-tag build, both attestations verified.
- [x] Dependabot's first run handles the uv lock and frozen hooks: PRs #4–#6
      passed all thirteen jobs and were merged after the release.

Evidence, environments, and limits: `docs/QUALITY-REVIEW.md`, section
"Post-release audit: 2026-09-24".
