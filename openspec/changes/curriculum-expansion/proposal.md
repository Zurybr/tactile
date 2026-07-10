# Proposal: Curriculum Expansion (100+ fluency lessons)

> Source: `openspec/changes/curriculum-expansion/exploration.md` + Engram `sdd/curriculum-expansion/explore` (#338).
> BINDING decisions: ≥100 new lessons "of all types"; fluency WPM ramp **40→65** starting where the 10→40 spine ends; fluency track appended AFTER the existing speedtest.

## Intent

The key-introduction spine (26–27 units/layout) teaches keys but never builds real-world fluency: no sentences, paragraphs, n-grams, code, numbers-in-context, or timed bursts, and the 300-word lists force pseudo-word fallbacks. Learners graduate the speedtest with nothing left to practice. This adds a **post-speedtest fluency track** (≥100 new lessons across both layouts) covering common motor patterns, real prose, code, numbers, and speed bursts.

## Scope

### In Scope
- Fluency track appended AFTER the speedtest: bigrams/trigrams, common-words tiers (100→500→1000), sentences, paragraphs, numbers, symbols, code snippets (en_us), speed bursts — ~37 units/layout × 2 ≈ 74 min, expandable to 100+.
- New WPM ramp **40→65** for fluency units (spine keeps 10→40); overall ramp stays monotonic.
- Data model: add `track` field + fluency `kind` values; `_finalize()` newline-preserving path for paragraphs.
- Wordlists grown 300→1000+ (public-domain frequency lists); new bundled content files (sentences, paragraphs, code, n-grams).
- Chained-PR delivery (one PR per exercise-type group).

### Out of Scope
- New keyboard layouts or new languages beyond en_us/es_la.
- Adaptive weak-key review (Option D) — deferred to a follow-up.
- UI/screen changes beyond an optional fluency-track section header in the lesson map.

## Capabilities

> `openspec/specs/` has no baseline curriculum spec; both below are new specs capturing existing + new curriculum behavior.

### New Capabilities
- `fluency-track`: post-speedtest units — n-gram / common-word / sentence / paragraph / number / symbol / code / burst generators, 40→65 WPM ramp, newline-preserving finalize, determinism via seeded `_rng`.
- `curriculum-builder`: `build_curriculum` pipeline + `Unit`/`Exercise` data model + `track` field. *modifies existing spine behavior* (appends fluency track; spine preserved).

### Modified Capabilities
None baseline-spec'd yet — see New Capabilities above.

## Approach

| # | Change | Approach |
|---|--------|----------|
| 1 | Track field | Add `Unit.track: Literal["spine","fluency"]`; spine units unchanged; fluency units start at 40 WPM. Lets UI/ramp logic branch cleanly. |
| 2 | Generators | One seeded `_rng`-based generator per type, appended in `build_curriculum` after the speedtest. Pedagogical order: ngrams → words → sentences → paragraphs → code → numbers → symbols → bursts. |
| 3 | Newline path | `_finalize` branches on track — paragraphs/sentences keep `\n`; lessons keep current single-line behavior. |
| 4 | Content | Public-domain EN/ES prose (Project Gutenberg / public-domain ES); code = curated patterns (en_us only); per-layout `typable()` filter verified before bundling. |
| 5 | Tests | Redesign unit-count + WPM-ramp (two-segment monotonic); add generator + determinism + content tests per type. |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/tactile/curriculum.py` | Modified | `track` field, new `kind` literals, new generators, extended `build_curriculum`, `_finalize` branch |
| `src/tactile/wordlists/` | New/Modified | grow `en.txt`/`es.txt`; add content files (sentences, paragraphs, code, ngrams) |
| `src/tactile/layouts/*` | Unchanged | `key_order` spine preserved (optional minor extension deferred) |
| `src/tactile/progress.py` | Unchanged | free-navigation model; new unit ids just flow through |
| `tests/test_curriculum.py` | Modified | redesign count + ramp tests; add per-type tests |
| `docs/engineering/curriculum.md` + `CHANGELOG.md` | Modified | per AGENTS.md mapping |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Test churn (count + ramp) | High | Redesign to two-segment monotonic (10→40 spine, 40→65 fluency); TDD red→green |
| Determinism break | Medium | Mandate seeded `_rng` in every generator; keep determinism test |
| `_finalize` `\n` regression | Medium | Branch on track; lesson-no-newline test stays green (only checks `kind=="lesson"`) |
| Content licensing | Medium | Public-domain sources only; document provenance per file |
| 400-line PR budget | High | Chained PRs per exercise type (flag for sdd-tasks forecast) |
| Wordlist typable shrinkage | Low | Per-layout `typable()` filter verification before bundling |

## First Slice (tracer bullet)

**Bigrams/trigrams drills** — establishes the full fluency-track scaffolding (`track` field, `build_curriculum` append, 40→65 ramp, new `kind`, seeded generator) with minimal content, no newline/licensing risk, highest pedagogical value (most common motor patterns). Each subsequent type reuses the pattern as its own chained PR. Bundle trivial wordlist growth (300→1000) early to feed later common-words tiers.

## Rollback Plan

Each exercise type lands as one atomic `feat(curriculum)` commit. Revert a type's commit to remove it. Curricula are rebuilt from code (never persisted), so rollback is code-only; any `progress.json` unit ids that vanish are simply ignored by the free-navigation model — no migration needed.

## Dependencies

None external. All content sourced from public-domain texts and bundled as package data via `importlib.resources`.

## Success Criteria

- [ ] ≥100 new fluency units across en_us + es_la combined (≈74 min, expandable).
- [ ] Spine (26–27 units/layout) and its tests preserved; WPM ramp monotonic across spine (10→40) then fluency (40→65).
- [ ] Every new generator deterministic via seeded `_rng`; paragraphs preserve `\n`, lessons stay single-line.
- [ ] `uv run pytest -q` green; `docs/engineering/curriculum.md` + `CHANGELOG.md` updated; `validate_docs.py` passes.
- [ ] Delivered as chained PRs, each ≤400 lines.
