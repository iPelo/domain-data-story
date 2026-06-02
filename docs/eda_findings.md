# EDA Findings

`notebooks/01_eda.ipynb` profiles coverage, data quality, delay distributions, train-type behavior, time windows, stations, and route/service outliers. The main point from EDA is that coverage has to be handled before making any trend claim.

## Main Findings

- **Coverage is the first issue to control.** The 2025 local dataset is a 107-station
  panel from January through October, then expands to more than 5,000 stations
  in November and December. Do not treat the November row jump as an operational
  delay event.
- **Stable-station trends are the safer baseline.** Use stations present across
  January-October for trend claims. Use all stations for post-expansion mapping
  and outlier discovery.
- **Long-distance trains are structurally different.** ICE and IC services have
  much higher 6+ minute late share and heavier p90/p99 delay tails than local
  services. They should be analyzed separately from S-Bahn/RB/RE-heavy totals.
- **Cancellation is a separate outcome.** Train types and months with higher
  cancellation share are not always the same ones with higher late share.
- **Time windows matter.** All-service late share is highest around the late
  afternoon/evening window. Long-distance late-night cells are also high, but
  lower volume makes them risky headline claims without sensitivity checks.
- **Station rankings depend on the metric.** Highest late-share station/type
  pairs differ from highest estimated late-stop contribution stations.
- **Route rankings need floors.** `line_metrics` has a 100-stop floor, but the
  EDA uses at least 500 stops for more stable route/service outliers. Phase 4
  should test higher floors for headline rankings.

## Confusing Points Resolved

- The November/December row jump looked like a performance shift. It is the
  documented coverage expansion.
- Extreme delay values exist in the source. The cleaning pipeline keeps the stop
  event but sets `delay_min` outside `[-60, 720]` to null.
- Source timestamps are naive Europe/Berlin wall-clock time. Hour and weekday
  analysis should be interpreted as local traveler-facing time.
- The original project question mentions July 2024, but only 2025 files are
  local right now. Download 2024 files or adjust the final question to 2025.

## Next Analysis Step

Frame the analysis as a descriptive decomposition:

1. Start with stable-station monthly trends.
2. Compare all-station versus stable-station results after the coverage break.
3. Decompose estimated late stops by train type, station, weekday/hour, and
   route/service.
4. Report cancellation separately from delay.
5. Use contribution rankings, not only late-share rankings, for the headline
   operational story.
