-- Wide, append-only, timestamped rows -- the shape window functions exist
-- for (ordering/ranking/running-totals *within* a partition), as opposed
-- to GROUP BY which collapses rows instead of keeping them alongside their
-- computed value.

DROP TABLE IF EXISTS user_events CASCADE;

CREATE TABLE user_events (
    event_id    SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    session_id  INTEGER NOT NULL,
    event_type  TEXT NOT NULL CHECK (event_type IN ('login', 'page_view', 'add_to_cart', 'purchase', 'logout')),
    event_time  TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_events_user_id ON user_events(user_id);
CREATE INDEX idx_user_events_session_id ON user_events(session_id);
CREATE INDEX idx_user_events_event_time ON user_events(event_time);
