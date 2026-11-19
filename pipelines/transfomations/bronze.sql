-- Події: append-only, як прийшли
CREATE OR REFRESH STREAMING TABLE bronze_events
COMMENT 'Raw product tour events, append-only'
AS SELECT *,
       _metadata.file_name AS source_file,
       current_timestamp()  AS ingested_at
FROM STREAM read_files(
  '/Volumes/workspace/product_tours/landing/events/',
  format => 'json',
  rescuedDataColumn => '_rescued_data'
);

-- Зміни акаунтів: кожен файл містить зміни за день
CREATE OR REFRESH STREAMING TABLE bronze_accounts
COMMENT 'Raw account plan changes'
AS SELECT *,
       _metadata.file_name AS source_file,
       current_timestamp()  AS ingested_at
FROM STREAM read_files(
  '/Volumes/workspace/product_tours/landing/accounts/',
  format => 'csv',
  header => true,
  rescuedDataColumn => '_rescued_data'
);

-- Довідник турів: один файл, який перезаписується
CREATE OR REFRESH MATERIALIZED VIEW bronze_tours
COMMENT 'Tours reference data'
AS SELECT *, _metadata.file_name AS source_file
FROM read_files(
  '/Volumes/workspace/product_tours/landing/tours/',
  format => 'csv',
  header => true
);