# Data Dictionary

## Source: Monthly Processed Parquet

Expected local path: `data/raw/yearly_processed_data/data-YYYY-MM.parquet`

Supported alternate path: `data/raw/monthly_processed_data/data-YYYY-MM.parquet`

| Column | Type | Meaning |
|---|---:|---|
| `station_name` | string | Station name after source processing. |
| `xml_station_name` | string | Station name from the API XML response. |
| `eva` | string | EVA station number, used as a station identifier. |
| `train_name` | string | Train display name, such as `ICE 123` or `RE 5`. |
| `final_destination_station` | string | Final destination of the service. |
| `delay_in_min` | integer | Delay in minutes. Negative values are early arrivals/departures. |
| `time` | timestamp | Actual or changed arrival/departure event time. |
| `is_canceled` | boolean | Whether the stop was canceled. |
| `train_type` | string | Service family, such as `ICE`, `IC`, `RE`, `RB`, `S`, or `Bus`. |
| `train_line_ride_id` | string | Identifier for a train ride. |
| `train_line_station_num` | integer | Stop order in the train's route. |
| `arrival_planned_time` | timestamp | Planned arrival time, if present. |
| `arrival_change_time` | timestamp | Changed arrival time, if present. |
| `departure_planned_time` | timestamp | Planned departure time, if present. |
| `departure_change_time` | timestamp | Changed departure time, if present. |
| `id` | string | Source stop identifier. |

## Clean Table: `stops_clean`

Created by `sql/02_clean_stops.sql`.

| Column | Meaning |
|---|---|
| `stop_id` | Renamed source `id`. |
| `delay_min` | Cleaned delay minutes; extreme values below -60 or above 720 are set to null. |
| `event_time` | Renamed source `time`. |
| `service_date`, `service_year`, `service_month` | Date features from `event_time`. |
| `hour_of_day`, `weekday` | Time-window features from `event_time`. |
| `is_long_distance` | True for ICE/IC/EC-like service types. |
| `is_late_6_min` | True if not canceled and delay is at least 6 minutes. |
| `is_late_15_min` | True if not canceled and delay is at least 15 minutes. |
| `is_late_60_min` | True if not canceled and delay is at least 60 minutes. |

## Feature Tables

| Table | Grain | Use |
|---|---|---|
| `station_day_metrics` | date, station, train type | Station-level trends and hub comparisons. |
| `train_type_day_metrics` | date, train type | National train-family trend lines. |
| `hourly_delay_metrics` | date, weekday, hour, train type | Weekday/hour heatmaps. |
| `line_metrics` | train type, train name, destination | Route/service outlier ranking. |

## Known Gotchas

- The dataset coverage changes over time: the biggest roughly 100 stations are available from 2024-07 to 2025-11-02, then all stations after that. Trend analyses should use a stable station set or explicitly model the coverage change.
- `delay_in_min` is stop-level, not passenger-level. A busy station stop and a small station stop count equally unless weighted later.
- Cancellation and delay metrics are related but not interchangeable. A canceled stop is excluded from late-share flags in the current clean table.
