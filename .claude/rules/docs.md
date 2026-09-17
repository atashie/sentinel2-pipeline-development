---
paths:
  - "docs/**"
  - "README.md"
  - "CLAUDE.md"
  - "AGENTS.md"
---

# Rules for documents

- Every claim about a source, service, or tool carries `documented`, `measured`, or `unverified`. Every planning assumption is a row in `docs/assumptions.md` with `sourced` or `unsourced`.
- One fact has one home. Link to it. If you find a copy, remove the copy.
- Refer to colleagues by role. Never write a person's name. Do not name the company's customers or the customers' current vendors.
- Measurement numbers cite a file in `benchmarks/results/` or a primary page. Verification results name the command and outcome.
- Dates are ISO 8601 with no relative dates. Dated documents put the date in the first heading.
- Plain English and American spelling. Descriptive sentences: 25 words maximum. Procedure steps: imperative, 20 words maximum. No semicolons. No "should". Quoted source text stays verbatim.
- Use relative links for repository files. External primary-source citations use HTTPS links.
- `tests/test_docs.py` checks that every relative link resolves.
- Decisions go in `docs/decisions/NNNN-<slug>.md` and the index. Reviews go in `docs/reviews/YYYY-MM-DD-<slug>.md` and the index.
- AI-generated research, including files under `docs/references/`, is input, not evidence. Its claims stay `unverified` until rechecked against a primary page.
