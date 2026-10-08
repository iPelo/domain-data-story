# Data and Analysis Notes

## Source and License

- **Dataset:** [`piebro/deutsche-bahn-data`](https://huggingface.co/datasets/piebro/deutsche-bahn-data) on Hugging Face.
- **License:** CC BY 4.0 (Attribution 4.0 International), <https://creativecommons.org/licenses/by/4.0/>.
- **Required attribution:** "Data sourced from Deutsche Bahn's public APIs. Special thanks to Deutsche Bahn for providing open access to this data."
- **Collection:** Built from Deutsche Bahn public APIs (`timetables/v1/plan` and `timetables/v1/fchg`).
- **This project uses** the `monthly_processed_data/` slice (re-published locally under `yearly_processed_data/`); the raw hourly API responses are not used.

## Analysis Scope

The notebooks study 2025. Trend comparisons use stations present in every
month from January through October, before station coverage expands in November.
The dashboard shows all processed data, so it should not be used alone to draw
stable-panel trend conclusions.

## Source: Monthly Processed Parquet

Expected local path: `data/raw/yearly_processed_data/data-YYYY-MM.parquet`

Supported alternate path: `data/raw/monthly_processed_data/data-YYYY-MM.parquet`

| Column | Type | Meaning |
|---|---|---|
| `station_name` | string | Station name after source processing. May be null (~1.2k rows). |
| `xml_station_name` | string | Station name from the API XML response. |
| `eva` | string | EVA station number, used as a station identifier. |
| `train_name` | string | Train display name, such as `ICE 123` or `RE 5`. |
| `final_destination_station` | string | Final destination of the service. |
| `delay_in_min` | integer | Delay in minutes. Negative values are early arrivals/departures. |
| `time` | timestamp (ns) | Actual or changed arrival/departure event time. Naive local (Europe/Berlin) wall-clock time. |
| `is_canceled` | boolean | Whether the stop was canceled. |
| `train_type` | string | Service family, such as `ICE`, `IC`, `RE`, `RB`, `S`, or `Bus`. |
| `train_line_ride_id` | string | Identifier for a train ride. |
| `train_line_station_num` | integer | Stop order in the train's route. |
| `arrival_planned_time` | timestamp (ns) | Planned arrival time, if present. |
| `arrival_change_time` | timestamp (ns) | Changed arrival time, if present. |
| `departure_planned_time` | timestamp (ns) | Planned departure time, if present. |
| `departure_change_time` | timestamp (ns) | Changed departure time, if present. |
| `id` | string | Source stop identifier. Unique per stop event. |

## Clean Table: `stops_clean`

Created by `src/bahn_delay_story/clean_stops.sql`. One row per source stop event that has a
non-null `id` and `time`. Blank strings are normalized to NULL.

| Column | Type | Meaning |
|---|---|---|
| `stop_id` | string | Renamed source `id`. Unique key of the table. |
| `station_name` | string | Trimmed station name; NULL if blank in the source. |
| `xml_station_name` | string | Trimmed XML station name. |
| `eva` | string | EVA station number. |
| `train_name` | string | Trimmed train display name. |
| `final_destination_station` | string | Trimmed final destination. |
| `delay_min` | integer | Cleaned delay minutes; values below -60 or above 720 are set to NULL. |
| `is_canceled` | boolean | Cancellation flag; null source values become `false`. |
| `train_type` | string | Upper-cased service family. |
| `train_line_ride_id` | string | Train ride identifier. |
| `train_line_station_num` | integer | Stop order in the route. |
| `event_time` | timestamp | Renamed source `time` (naive Europe/Berlin local time). |
| `arrival_planned_time` | timestamp | Planned arrival time. |
| `arrival_change_time` | timestamp | Changed arrival time. |
| `departure_planned_time` | timestamp | Planned departure time. |
| `departure_change_time` | timestamp | Changed departure time. |
| `service_date` | date | Calendar date of `event_time`. |
| `service_year`, `service_month` | integer | Year and month of `event_time`. |
| `hour_of_day` | integer | Local hour 0–23 of `event_time`. |
| `weekday` | string | Day of week, `'0'` (Sunday) to `'6'` (Saturday). |
| `is_long_distance` | boolean | True for ICE/IC/EC/ECE/EN/NJ/RJ/RJX/TGV/THA service types. |
| `is_late_6_min` | boolean | True if not canceled and delay is at least 6 minutes. |
| `is_late_15_min` | boolean | True if not canceled and delay is at least 15 minutes. |
| `is_late_60_min` | boolean | True if not canceled and delay is at least 60 minutes. |

## Feature Tables

Created by `src/bahn_delay_story/delay_metrics.sql`.

| Table | Grain | Use |
|---|---|---|
| `station_day_metrics` | date, station, eva, train type | Station-level trends and hub comparisons. |
| `train_type_day_metrics` | date, train type | National train-family trend lines. |
| `hourly_delay_metrics` | date, weekday, hour, train type | Weekday/hour heatmaps. |
| `line_metrics` | train type, train name, destination | Route/service outlier ranking. |

Shared metric columns:

| Column | Meaning |
|---|---|
| `stop_count` | Number of stop events in the group. |
| `canceled_count` | Stops marked canceled. |
| `cancellation_share` | `canceled_count / stop_count`, in [0, 1]. |
| `avg_delay_min`, `median_delay_min` | Mean and median of non-null `delay_min`. |
| `p90_delay_min` | 90th percentile delay (severe tail). Not in `hourly_delay_metrics`. |
| `late_share_6_min`, `late_share_15_min` | Non-canceled stops at least 6 / 15 minutes late divided by all stops, in [0, 1]. |
| `late_share_60_min` | Share at least 60 minutes late. Only in `station_day_metrics` and `train_type_day_metrics`. |
| `station_count`, `ride_count` | Distinct stations / rides in the group (`train_type_day_metrics`, `line_metrics`). |

`line_metrics` keeps only groups with `stop_count >= 100`.

## Known Gotchas

- **Coverage break.** The dataset covers the biggest ~100 stations from 2024-07 to 2025-11-02, then all stations after that. This is visible as the ~2M to ~14M monthly row jump in November. Trend analyses must use a stable station set or explicitly model the coverage change.
- **Stop-level, not passenger-level.** `delay_min` is per stop. A busy hub stop and a tiny halt count equally unless weighted later.
- **Cancellation vs. delay.** They are related but not interchangeable. A canceled stop is excluded from the `is_late_*` flags. It remains in total stop counts and contributes to delay averages when its cleaned delay is non-null.
- **Outlier delays become NULL.** For rows with `delay_in_min` outside [-60, 720], `delay_min` is set to NULL, so the stop still counts toward `stop_count` and cancellation metrics but not delay averages.
- **Time zones.** Source timestamps are naive Europe/Berlin wall-clock time. No UTC conversion is applied; `hour_of_day` and `weekday` are intentionally local clock values.
- **Correlated observations.** One late train produces many delayed stop rows along its route, so stop-level rows are not independent.

The analysis is descriptive. It does not control for weather, strikes,
construction, or passenger demand. Missing API calls can also affect coverage.
