-- Stage 03: aggregate stops_clean into four analysis-ready feature tables.
--
-- Each table answers a different slice of the project question:
--   station_day_metrics    - station-level daily trends and hub comparisons
--   train_type_day_metrics - national train-family daily trend lines
--   hourly_delay_metrics   - weekday x hour delay patterns
--   line_metrics           - per-line/destination outlier ranking
--
-- Shares (cancellation_share, late_share_*) are AVG of 0/1 flags, so they are
-- bounded in [0, 1]. line_metrics keeps only groups with >= 100 stops so rare
-- lines do not produce noisy rankings.
--
-- Idempotent: CREATE OR REPLACE rebuilds every table from scratch each run.

CREATE OR REPLACE TABLE station_day_metrics AS
SELECT
  service_date,
  station_name,
  eva,
  train_type,
  is_long_distance,
  COUNT(*) AS stop_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) AS avg_delay_min,
  MEDIAN(delay_min) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) AS p90_delay_min,
  AVG(CASE WHEN is_late_6_min THEN 1.0 ELSE 0.0 END) AS late_share_6_min,
  AVG(CASE WHEN is_late_15_min THEN 1.0 ELSE 0.0 END) AS late_share_15_min,
  AVG(CASE WHEN is_late_60_min THEN 1.0 ELSE 0.0 END) AS late_share_60_min
FROM stops_clean
GROUP BY ALL;

CREATE OR REPLACE TABLE train_type_day_metrics AS
SELECT
  service_date,
  train_type,
  is_long_distance,
  COUNT(*) AS stop_count,
  COUNT(DISTINCT station_name) AS station_count,
  COUNT(DISTINCT train_line_ride_id) AS ride_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) AS avg_delay_min,
  MEDIAN(delay_min) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) AS p90_delay_min,
  AVG(CASE WHEN is_late_6_min THEN 1.0 ELSE 0.0 END) AS late_share_6_min,
  AVG(CASE WHEN is_late_15_min THEN 1.0 ELSE 0.0 END) AS late_share_15_min,
  AVG(CASE WHEN is_late_60_min THEN 1.0 ELSE 0.0 END) AS late_share_60_min
FROM stops_clean
GROUP BY ALL;

CREATE OR REPLACE TABLE hourly_delay_metrics AS
SELECT
  service_date,
  weekday,
  hour_of_day,
  train_type,
  is_long_distance,
  COUNT(*) AS stop_count,
  SUM(CASE WHEN is_canceled THEN 1 ELSE 0 END) AS canceled_count,
  AVG(CASE WHEN is_canceled THEN 1.0 ELSE 0.0 END) AS cancellation_share,
  AVG(delay_min) AS avg_delay_min,
  MEDIAN(delay_min) AS median_delay_min,
  AVG(CASE WHEN is_late_6_min THEN 1.0 ELSE 0.0 END) AS late_share_6_min,
  AVG(CASE WHEN is_late_15_min THEN 1.0 ELSE 0.0 END) AS late_share_15_min
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
  AVG(delay_min) AS avg_delay_min,
  MEDIAN(delay_min) AS median_delay_min,
  QUANTILE_CONT(delay_min, 0.9) AS p90_delay_min,
  AVG(CASE WHEN is_late_6_min THEN 1.0 ELSE 0.0 END) AS late_share_6_min,
  AVG(CASE WHEN is_late_15_min THEN 1.0 ELSE 0.0 END) AS late_share_15_min
FROM stops_clean
GROUP BY ALL
HAVING COUNT(*) >= 100;
