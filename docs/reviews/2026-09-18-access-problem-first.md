# Section 02 states the problem before the answer, 2026-09-18

Implementer: Claude Code (AI coding agent), directed by the repository owner. Status: ready for owner and Codex review after the checks recorded below.

Scope: the head of section 02 of the [page](../s2-options.html). No fact, number, link, table, or figure changed. No script contacted a provider. No selection changed.

## The owner's direction

Section 02 must first define the problem for the reader: Sentinel-2 is on AWS as two collections. How do we choose between them, or use both? The answer comes after that.

The owner also settled two questions from the [sensor band comparison](2026-09-17-sensor-band-comparison.md): the comparison block stays closed by default, and the band footnotes stay as they are.

## What changed

Before, the section opened with the answer as its headline, "Use Collection 1 first. Keep the older copy for gaps." The reader met the two archives only in the sentence below it.

Now the section opens with the situation and the question. The headline is "Two public copies of Sentinel-2. Pick one, or use both?" The introduction says what the two collections are, that they are not interchangeable, and that we must decide which copy to trust, and when.

Four short boxes name the ways the copies differ, each pointing at evidence the section already carries: neither copy is complete, the same product can hold different numbers, versions compete, and quality layers differ.

The former headline follows as a subheading, "Our answer: read Collection 1 first. Keep the older copy for gaps." The route figure, the comparison table, the validation note, the archive history, the coverage strip, and "Why both matter" follow unchanged.

The four boxes reuse the existing four-column style from section 01. No new style was added. One inline margin separates the subheading from the route figure.

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass |
| `uv run pytest -q` | 214 passed in 12.20 seconds, existing library deprecation warnings only |
| The four `--check` tools and `git diff --check` | Inventory, sensor band dataset, page, and gap report match their inputs. No whitespace error |
| Sentence audit of the new head | Longest sentence 17 words. No semicolon, no "should", no modal |
| Headless Chromium at 1280 pixels | The head, the four boxes, the subheading, and the route figure render in that order above the unchanged table |

## Proposed next step

Owner and Codex review of this head together with the sensor band comparison. No commit, push, or deployment was performed.
