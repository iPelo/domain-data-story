# Methodology

## Analytical Scope

This project uses the monthly processed `piebro/deutsche-bahn-data` Parquet files. The files are already structured for stop-level analysis, which keeps the project focused on cleaning, validation, and interpretation rather than API collection.

The analysis scope is fixed to 2025. Headline trend claims use the stable station panel from January through October. November and December are kept for post-expansion views, but not for before/after trend conclusions.

The live DB Timetables API remains useful for:

- validating individual station examples
- adding a small current-day appendix
- showing how the historical dataset was generated

It is not the primary source for this analysis because historical crawling would add credentials, rate limits, and reproducibility problems without improving the current 2025 question.

## Metrics

Primary metrics:

- `late_share_6_min`: share of non-canceled stops at least 6 minutes late
- `avg_delay_min`: average stop-level delay
- `median_delay_min`: median stop-level delay
- `p90_delay_min`: 90th percentile stop-level delay
- `late_share_15_min`: share of non-canceled stops at least 15 minutes late
- `cancellation_share`: share of stops marked canceled

Use `late_share_6_min` for punctuality and `p90_delay_min` for severe tail delay. Keep cancellations separate.

## Analysis Plan

1. Profile coverage by month, station, and train type.
2. Decide whether the main trend chart should use only the stable station subset.
3. Compare ICE/IC/EC-like services against regional and S-Bahn services.
4. Decompose changes by station, train type, weekday, and hour.
5. Rank station-hour segments by their contribution to added late stops.

## Coverage Strategy

Because the source dataset expands from the biggest roughly 100 stations to all stations after 2025-11-02, raw national trend lines can be misleading. Use one of these strategies:

- Main analysis: restrict to stations present before and after the coverage change.
- Secondary analysis: show all stations, but annotate the coverage expansion.
- Sensitivity check: compare results for all stops versus stable-station stops.

## Limitations

- Stop-level data does not measure passenger impact directly.
- The project does not yet control for weather, strikes, construction, or special events.
- The source data is derived from public API responses, so missing API calls or schema changes can affect coverage.
- Delay at each stop is not independent because one late train creates multiple delayed stop observations.
