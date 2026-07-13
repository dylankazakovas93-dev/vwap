# Efficient displacement continuation — frozen 2018–2022 development study

This report is descriptive and contains no trading simulation.

## Answers

1. The answer is determined by the sign, size, and corrected significance of the size-matched efficient-minus-inefficient continuation difference in the primary table.
2. Upward and downward impulses are reported separately.
3. Asia, London, and New York are reported separately.
4. ES/NQ agreement is reported in the cross-market confirmation table.
5. Confirmation is secondary and is not promoted unless the frozen strengthening criteria are met.

## Sample accounting

```
instrument  session                            state    n
        ES     ASIA           EFFICIENT_DISPLACEMENT 4482
        ES     ASIA INEFFICIENT_DISPLACEMENT_CONTROL  143
        ES     ASIA                     INTERMEDIATE 4483
        ES   LONDON           EFFICIENT_DISPLACEMENT 2973
        ES   LONDON INEFFICIENT_DISPLACEMENT_CONTROL   80
        ES   LONDON                     INTERMEDIATE 2675
        ES NEW_YORK           EFFICIENT_DISPLACEMENT 3277
        ES NEW_YORK INEFFICIENT_DISPLACEMENT_CONTROL   82
        ES NEW_YORK                     INTERMEDIATE 3114
        NQ     ASIA           EFFICIENT_DISPLACEMENT 4535
        NQ     ASIA INEFFICIENT_DISPLACEMENT_CONTROL  125
        NQ     ASIA                     INTERMEDIATE 4637
        NQ   LONDON           EFFICIENT_DISPLACEMENT 2969
        NQ   LONDON INEFFICIENT_DISPLACEMENT_CONTROL   51
        NQ   LONDON                     INTERMEDIATE 2757
        NQ NEW_YORK           EFFICIENT_DISPLACEMENT 3597
        NQ NEW_YORK INEFFICIENT_DISPLACEMENT_CONTROL   88
        NQ NEW_YORK                     INTERMEDIATE 3044
```

## Primary results

```
instrument  session  direction  n_efficient  n_inefficient  non_tied  efficient_continuation_rate  inefficient_continuation_rate  difference  p_value  matched_strata classification  q_value
        ES     ASIA         -1         1985             59      2044                     0.442317                       0.440678    0.001639 1.000000              27   UNDERPOWERED      1.0
        ES     ASIA          1         2045             59      2104                     0.460636                       0.389831    0.070805 0.315068              27   UNDERPOWERED      1.0
        ES   LONDON         -1         1333             33      1366                     0.471868                       0.515152   -0.043284 0.753425              15   UNDERPOWERED      1.0
        ES   LONDON          1         1369             30      1399                     0.460190                       0.500000   -0.039810 0.730627              15   UNDERPOWERED      1.0
        ES NEW_YORK         -1         1602             30      1632                     0.473159                       0.500000   -0.026841 0.889311              21   UNDERPOWERED      1.0
        ES NEW_YORK          1         1393             34      1427                     0.491027                       0.529412   -0.038385 0.755324              21   UNDERPOWERED      1.0
        NQ     ASIA         -1         2027             49      2076                     0.475086                       0.551020   -0.075934 0.614039              27   UNDERPOWERED      1.0
        NQ     ASIA          1         2104             59      2163                     0.493346                       0.474576    0.018770 0.904210              27   UNDERPOWERED      1.0
        NQ   LONDON         -1         1300             21      1321                     0.505385                       0.285714    0.219670 0.163384              15   UNDERPOWERED      1.0
        NQ   LONDON          1         1374             19      1393                     0.493450                       0.421053    0.072397 0.721628              15   UNDERPOWERED      1.0
        NQ NEW_YORK         -1         1731             36      1767                     0.512998                       0.527778   -0.014780 0.968903              21   UNDERPOWERED      1.0
        NQ NEW_YORK          1         1580             36      1616                     0.512658                       0.472222    0.040436 0.746425              21   UNDERPOWERED      1.0
```