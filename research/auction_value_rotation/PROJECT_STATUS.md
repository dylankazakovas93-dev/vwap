# PROJECT_STATUS.md — auction value reacceptance and rotation engine

Branch: research/auction-value-rotation-engine (base 201896d)
Research generation: independent (auction-value failed-discovery / reacceptance / rotation mechanism study)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code (`2bf11ee`) |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — done during preregistration, see `DATA_CONTRACT.md` |
| Profile construction engine (3 models x 3 bins x 3 VA%) | COMPLETE | PASS — 9 hand-calculated unit tests |
| Event state machine + master excursion/acceptance ledger | COMPLETE | PASS — 10 unit tests incl. independent-scan spot-check |
| Outcomes + controls engine | COMPLETE | PASS — tz-bug and control-definition bug found and fixed via tests before real data |
| Test suite (required coverage list) | COMPLETE | PASS — 71 tests passing |
| Development grid run + candidate selection | COMPLETE | 1 qualifying family (`M2_LONDON_TO_NY`, short, `R1_ONE_CLOSE`), 6 parameter rows, all 12 criteria |
| CANDIDATE_MANIFEST.md (or NO_CANDIDATE) | COMPLETE | Committed and pushed separately (`cfba108`) before OOS pipeline existed |
| OOS evaluation (only if a candidate qualifies) | COMPLETE | **FAIL** — all 6 rows fail; effect shrank from +17.4pp dev to +2.6pp OOS, p=0.83 |
| Final report | COMPLETE | See `AUCTION_VALUE_ROTATION_REPORT.md` |

**Final verdict: NULL.** The auction-value reacceptance/rotation mechanism,
as operationalized by this engine, does not survive out-of-sample
evaluation on NQ 2019/2021/2023/2025. ES was not evaluated (see
`KNOWN_LIMITATIONS.md` #14).
