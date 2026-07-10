# Reproduction

From `research/vwap_shock/`, with `data/raw/` populated by files matching
the SHA256 hashes in DATA_CONTRACT.md:

```
pip install -r requirements.txt
python -m pytest tests/ -q          # deterministic fixtures (must pass)
python -m src.data_build            # Stage 0 build + audit json
python -m src.run_stage2 ES         # dev-partition features + event ledgers
python -m src.run_stage2 NQ
python -m src.run_analysis          # preregistered Stage 2 tables + registry
```

All randomness is seeded (SEED=20260710 in src/analysis.py). Outputs:
- `outputs/*.parquet` ledgers (git-ignored; reproducible)
- `reports/tables/*.csv` committed summaries
- `RUN_REGISTRY.csv` appended analysis configurations
