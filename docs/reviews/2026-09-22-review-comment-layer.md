# Review-comment layer on the assessment page, 2026-09-22

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented for owner review.

The owner asked for the `html-review-comments` skill, held locally under `~/github/cc-skills`, on the
assessment page, so colleagues can comment on it without an account or a server.

## What changed

- `tools/s2-options.template.html` gains one injected block before `</body>`: a stylesheet, a JSON config,
  a mount point, and a script. The block is generated. Never edit it by hand.
- `tools/review-layer.json` holds the configuration, so the injection and its drift check use one source.
- `docs/s2-options.html` is regenerated from the template. It grew from 213,482 to 265,442 bytes.
- [CLAUDE.md](../../CLAUDE.md) gains the drift-check command and the rule against hand edits.

The configuration is `rootSelector` `#main`, `tabSelector` `section[role="tabpanel"]`, and `docKey`
`s2-options`. The fixed document key keeps a reader's stored comments across regenerations of the page.
The tab selector groups comments by tab and reveals a comment on a hidden tab.

Injection follows the skill's template procedure. The layer goes into the template, not the generated page,
so `tools/render_options.py --check` stays green.

## How to use it

```sh
python3 ~/github/cc-skills/html-review-comments/scripts/inject.py tools/s2-options.template.html \
    --config "$(cat tools/review-layer.json)" --check     # drift check
uv run python tools/render_options.py                     # regenerate after any injection
python3 ~/github/cc-skills/html-review-comments/scripts/merge_comments.py \
    --html docs/s2-options.html --out digest.md --roles roles.json returned.json
```

Tell a reader: select text, click "Add comment", then open "Comments" and use "Copy" or "Download JSON".
Comments stay in that reader's browser until they export. Ask for the export before the file moves.
A commented copy of the page contains the whole page. Say so before sharing one.
Replace names with roles through `--roles` before a digest enters this repository.

## Verification

- `python3 inject.py ... --check`: up to date.
- `uv run python tools/render_options.py --check`: the page matches its template and evidence inputs.
- `uv run pytest -q`: 278 passed. The documentation link check sees no new relative link.
- Headless Chromium on the generated page: the "Comments (0)" button is visible, the Prototyping tab opens,
  selecting the section 00 heading raises the "Add comment" popover, and no page error or failed request occurred.
- `uv run ruff check .` and `uv run ruff format --check .`: passed. `git diff --check`: passed.

The layer changes no content inside `#main` and no measured evidence.

## Limits and proposed next step

The layer needs a browser with the CSS Custom Highlight API. Comment anchors can fail after the quoted text
changes by more than about 30 percent, and `merge_comments.py` then reports them under "Not found".
The drift check is not in CI, because the skill lives outside this repository.
Proposed next step: host or send the page and collect the first round of comments.
No commit, push, or publication occurred.
