# Development workflow, 2026-09-09

Authority: the repository owner requested stepwise work with review by the owner, Codex, and Claude Code after each step.
The owner confirmed on 2026-09-09 that this repository follows the same workflow as the weather feature repository.

## Assessment and selection gate

[Decision 0001](decisions/0001-scope-and-sequence.md) records the sequence: initialize, discover, select, prototype, specify, weigh tradeoffs, present.
Complete discovery and collate findings before selecting prototype candidates.
Review that discovery with the owner, Codex, and Claude Code before the owner authorizes a prototype step.
The preferred route in [assumptions.md](assumptions.md) confers no selected status.

## One step at a time

1. Read [CLAUDE.md](../CLAUDE.md), applicable rules, the latest review, and relevant decisions.
2. Inspect the working tree and preserve changes from other contributors.
3. State the authorized step, acceptance checks, and work deferred to later steps.
4. Implement that step and update its tests, contract, and documentation where needed.
5. Run the [check workflow](../.claude/skills/check/SKILL.md).
6. Record changed behavior, evidence, remaining risks, and unresolved findings in a dated review response.
7. Stop for review by the owner, Codex, and Claude Code.
8. Address review feedback within the same step and repeat affected checks.
9. Start the next step only after the owner explicitly accepts the review and authorizes continuation.

Do not treat silence, passing tests, or an AI review as owner approval.
Do not commit, push, or publish a pending step without explicit authorization after review.
Do not contact another reviewer automatically. The owner coordinates the review handoff unless they authorize another arrangement.

## Review record

Each response records the original finding IDs and their dispositions.
Use `fixed`, `accepted and deferred`, or `corrected with evidence`.
Describe the actual checks and their limits. Distinguish AI review from human or engineering approval.
Keep historical audits intact and link later corrections from [reviews/README.md](reviews/README.md).

The response must identify the next proposed step without starting it.
Reference [assumptions.md](assumptions.md) for scope and [work-plan.md](work-plan.md) for step order.

## Research with subagents

Discovery uses a team of research and checking subagents, as the owner instructed on 2026-09-09.
A research agent drafts claims with sources and access dates. A different agent checks each claim against its page.
Only confirmed or corrected claims populate the inventory. Rejected claims stay in the check record as history.
Subagents do not contact a provider for data. Catalog metadata queries are allowed when the plan bounds them.

## Measurements and access

Keep result JSON immutable between script runs. Label existing measurements with their code version.
Scripts that read products from a bucket or API run only when the user invokes them.
Existing authorization applies only within its recorded scope. Follow the environment's actual filesystem and network permissions.
Claude Code permission patterns configure Claude Code. They do not grant another agent additional tool permissions.

## Persistent project guidance

[CLAUDE.md](../CLAUDE.md) owns shared conventions. [AGENTS.md](../AGENTS.md) directs Codex to those conventions and applicable rules.
This arrangement keeps project guidance in version control and avoids a second private copy of the development policy.
It does not claim to update either product's private automatic-memory store.

The short instructions, scoped rules, and repeatable checks follow the official Claude Code documentation.
See [project memory](https://code.claude.com/docs/en/memory) and [best practices](https://code.claude.com/docs/en/best-practices).
