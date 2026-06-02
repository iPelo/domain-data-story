-- Convenience view for interactive DuckDB sessions launched from the repo root.
-- Your current files live in yearly_processed_data; this glob also supports
-- monthly_processed_data if you later use that source naming variant.

CREATE OR REPLACE VIEW monthly_raw AS
SELECT *
FROM read_parquet('data/raw/*_processed_data/data-*.parquet', union_by_name = true);
