SELECT
    session_id,
    event_type,
    event_time,
    EXTRACT(EPOCH FROM (
        event_time - LAG(event_time) OVER (PARTITION BY session_id ORDER BY event_time)
    )) AS seconds_since_prev
FROM user_events
ORDER BY session_id, event_time;
