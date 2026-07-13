# 10:00 Open Mechanism / Pre-10:00 Rejection-Block Report

Generation: 10:00 open mechanism / pre-10:00 rejection-block discovery
(base `201896d`). Branch: `research/ten-am-rejection-block-discovery`.
Partition: development only, ES + NQ, 2018-01-03 -> 2022-12-30. 2023
onward was never read. Pure OHLCV geometry; no ICT narrative, no
order-flow/absorption/dealer-positioning/liquidity-sweep claim, no
profitability, entries, exits, sizing, or TP/SL anywhere.

## Session/event counts

| Instrument | Valid sessions | Module A events | Module B events (upper+lower) |
|---|---|---|---|
| ES | 1286/1291 | 1286 | 1465 |
| NQ | 1284/1291 | 1284 | 1451 |

Upper block valid 1223 (ES) / 1267 (NQ) of valid sessions; lower block
valid 1233 (ES) / 1271 (NQ) — the rest failed the one-tick minimum-width
gate. All 2570 Module A events and 2916 Module B events are retained in
the ledgers regardless of classification.

## Module A classification (28 cells: instrument x candle_state x horizon)

25/28 `TEN_AM_CONTINUATION`, 2 `TEN_AM_MIXED_OR_NULL` (both H=1, small
sample), 1 `UNDERPOWERED` (NQ `BULLISH_1000` H=1). Effect sizes are large
(6-27 percentage points, continuation-first minus reversal-first),
q-values are extremely small (1e-4 to 1e-25), and 4-5 of 5 years agree
in sign in every cell. **Coherent-mechanism rollup: all 4
`instrument x candle_state` combinations reach `TEN_AM_CONTINUATION`**
(ES bullish, ES bearish, NQ bullish, NQ bearish), supported by
2+ adjacent horizons in every case.

**This is a real, statistically overwhelming pattern in the data — but
it must be read with an important structural caveat before it is treated
as a predictive discovery**, per this generation's charter commitment to
distinguish genuine signal from mechanical artifact:

> Module A's continuation/reversal directions and barriers are defined
> relative to `O_1000` (the 10:00 candle's **open**), while the 10:00
> candle **state itself** (`BULLISH_1000`/`BEARISH_1000`) is defined by
> where the candle **closes** relative to that same open. The
> post-event price path (measured from `T+1` onward) necessarily starts
> from `Close_1000`, which — by the very definition of a bullish or
> bearish candle state — already sits some distance from `O_1000` on the
> continuation side. A barrier measured `b x RANGE_30` from `O_1000` is
> therefore mechanically closer to being reached in the continuation
> direction (part of the distance was already covered by the candle's
> own body) and mechanically farther in the reversal direction (price
> must first travel back through `O_1000`). This is not a lookahead bug
> — every bar used is strictly at or after `T+1` — but it means part
> (plausibly most) of the 6-27pp "continuation" edge is a **direct,
> deterministic consequence of anchoring the barrier to the candle's
> open rather than its close**, not new information revealed by holding
> a position through 10:01 onward. The effect growing with horizon (6pp
> at H=1 up to ~27pp at H=15-30, per instrument/side) and the same
> pattern appearing in *every* instrument/side combination with no
> exception is consistent with this structural explanation rather than a
> discovered market inefficiency. This construction is exactly as
> specified in `SPEC_TEN_AM_BLOCKS.md` (mirroring the task's own Module A
> definition) — it is disclosed here, not silently corrected, per "do
> not redesign the study."

Given this caveat, Module A's finding is reported honestly as: **the
10:00 candle's own directional move very often continues past its own
open over the following hour — largely, and probably mostly, because
that is what "continuation measured from the open" means when the
candle itself already moved** — rather than as a freestanding predictive
discovery about future price action independent of the candle's own
displacement.

## Module B classification (336 cells: instrument x side x freshness x activation_window x horizon)

224 `MIXED_OR_NULL`, 104 `UNDERPOWERED` (mostly `WITHIN_10AM_CANDLE`
activation window, smallest samples), **8 `REJECTION_BLOCK_REVERSAL_DOMINANT`**,
0 `REJECTION_BLOCK_BREAKTHROUGH_DOMINANT`. All 8 directional cells belong
to one combination: **ES, lower block, `PRETOUCHED`**, spanning
activation windows `WITHIN_10MIN`/`WITHIN_15MIN`/`WITHIN_30MIN` and
horizons 10/15/30 minutes (all adjacent), effect sizes 9-19pp, q<0.05,
4-5/5-year agreement. **Coherent-mechanism rollup: ES lower-block
PRETOUCHED reaches `REVERSAL_DOMINANT`**; all other 7
`instrument x side x freshness` combinations (including NQ lower-block
PRETOUCHED) are `NO_COHERENT_MECHANISM`.

Unlike Module A, Module B's barriers are anchored to the pre-10:00 block
boundaries (fixed before 10:00, independent of the 10:00 candle), so this
finding does not share Module A's open-vs-close mechanical artifact.
It is a genuinely narrower, more surprising result — but it is
**instrument-specific (ES only, not replicated in NQ)** and
**freshness-specific (PRETOUCHED only, not PRISTINE)**, which limits how
much weight it should carry.

## Same-bar findings (Module B)

Same-bar reversal/breakthrough rates sit close to 50/50 across most
cells (`reports/tables/same_bar_morphology_table.csv`); no strong
same-bar tilt independent of the post-interaction barrier result above.

## Pristine vs. pretouched

The one Module B directional finding is confined to `PRETOUCHED` blocks
(a later pre-10:00 bar already traded into the zone before 10:00);
`PRISTINE` blocks (untouched before 10:00) show no directional cells in
either instrument. This is consistent with — though does not prove — the
intuitive reading that a zone already revisited once pre-10:00 behaves
differently from one visited for the first time after 10:00; it is
reported as an observed pattern, not explained by any order-flow
mechanism (explicitly out of scope).

## Momentum-context findings

`MOMENTUM_INTO_BLOCK` vs. `NOT_MOMENTUM_INTO_BLOCK` context strata are
reported in `reports/tables/module_b_context_strata_table.csv`; neither
stratum shows a materially different pattern from the pooled result for
the one directional cell family (ES lower PRETOUCHED) — the reversal tilt
is present regardless of whether pre-10:00 momentum ran into the block,
so momentum alignment does not appear to be a distinguishing factor here.

## Activation-window findings

The Module B finding spans `WITHIN_10MIN`, `WITHIN_15MIN`, and
`WITHIN_30MIN` (not `WITHIN_10AM_CANDLE` or `WITHIN_5MIN`, which are
underpowered at this sample size, and not distinctly stronger at
`WITHIN_60MIN`). It is not confined to the 10:00 candle or the first five
minutes.

## Horizon findings

Module A's continuation edge grows from ~5-8pp at H=1 to a plateau of
~20-27pp by H=15-30, then eases slightly by H=60 — consistent with the
mechanical open-anchoring explanation (more time for `RANGE_30`-scaled
barriers to be reached in either direction, with continuation
structurally favored throughout). Module B's ES-lower-PRETOUCHED effect
is present from H=10 through H=30 and is not tested at H=1 (too few
non-tied outcomes) or H=60 (drops out of the reported directional set,
though still `MIXED_OR_NULL` rather than reversing sign).

## Year stability

Both findings show 4-5 of 5 development years agreeing in sign — neither
is a single-year (e.g. 2020) artifact.

## ES vs. NQ agreement

Module A: both instruments show the same pattern in both directions (4/4
`instrument x candle_state` mechanisms are `TEN_AM_CONTINUATION`) —
consistent with the mechanical explanation applying equally to both.
Module B: ES and NQ disagree — only ES lower-PRETOUCHED reaches a
coherent mechanism; NQ's matched cell (`NQ lower PRETOUCHED`) is
`NO_COHERENT_MECHANISM` despite qualitatively similar point estimates in
several individual cells (see `reports/tables/module_b_classification.csv`),
so this finding does not have cross-instrument confirmation.

## Strongest reversal cell

Module B, ES lower block, `PRETOUCHED`, `WITHIN_30MIN`, H=30: reversal-first
18.8pp above breakthrough-first (n=359, q=0.023, 4/5-year agreement,
median signed close +0.10 ATR, matching sign).

## Strongest breakthrough cell

None reached directional classification anywhere in Module B (0/336
`REJECTION_BLOCK_BREAKTHROUGH_DOMINANT`). The closest breakthrough-leaning
cell (largest negative effect, still `MIXED_OR_NULL`) is documented in
`reports/tables/module_b_result_table.csv`.

## Strongest nulls

Module B: NQ upper block, `PRISTINE`, `ALL` context, most horizons —
reversal/breakthrough-first rates within a few points of 50/50, q>0.5.
Module A H=1 cells (smallest samples, weakest — though still
significant — effect) are the weakest points in an otherwise uniform
Module A pattern.

## Final report questions

1. **Does the 10:00 open create continuation or reversal information?**
   The data show a large, consistent, highly significant continuation
   pattern in all 4 instrument/candle-state cells — but per the
   structural caveat above, this is very likely dominated by the
   open-vs-close anchoring construction rather than new predictive
   information about future price action beyond what the candle's own
   close already encodes.
2. **Do upper rejection blocks reject or break through?** Neither,
   directionally — 0 upper-block cells (either instrument, either
   freshness) reached a coherent classification.
3. **Do lower rejection blocks reject or break through?** ES lower
   blocks show a reversal-dominant pattern, but only when `PRETOUCHED`;
   NQ lower blocks show no coherent pattern.
4. **Does pristine versus pretouched status matter?** Yes for the one
   Module B finding found — it is present only in `PRETOUCHED`, absent in
   `PRISTINE`, for both sides and both instruments.
5. **Does momentum into the block predict breakthrough?** No — momentum
   alignment does not distinguish the pattern in the one cell family
   where a directional result exists, and no breakthrough-dominant cell
   was found anywhere to test this against directly.
6. **Does opposite pre-10 direction predict rejection?** Not tested as a
   standalone significant driver here; the context-strata table shows no
   cell where `pre10_stratum` alone reaches a materially different result
   from the pooled ES-lower-PRETOUCHED finding.
7. **Is any effect confined to the 10:00 candle or first 30 minutes?**
   No — Module A's pattern strengthens with horizon (not confined to the
   candle); Module B's finding spans 10-30 minute activation windows, not
   the candle itself or the first 5 minutes.
8. **At which post-event horizons does it persist?** Module A: H=3
   through H=60 (not H=1). Module B: H=10 through H=30.
9. **Is it stable across 2018-2022?** Yes for both findings, 4-5 of 5
   years agree in sign.
10. **Does ES agree with NQ?** Module A: yes, both instruments show the
    identical pattern. Module B: no — the one directional finding is
    ES-only.
11. **Is there any coherent candidate worth later validation?** Module
    A's pattern is coherent and stable but is assessed here as largely a
    structural/mechanical consequence of the O_1000-anchored definition
    rather than a standalone predictive candidate — freezing it for
    validation without first re-anchoring the comparison to `Close_1000`
    would risk validating a tautology, which is outside this
    generation's scope (no redesign permitted). Module B's ES-lower-
    PRETOUCHED finding is the more genuinely novel candidate, but it
    lacks NQ confirmation and rests on a comparatively modest, single-
    instrument sample (n=255-421 depending on cell) — not strong enough
    on its own, absent replication, to call a clean validation candidate.

## Verdict

A coherent statistical pattern was found in both modules, but neither
clears an unambiguous bar for a genuinely novel, cross-instrument-
confirmed, non-mechanical mechanism: Module A's result is dominated by
its open-vs-close construction rather than new predictive content, and
Module B's result is real but confined to one instrument, one side, and
one freshness state. Per the preregistered fallback framing, no
*coherent, cross-confirmed* 10:00-open or pre-10:00 rejection-block
mechanism free of a structural explanation was found in ES/NQ one-minute
OHLCV during 2018-2022 that would be responsible to carry into a 2023+
validation study.

No validation-partition (2023+) study follows this generation.
