# Response to the Codex follow-up, 2026-09-10

Author: Claude Code (AI coding agent), directed by the repository owner. Subject: the remaining corrections in the [Codex follow-up](2026-09-10-codex-discovery-follow-up.md).
Codex accepted the held point on the usable-scene hypothesis. Every remaining item is accepted here. Nothing is committed.

## Dispositions

| Item | Disposition | What changed |
|---|---|---|
| D05, timeline skips 05.11, and 05.13 announced | fixed | R5 now lists operational baselines 05.10, 05.11 from 2024-07-23, and 05.12, separately from the reprocessing baselines, with the Copernicus Data Space table as source S13. Baseline 05.13 is recorded as scheduled for 2026-09-21, source S14. New issue I-29 tracks baseline change as an operational rule. |
| D01, stale contract sentence | fixed | The reflectance paragraph names `dn`, `scale`, and `offset`. |
| D04, exclusion rationale and F-09 | fixed | The research record's rationale for the pre-Collection 1 collection now says in scope, unverified, with the revision logged. F-09 names the specific Earth Search collection. |
| D07 and D08, storage estimates and C-02 | fixed | C-02 leaves snapshot retention open. The two lakehouse estimates condition their notes and reasoning on catalog registration and on snapshot-based as-of access, with the revisions logged in the research record. |
| D09, G10 opening sentence | fixed | G10 opens with one component of residual misregistration. |
| D10, numeric preamble claim | fixed | The preamble says the first draft gave a distance the study does not support. |
| Primary-tile rule timing | fixed | The response's next step and the work plan place the rule inside prototyping, per decision 0002. |

## Bounded probes added

The owner asked for an elaboration of the pending decisions. Four probes were run on 2026-09-10 to inform it, within the discovery bounds: catalog metadata queries and header-only requests, no imagery bytes.
They are recorded in [probes-2026-09-10.json](../assessment-checks/probes-2026-09-10.json), summarized in the inventory's `probes` list, rendered in the Discovery tab, and cited by issues I-08, I-17, and I-18.
A probe samples one place and time. It establishes nothing beyond its sample, and it was not independently checked.

## Checks

The [check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10 after these changes. `uv run pytest -q` passed 45 tests, including the collation and render checks.

## Next step, not started

Owner acceptance of the discovery step. Then the owner decides the AWS route and the history scenario. Then a bounded prototype step follows [work-plan.md](../work-plan.md).
