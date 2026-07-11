# KNOWN_LIMITATIONS.md — generation 6

1. Descriptive taxonomy only; no class here is a signal, predictor, or
   tradable edge. Part 1 explicitly excludes level-reaction testing,
   profitability metrics, and entries/exits.
2. Development partition only (2018-2022); validation/holdout untouched.
3. Same-bar proxy labels are morphology-based, not a verified
   reconstruction of intrabar order (permanent caveat, SPEC_TAXONOMY.md
   Sec. 3.2) — carried on every relevant row and table.
4. `τ_c=1.0`, `τ_d=0`, `τ_b=0.15`, `N=15` are fixed design choices with
   declared sensitivity grids for `τ_c`/`τ_b`; `τ_d` and `N` do not have
   dedicated sensitivity grids in this Part-1 pass (a fixed value each,
   per SPEC_TAXONOMY.md) — flagged as a scope limitation, not tuned.
5. The excursion ladder is capped at `tau=59` (10:30 ET); sessions whose
   interesting excursion develops after 10:30 ET are not captured further.
6. `scale_U(s)`/`scale_D(s)` require 20+ prior valid sessions; the first
   ~20-60 development sessions have undefined normalized quantities and
   are excluded from those cells (not imputed).
7. Roll-week sessions are not excluded (consistent with prior generations'
   policy).
8. `LATER_OPPOSITE_SIDE_TAKEOVER` vs `LATER_ORDERED_REVERSAL_AFTER_PROXY`
   depends on a clean-hold definition that may be sensitive to bar-to-bar
   noise in `Q(t)` near zero; no smoothing is applied (consistent with the
   project's discipline against introducing untested transformations).
