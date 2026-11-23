-- Stage 03: aggregate stops_clean into analysis-ready feature tables.
--
-- Each table answers a different slice of the project question:
--   station_day_metrics    - station-level daily trends and hub comparisons
--   train_type_day_metrics - national train-family daily trend lines
--   hourly_delay_metrics   - weekday x hour delay patterns
--   line_metrics           - per-line/destination outlier ranking
--   stable_line_metrics    - line_metrics restricted to the stable Jan-Oct panel
--
-- station_day, train_type_day and hourly tables carry in_stable_panel as a
-- grouping column, so filter or sum over it; never read one row per date/type
-- as the whole picture.
--
-- Shares (cancellation_share, late_share_*) are AVG of 0/1 flags, so they are
-- bounded in [0, 1]. Late flags are NULL when a non-cancelled stop has no
-- delay value, so AVG skips those stops: late_share_* = late_count_* /
-- late_eligible_count. Pool rows by summing counts, never by averaging shares.
-- Delay statistics (avg/median/p90) cover non-cancelled stops with a delay
-- value; delay_count is that row count, the weight for pooling averages.
-- line_metrics and stable_line_metrics keep only groups with >= 100 stops so
-- rare lines do not produce noisy rankings.
--
-- Idempotent: CREATE OR REPLACE rebuilds every table from scratch each run.

CREATE OR REPLACE TABLE station_day_metrics AS
SELECT
  service_date,
  station_name,
  eva,
  train_type,
  is_long_distance,
  in_stable_panel,
  COUNT(*) AS stop_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) FILTER (WHERE NOT is_canceled) AS avg_delay_min,
  MEDIAN(delay_min) FILTER (WHERE NOT is_canceled) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) FILTER (WHERE NOT is_canceled) AS p90_delay_min,
  AVG(CAST(is_late_6_min AS DOUBLE)) AS late_share_6_min,
  AVG(CAST(is_late_15_min AS DOUBLE)) AS late_share_15_min,
  AVG(CAST(is_late_60_min AS DOUBLE)) AS late_share_60_min,
  COUNT(delay_min) FILTER (WHERE NOT is_canceled) AS delay_count,
  COUNT(is_late_6_min) AS late_eligible_count,
  COUNT(*) FILTER (WHERE is_late_6_min) AS late_count_6_min,
  COUNT(*) FILTER (WHERE is_late_15_min) AS late_count_15_min,
  COUNT(*) FILTER (WHERE is_late_60_min) AS late_count_60_min
FROM stops_clean
GROUP BY ALL;

CREATE OR REPLACE TABLE train_type_day_metrics AS
SELECT
  service_date,
  train_type,
  is_long_distance,
  in_stable_panel,
  COUNT(*) AS stop_count,
  COUNT(DISTINCT station_name) AS station_count,
  COUNT(DISTINCT train_line_ride_id) AS ride_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) FILTER (WHERE NOT is_canceled) AS avg_delay_min,
  MEDIAN(delay_min) FILTER (WHERE NOT is_canceled) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) FILTER (WHERE NOT is_canceled) AS p90_delay_min,
  AVG(CAST(is_late_6_min AS DOUBLE)) AS late_share_6_min,
  AVG(CAST(is_late_15_min AS DOUBLE)) AS late_share_15_min,
  AVG(CAST(is_late_60_min AS DOUBLE)) AS late_share_60_min,
  COUNT(delay_min) FILTER (WHERE NOT is_canceled) AS delay_count,
  COUNT(is_late_6_min) AS late_eligible_count,
  COUNT(*) FILTER (WHERE is_late_6_min) AS late_count_6_min,
  COUNT(*) FILTER (WHERE is_late_15_min) AS late_count_15_min,
  COUNT(*) FILTER (WHERE is_late_60_min) AS late_count_60_min
FROM stops_clean
GROUP BY ALL;

CREATE OR REPLACE TABLE hourly_delay_metrics AS
SELECT
  service_date,
  weekday,
  hour_of_day,
  train_type,
  is_long_distance,
  in_stable_panel,
  COUNT(*) AS stop_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) FILTER (WHERE NOT is_canceled) AS avg_delay_min,
  MEDIAN(delay_min) FILTER (WHERE NOT is_canceled) AS median_delay_min,
  AVG(CAST(is_late_6_min AS DOUBLE)) AS late_share_6_min,
  AVG(CAST(is_late_15_min AS DOUBLE)) AS late_share_15_min,
  COUNT(delay_min) FILTER (WHERE NOT is_canceled) AS delay_count,
  COUNT(is_late_6_min) AS late_eligible_count,
  COUNT(*) FILTER (WHERE is_late_6_min) AS late_count_6_min,
  COUNT(*) FILTER (WHERE is_late_15_min) AS late_count_15_min
FROM stops_clean
GROUP BY ALL;

CREATE OR REPLACE TABLE line_metrics AS
SELECT
  train_type,
  train_name,
  final_destination_station,
  COUNT(*) AS stop_count,
  COUNT(DISTINCT station_name) AS station_count,
  COUNT(DISTINCT train_line_ride_id) AS ride_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) FILTER (WHERE NOT is_canceled) AS avg_delay_min,
  MEDIAN(delay_min) FILTER (WHERE NOT is_canceled) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) FILTER (WHERE NOT is_canceled) AS p90_delay_min,
  AVG(CAST(is_late_6_min AS DOUBLE)) AS late_share_6_min,
  AVG(CAST(is_late_15_min AS DOUBLE)) AS late_share_15_min,
  COUNT(delay_min) FILTER (WHERE NOT is_canceled) AS delay_count,
  COUNT(is_late_6_min) AS late_eligible_count,
  COUNT(*) FILTER (WHERE is_late_6_min) AS late_count_6_min,
  COUNT(*) FILTER (WHERE is_late_15_min) AS late_count_15_min
FROM stops_clean
GROUP BY ALL
HAVING COUNT(*) >= 100;

CREATE OR REPLACE TABLE stable_line_metrics AS
SELECT
  train_type,
  train_name,
  final_destination_station,
  COUNT(*) AS stop_count,
  COUNT(DISTINCT station_name) AS station_count,
  COUNT(DISTINCT train_line_ride_id) AS ride_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) FILTER (WHERE NOT is_canceled) AS avg_delay_min,
  MEDIAN(delay_min) FILTER (WHERE NOT is_canceled) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) FILTER (WHERE NOT is_canceled) AS p90_delay_min,
  AVG(CAST(is_late_6_min AS DOUBLE)) AS late_share_6_min,
  AVG(CAST(is_late_15_min AS DOUBLE)) AS late_share_15_min,
  COUNT(delay_min) FILTER (WHERE NOT is_canceled) AS delay_count,
  COUNT(is_late_6_min) AS late_eligible_count,
  COUNT(*) FILTER (WHERE is_late_6_min) AS late_count_6_min,
  COUNT(*) FILTER (WHERE is_late_15_min) AS late_count_15_min
FROM stops_clean
WHERE in_stable_panel
GROUP BY ALL
HAVING COUNT(*) >= 100;
