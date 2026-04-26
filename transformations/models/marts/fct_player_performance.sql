-- models/marts/fct_player_performance.sql

{{ config(materialized='table') }}

WITH raw_pbp AS (
    SELECT * FROM {{ source('ncaa', 'play_by_play') }}
),

player_stats AS (
    SELECT
        player,
        batting_team,
        source_team,
        COUNT(*) as total_at_bats,
        SUM(CASE WHEN is_hit = 1 THEN 1 ELSE 0 END) as total_hits,
        SUM(CASE WHEN hit_type = 'home_run' THEN 1 ELSE 0 END) as total_hr
    FROM raw_pbp
    WHERE hit_location != 'Unknown'
    GROUP BY 1, 2, 3
)

SELECT
    *,
    CAST(total_hits AS FLOAT) / NULLIF(total_at_bats, 0) as batting_average
FROM player_stats
ORDER BY batting_average DESC
