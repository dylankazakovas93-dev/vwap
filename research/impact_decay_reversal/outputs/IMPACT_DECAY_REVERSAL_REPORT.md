# Impact-decay reversal — frozen 2018–2022 development study

No validation or trading simulation was run.

## Plain-English verdict

High diagnostic volume does not add supported predictive information beyond the
observed price stall. All twelve primary cells are `NULL_OR_MIXED`. The largest
raw difference is NQ New York downward: high-volume decay reverses 9.93
percentage points less often than the low-volume stall control, but it is not
BH-significant (q = 0.49795).

## Sample accounting

instrument  session  direction                        state    n
        ES     ASIA         -1            HIGH_VOLUME_DECAY  265
        ES     ASIA         -1 HIGH_VOLUME_PROGRESS_CONTROL 1366
        ES     ASIA         -1     LOW_VOLUME_DECAY_CONTROL  261
        ES     ASIA          1            HIGH_VOLUME_DECAY  306
        ES     ASIA          1 HIGH_VOLUME_PROGRESS_CONTROL 1282
        ES     ASIA          1     LOW_VOLUME_DECAY_CONTROL  331
        ES   LONDON         -1            HIGH_VOLUME_DECAY  196
        ES   LONDON         -1 HIGH_VOLUME_PROGRESS_CONTROL  852
        ES   LONDON         -1     LOW_VOLUME_DECAY_CONTROL  170
        ES   LONDON          1            HIGH_VOLUME_DECAY  197
        ES   LONDON          1 HIGH_VOLUME_PROGRESS_CONTROL  767
        ES   LONDON          1     LOW_VOLUME_DECAY_CONTROL  241
        ES NEW_YORK         -1            HIGH_VOLUME_DECAY  220
        ES NEW_YORK         -1 HIGH_VOLUME_PROGRESS_CONTROL 1125
        ES NEW_YORK         -1     LOW_VOLUME_DECAY_CONTROL  130
        ES NEW_YORK          1            HIGH_VOLUME_DECAY  216
        ES NEW_YORK          1 HIGH_VOLUME_PROGRESS_CONTROL  890
        ES NEW_YORK          1     LOW_VOLUME_DECAY_CONTROL  194
        NQ     ASIA         -1            HIGH_VOLUME_DECAY  244
        NQ     ASIA         -1 HIGH_VOLUME_PROGRESS_CONTROL 1493
        NQ     ASIA         -1     LOW_VOLUME_DECAY_CONTROL  206
        NQ     ASIA          1            HIGH_VOLUME_DECAY  332
        NQ     ASIA          1 HIGH_VOLUME_PROGRESS_CONTROL 1467
        NQ     ASIA          1     LOW_VOLUME_DECAY_CONTROL  279
        NQ   LONDON         -1            HIGH_VOLUME_DECAY  173
        NQ   LONDON         -1 HIGH_VOLUME_PROGRESS_CONTROL  941
        NQ   LONDON         -1     LOW_VOLUME_DECAY_CONTROL  129
        NQ   LONDON          1            HIGH_VOLUME_DECAY  204
        NQ   LONDON          1 HIGH_VOLUME_PROGRESS_CONTROL  856
        NQ   LONDON          1     LOW_VOLUME_DECAY_CONTROL  184
        NQ NEW_YORK         -1            HIGH_VOLUME_DECAY  205
        NQ NEW_YORK         -1 HIGH_VOLUME_PROGRESS_CONTROL 1169
        NQ NEW_YORK         -1     LOW_VOLUME_DECAY_CONTROL  166
        NQ NEW_YORK          1            HIGH_VOLUME_DECAY  230
        NQ NEW_YORK          1 HIGH_VOLUME_PROGRESS_CONTROL  941
        NQ NEW_YORK          1     LOW_VOLUME_DECAY_CONTROL  228

## Primary comparison

instrument  session  direction  n_high_volume_decay  n_low_volume_control  resolved_high  resolved_low  ambiguous_high  ambiguous_low  neither_high  neither_low  incomplete_high  incomplete_low  matched_strata  high_reversal_rate  low_reversal_rate  difference  p_value  q_value classification
        ES     ASIA         -1                  265                   261            234           242               0              1            28            8                3              10              13            0.521368           0.561983   -0.040616 0.501450  1.00000  NULL_OR_MIXED
        ES     ASIA          1                  306                   331            248           298               0              1            49           25                9               7              24            0.500000           0.510067   -0.010067 0.999800  1.00000  NULL_OR_MIXED
        ES   LONDON         -1                  196                   170            180           158               0              1             9            3                7               8               5            0.533333           0.531646    0.001688 1.000000  1.00000  NULL_OR_MIXED
        ES   LONDON          1                  197                   241            169           219               0              0            18            6               10              16              11            0.479290           0.497717   -0.018427 0.255674  1.00000  NULL_OR_MIXED
        ES NEW_YORK         -1                  220                   130            196           118               0              0            14            1               10              11               4            0.494898           0.500000   -0.005102 1.000000  1.00000  NULL_OR_MIXED
        ES NEW_YORK          1                  216                   194            195           179               1              0            18           10                2               5               8            0.441026           0.480447   -0.039421 0.939406  1.00000  NULL_OR_MIXED
        NQ     ASIA         -1                  244                   206            208           190               1              2            28            9                7               5              10            0.480769           0.521053   -0.040283 0.499750  1.00000  NULL_OR_MIXED
        NQ     ASIA          1                  332                   279            264           250               0              1            60           16                8              12              11            0.458333           0.472000   -0.013667 0.411659  1.00000  NULL_OR_MIXED
        NQ   LONDON         -1                  173                   129            154           121               0              0            11            4                8               4               6            0.441558           0.487603   -0.046045 0.503550  1.00000  NULL_OR_MIXED
        NQ   LONDON          1                  204                   184            167           167               0              2            31            6                6               9               8            0.514970           0.526946   -0.011976 1.000000  1.00000  NULL_OR_MIXED
        NQ NEW_YORK         -1                  205                   166            177           150               1              1            18            3                9              12               9            0.440678           0.540000   -0.099322 0.041496  0.49795  NULL_OR_MIXED
        NQ NEW_YORK          1                  230                   228            202           208               0              0            24            9                4              11               6            0.425743           0.456731   -0.030988 1.000000  1.00000  NULL_OR_MIXED

Adjacent horizons: `adjacent_horizon_table.csv`. Supporting control: `high_volume_progress_control.csv`. Year stability: `year_stability_table.csv`. Cross-market diagnostics: `cross_market_confirmation_table.csv`. 
