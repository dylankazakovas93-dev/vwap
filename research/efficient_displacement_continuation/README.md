# Efficient displacement continuation

Run the frozen fixture tests with:

```sh
python3 -m pytest -q research/efficient_displacement_continuation/tests
```

Run the development study with the external upload root:

```sh
python3 research/efficient_displacement_continuation/src/run_study.py \
  --data-root /Users/mariusvidziunas/Downloads/quant-data-upload
```

The engine uses only ES/NQ source archives named in `DATA_CONTRACT.md`, applies
the causal front-month construction, and hard-filters the development period at
2022-12-31. Large event ledgers are intentionally ignored by Git; compact
reports and tables in `outputs/` are the audit artifacts.
