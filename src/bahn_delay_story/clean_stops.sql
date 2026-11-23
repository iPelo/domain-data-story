-- Stage 02: clean raw stop events into stops_clean.
--
-- Real-world mess handled here:
--   * Schema drift   - the pipeline registers monthly_raw with union_by_name,
--                      so columns missing in one month do not break the read.
--                      The source no longer has train_name or is_canceled:
--                      train_name is rebuilt as train_type plus line_number,
--                      falling back to train_number: 'HLB RB21' for a line,
--                      'ICE 823' for a train with no line. Rows with no
--                      train_type, or neither line nor number, get NULL.
--   * Cancellation   - the source flags arrival and departure separately. A stop
--                      counts as cancelled if either is cancelled. This includes
--                      partial cancellations where the train still arrives but
--                      does not depart (or the reverse), so it is a broad
--                      definition; both source flags are kept for narrower ones.
--   * Missingness    - blank strings are normalized to NULL via NULLIF(TRIM(...));
--                      rows with a null id or time are dropped (WHERE clause).
--   * Outliers       - delay_in_min outside [-60, 720] is set to NULL rather
--                      than dropped, so the stop still counts for other metrics.
--   * Unknown delay  - is_late_* flags use the cleaned delay_min. They are NULL
--                      for non-cancelled stops whose delay is missing or out of
--                      range, so they drop out of late-share denominators instead
--                      of counting as on time. Cancelled stops are false.
--   * Encoding       - source Parquet is UTF-8; station names keep their umlauts.
--   * Time zones     - source timestamps are naive Europe/Berlin wall-clock time.
--                      No UTC conversion is applied: hour_of_day and weekday are
--                      meant to read as local clock time for travellers.
--   * Coverage break - the source covers ~100 large stations until November 2025,
--                      then all stations. in_stable_panel marks stops at stations
--                      present in every month January-October 2025, dated within
--                      January-October 2025: the like-for-like trend panel.
--
-- Idempotent: CREATE OR REPLACE rebuilds the table from scratch each run.

CREATE OR REPLACE TABLE stops_clean AS
WITH cleaned AS (
  SELECT
    CAST(id AS VARCHAR) AS stop_id,
    NULLIF(TRIM(station_name), '') AS station_name,
    NULLIF(TRIM(xml_station_name), '') AS xml_station_name,
    CAST(eva AS VARCHAR) AS eva,
    UPPER(NULLIF(TRIM(train_type), '')) || ' '
      || COALESCE(NULLIF(TRIM(line_number), ''), NULLIF(TRIM(train_number), ''))
      AS train_name,
    NULLIF(TRIM(train_number), '') AS train_number,
    NULLIF(TRIM(line_number), '') AS line_number,
    NULLIF(TRIM(final_destination_station), '') AS final_destination_station,
    CASE
      WHEN delay_in_min < -60 OR delay_in_min > 720 THEN NULL
      ELSE CAST(delay_in_min AS INTEGER)
    END AS delay_min,
    COALESCE(arrival_is_canceled, false) OR COALESCE(departure_is_canceled, false)
      AS is_canceled,
    arrival_is_canceled,
    departure_is_canceled,
    is_additional_stop,
    is_replacement_train,
    UPPER(NULLIF(TRIM(replaced_train_type), '')) AS replaced_train_type,
    NULLIF(TRIM(replaced_train_number), '') AS replaced_train_number,
    has_plan_record,
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
    -- Long-distance products. Besides DB and international trains this covers
    -- open-access operators seen in the 2025 data: FLX/DPF (FlixTrain), WB
    -- (WESTbahn), EST (Eurostar, formerly THA/Thalys), ES (European Sleeper),
    -- D (long-distance 'Fern' trains) and UEX (holiday night train). Regional
    -- operator codes (HLB, VIA, SBB, ...) stay false.
    COALESCE(
      UPPER(NULLIF(TRIM(train_type), '')) IN (
        'ICE', 'IC', 'EC', 'ECE', 'EN', 'NJ', 'RJ', 'RJX', 'TGV', 'THA',
        'EST', 'FLX', 'DPF', 'WB', 'ES', 'D', 'UEX'
      ),
      false
    ) AS is_long_distance,
    CASE
      WHEN is_canceled THEN false
      WHEN delay_min IS NULL THEN NULL
      ELSE delay_min >= 6
    END AS is_late_6_min,
    CASE
      WHEN is_canceled THEN false
      WHEN delay_min IS NULL THEN NULL
      ELSE delay_min >= 15
    END AS is_late_15_min,
    CASE
      WHEN is_canceled THEN false
      WHEN delay_min IS NULL THEN NULL
      ELSE delay_min >= 60
    END AS is_late_60_min
  FROM monthly_raw
  WHERE id IS NOT NULL
    AND time IS NOT NULL
),
stable_stations AS (
  SELECT station_name
  FROM cleaned
  WHERE service_year = 2025
    AND service_month BETWEEN 1 AND 10
    AND station_name IS NOT NULL
  GROUP BY station_name
  HAVING COUNT(DISTINCT service_month) = 10
)
SELECT
  cleaned.*,
  stable_stations.station_name IS NOT NULL
    AND cleaned.service_year = 2025
    AND cleaned.service_month BETWEEN 1 AND 10 AS in_stable_panel
FROM cleaned
LEFT JOIN stable_stations ON cleaned.station_name = stable_stations.station_name;
