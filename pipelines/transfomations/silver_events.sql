-- 1. Розбір і валідація (дублікати тут ще є)
CREATE OR REFRESH STREAMING TABLE silver_events_clean (
  CONSTRAINT valid_event_id   EXPECT (event_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_event_ts   EXPECT (event_ts IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_user_id    EXPECT (user_id IS NOT NULL)  ON VIOLATION DROP ROW,
  CONSTRAINT valid_event_type EXPECT (event_type IN ('tour_shown','step_viewed','step_completed',
                                                     'tour_dismissed','tour_completed','cta_clicked'))
                              ON VIOLATION DROP ROW,
  CONSTRAINT no_rescued_data  EXPECT (_rescued_data IS NULL)          -- тільки попередження
)
COMMENT 'Validated, flattened tour events (may still contain duplicates)'
AS SELECT
  event_id,
  try_cast(event_ts AS TIMESTAMP)          AS event_ts,
  to_date(try_cast(event_ts AS TIMESTAMP)) AS event_date,
  user_id, account_id, session_id, event_type, tour_id,
  CAST(step_number AS INT)                 AS step_number,
  experiment_variant,
  properties.device.os                     AS device_os,
  properties.device.browser                AS device_browser,
  properties.page_url                      AS page_url,
  properties.locale                        AS locale,
  _rescued_data, source_file, ingested_at
FROM STREAM(bronze_events);

-- 2. Quarantine: те, що не пройшло перевірки, з причиною
CREATE OR REFRESH STREAMING TABLE silver_events_quarantine
COMMENT 'Rejected events with reject reasons'
AS SELECT * FROM (
  SELECT *,
    concat_ws(', ',
      CASE WHEN event_id IS NULL                         THEN 'missing_event_id'   END,
      CASE WHEN try_cast(event_ts AS TIMESTAMP) IS NULL  THEN 'invalid_event_ts'   END,
      CASE WHEN user_id IS NULL                          THEN 'missing_user_id'    END,
      CASE WHEN NOT coalesce(event_type IN ('tour_shown','step_viewed','step_completed',
                                            'tour_dismissed','tour_completed','cta_clicked'), false)
                                                         THEN 'unknown_event_type' END
    ) AS reject_reason
  FROM STREAM(bronze_events)
)
WHERE reject_reason <> '';

-- 3. Дедуплікація: один рядок на event_id
CREATE OR REFRESH STREAMING TABLE silver_events
COMMENT 'Deduplicated tour events, one row per event_id';

CREATE FLOW silver_events_dedup AS AUTO CDC INTO silver_events
FROM STREAM(silver_events_clean)
KEYS (event_id)
SEQUENCE BY ingested_at
STORED AS SCD TYPE 1;