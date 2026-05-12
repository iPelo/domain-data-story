CREATE OR REPLACE TABLE stops_clean AS
SELECT
  CAST(id AS VARCHAR) AS stop_id,
  NULLIF(TRIM(station_name), '') AS station_name,
  NULLIF(TRIM(xml_station_name), '') AS xml_station_name,
  CAST(eva AS VARCHAR) AS eva,
  NULLIF(TRIM(train_name), '') AS train_name,
  NULLIF(TRIM(final_destination_station), '') AS final_destination_station,
  CASE
    WHEN delay_in_min < -60 OR delay_in_min > 720 THEN NULL
    ELSE CAST(delay_in_min AS INTEGER)
  END AS delay_min,
  COALESCE(CAST(is_canceled AS BOOLEAN), false) AS is_canceled,
  UPPER(NULLIF(TRIM(train_type), '')) AS train_type,
  CAST(train_line_ride_id AS VARCHAR) AS train_line_ride_id,
  CAST(train_line_station_num AS INTEGER) AS train_line_station_num,
  CAST(time AS TIMESTAMP) AS event_time,
  CAST(arrival_planned_time AS TIMESTAMP) AS arrival_planned_time,
  CAST(arrival_change_time AS TIMESTAMP) AS arrival_change_time,
  CAST(departure_planned_time AS TIMESTAMP) AS departure_planned_time,
  CAST(departure_change_time AS TIMESTAMP) AS departure_change_time,
  CAST(DATE_TRUNC('day', time) AS DATE) AS service_date,
  EXTRACT(YEAR FROM time) AS service_year,
  EXTRACT(MONTH FROM time) AS service_month,
  EXTRACT(HOUR FROM time) AS hour_of_day,
  STRFTIME(time, '%w') AS weekday,
  CASE
    WHEN UPPER(NULLIF(TRIM(train_type), '')) IN ('ICE', 'IC', 'EC', 'ECE', 'EN', 'NJ', 'RJ', 'RJX', 'TGV', 'THA')
      THEN true
    ELSE false
  END AS is_long_distance,
  CASE
    WHEN COALESCE(CAST(is_canceled AS BOOLEAN), false) THEN false
    WHEN delay_in_min >= 6 THEN true
    ELSE false
  END AS is_late_6_min,
  CASE
    WHEN COALESCE(CAST(is_canceled AS BOOLEAN), false) THEN false
    WHEN delay_in_min >= 15 THEN true
    ELSE false
  END AS is_late_15_min,
  CASE
    WHEN COALESCE(CAST(is_canceled AS BOOLEAN), false) THEN false
    WHEN delay_in_min >= 60 THEN true
    ELSE false
  END AS is_late_60_min
FROM monthly_raw
WHERE id IS NOT NULL
  AND time IS NOT NULL;
