# EMA21 Level Discovery Report

Generation: intraday EMA21 level discovery (independent, base `201896d`)
Branch: `research/intraday-ema21-level-discovery`
Partition: development only, ES + NQ, 2018-01-03 -> 2022-12-30. 2023 onward
was never read by any analysis code in this generation.

This is a descriptive level-interaction study. It contains no entries,
exits, sizing, TP/SL, or profitability claim, and it is not a validation
or reproduction of the "21 EMA strategy" screenshot (+0.72% vs. +45.31%
buy-and-hold, Sharpe 0.13, max DD -22.18%) that motivated the question —
that screenshot describes a full trading system and is not evidence about
whether EMA21 is a repeatable price *level*.

## Event volume

| Instrument | Armed excursions | Touch events | RTH_EMA touches | FULL_SESSION_EMA touches |
|---|---|---|---|---|
| ES | 83,904 | 36,413 | 17,369 | 19,044 |
| NQ | 82,833 | 35,753 | 17,235 | 18,518 |

(Sums across EMA20/21/22 and both approach sides; see
`reports/tables/full_exploratory_results.csv` for the full breakdown.)
All 72,166 touch events had a valid (>0) pre-touch ATR20; none were
excluded on `ATR_INVALID` grounds. Same-bar morphology overall:
37,067 `SAME_BAR_REJECTION_PROXY` vs. 35,099 `SAME_BAR_BREAKTHROUGH_PROXY`
(51.4% vs. 48.6%, pooled across every span/side/instrument/definition —
individual cells range roughly 49%-53%, see below).

## Primary result: 1.0-ATR rejection-first vs. breakthrough-first, H=5 bars (25 min)

120 primary cells (`instrument x ema_session_definition x ema_span x
approach_side x time_stratum`; `reports/tables/primary_result_table.csv`).
All 120 cells met the minimum-sample gate (touch_events ranged 293-3,444,
all >=50; non-tied first-hit outcomes and year-coverage floors also met) —
**no cell was `UNDERPOWERED`**. This is a genuine null result, not a
power problem.

- 24/120 cells (20%) had |rejection-first minus breakthrough-first| >= 5pp
  (the material-effect floor).
- 8/120 cells had BH-adjusted q < 0.05 within their
  `instrument x session_definition x time_stratum` family.
- **0/120 cells satisfied all five joint classification conditions**
  (sample, >=5pp effect, q<0.05, matching median-signed-close sign, >=4/5
  year-sign agreement). **Classification: `MIXED_OR_NULL` for all 120
  primary cells.**

There is a small, fairly consistent tilt toward rejection-first over
breakthrough-first (median effect ~+2 to +4pp across most cells, i.e.
price reaching the "back toward approach side" barrier slightly more
often than the "through the EMA" barrier before the other), but it is
almost always below the 5pp material-effect threshold and rarely survives
BH correction. The strongest single cells were:

- **Strongest rejection tilt**: ES, `RTH_EMA`, EMA20, `FROM_BELOW`,
  `MID_MORNING`: rejection-first 9.2pp above breakthrough-first (n=620,
  raw binomial p=0.008; still `MIXED_OR_NULL` — fails the 4/5-year and
  cross-span-specificity requirements, see below).
- **Strongest breakthrough tilt**: NQ, `FULL_SESSION_EMA`, EMA21,
  `FROM_ABOVE`, `MID_MORNING`: breakthrough-first 7.7pp above
  rejection-first (n=676, p=0.025; `MIXED_OR_NULL` for the same reasons).
- **Strongest/cleanest nulls**: NQ `RTH_EMA` EMA20 `FROM_BELOW` `ALL_RTH`
  (rej-brk = +0.4pp, p=0.83, n=2,620) and ES `RTH_EMA` EMA20 `FROM_ABOVE`
  `ALL_RTH` (rej-brk = +1.4pp, p=0.39, n=3,190).

## EMA20/21/22 specificity

40 specificity cells (`instrument x session_definition x approach_side x
time_stratum`; `reports/tables/ema_specificity_table.csv`). **All 40 are
`GENERIC_EMA_ZONE`** (EMA20, EMA21, and EMA22 are all `MIXED_OR_NULL` with
pairwise effect differences under 5pp in every cell — see `DECISIONS.md`
#11 for how an all-null triple is scored). **Zero cells reached
`EMA21_SPECIFIC`.** Nowhere in the 2018-2022 ES/NQ development sample does
period 21 behave differently from its 20/22 neighbors by the required
margin.

## Same-bar morphology

Same-bar rejection rate hovers close to 50-53% in essentially every cell
(mean 51.2% `FULL_SESSION_EMA`, 51.5% `RTH_EMA`), consistent with the
barrier-outcome result: a slight, non-EMA21-specific rejection lean, not
a strong same-bar effect. Per the permanent caveat (`SPEC_EMA21_LEVELS.md`
§6), this only confirms that 5-minute OHLCV traded through the level; it
does not establish true intrabar sequence.

## Time-of-day

Mean rejection-minus-breakthrough tilt by stratum (pooled across
instrument/span/side, `reports/tables/time_of_day_table.csv`): `MIDDAY`
+4.1pp, `AFTERNOON` +3.2pp, `ALL_RTH` +2.6pp, `OPEN` +1.8pp,
`MID_MORNING` -0.2pp (essentially flat/slightly negative). There is no
stratum where the effect is both materially larger and cleaner than
`ALL_RTH`; if anything the tilt is *weakest* right after the cash open
and in mid-morning, not concentrated there. (Per-stratum `touch_rate`
values can nominally exceed 1.0 due to excursion-start-vs-touch-time
stratum attribution — `KNOWN_LIMITATIONS.md` #10 — this does not affect
the counts or classifications above.)

## RTH_EMA vs. FULL_SESSION_EMA

Both definitions produce materially the same picture: small rejection
lean, no cell reaching directional classification, no EMA21-specific
cell, comparable same-bar rejection rates (51.2% vs. 51.5%). Neither
definition rescues a directional finding the other lacks.

## Year stability (`reports/tables/year_stability.csv`)

Since no primary cell was directionally classified, the year-sign
agreement check (>=4/5 years) was frequently *not* met even where the
pooled 2018-2022 effect looked directionally consistent at first glance —
e.g. the strongest rejection cell above (ES `RTH_EMA` EMA20 `FROM_BELOW`
`MID_MORNING`) had a positive rej-minus-brk effect in only 3 of 5 years.
No systematic 2020-only concentration or single-year dominance was found
driving the pooled tilt; the small rejection lean is present, weakly, in
most years rather than being a 2020-volatility artifact — but it is too
small and inconsistent to pass the joint classification bar in any cell.

## ES vs. NQ agreement

Comparing the 60 matched (`session_definition x span x side x stratum`)
primary-effect pairs, ES and NQ agree on the *sign* of the
rejection-minus-breakthrough tilt in 73.3% of cells (44/60), with a weak
positive cross-instrument correlation (r=0.17) in effect magnitude — a
directionally similar but noisy relationship, consistent with a small,
shared, non-instrument-specific tilt rather than two independently
strong, cleanly-agreeing signals.

## Final report questions

1. **Does the five-minute EMA21 act as a rejection level?** Weakly and
   inconsistently — same-bar and barrier statistics lean rejection
   (~51-55% vs ~45-49%) in most cells, but no cell meets the full
   classification bar (magnitude, significance, sign-consistency, and
   year-stability jointly).
2. **Does it instead act as a breakthrough/continuation threshold?** No —
   breakthrough dominance is not observed anywhere at a classifiable
   level; a handful of cells lean breakthrough (e.g. NQ `FULL_SESSION_EMA`
   EMA21 `FROM_ABOVE` `MID_MORNING`) but none clear the bar either.
3. **Does behavior depend on approach from above versus below?** Both
   sides show the same small rejection lean; no qualitative asymmetry
   between `FROM_ABOVE` and `FROM_BELOW` beyond ordinary sampling noise.
4. **Does behavior differ between RTH-only and full-session EMA
   construction?** No — `RTH_EMA` and `FULL_SESSION_EMA` give materially
   the same (null) picture.
5. **Is any effect concentrated near the cash open or present
   elsewhere?** Not concentrated near the open; if anything `OPEN` and
   `MID_MORNING` show the *weakest* tilt, `MIDDAY`/`AFTERNOON` slightly
   stronger, but none reach a classifiable effect anywhere.
6. **Is the effect stable across 2018-2022?** There is no classified
   "effect" to test for stability; the small pooled tilt does not
   consistently reach 4-of-5-year sign agreement in the cells where it is
   largest.
7. **Is period 21 genuinely special compared with EMA20 and EMA22?** No —
   0/40 specificity cells reached `EMA21_SPECIFIC`; all 40 are
   `GENERIC_EMA_ZONE`.
8. **Does ES agree with NQ?** Loosely — same sign in 73% of matched
   cells, weak magnitude correlation; consistent with a shared, small,
   non-actionable tilt rather than strong independent agreement.
9. **Is there a coherent candidate worth freezing for 2023+ validation?**
   No single cell, span, side, session definition, or time stratum
   produced a `REJECTION_DOMINANT` or `BREAKTHROUGH_DOMINANT`,
   `EMA21_SPECIFIC` result. There is nothing here that clears the
   preregistered bar to freeze for out-of-sample validation.

## Verdict

No supported intraday EMA21 level mechanism was found in ES/NQ
five-minute OHLCV during 2018-2022.

No validation-partition (2023+) study is started as a consequence of this
generation. This matches the preregistered fallback in
`SPEC_EMA21_LEVELS.md` §15 and is not superseded by the marginal, sub-
threshold rejection lean documented above, which failed every joint
classification condition in every one of 120 primary cells and both
EMA20/22 specificity controls in every one of 40 cells.
