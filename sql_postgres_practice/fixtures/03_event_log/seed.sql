-- 10 sessions across 5 users, spread over a week. Deliberately includes:
--   - a browse-only session with no purchase (session 2)
--   - a cart-abandonment session: add_to_cart with no purchase (session 7)
--   - sessions of different lengths (2 events up to 8 events)
-- so funnel/conversion-style queries have real variation to find.

INSERT INTO user_events (user_id, session_id, event_type, event_time) VALUES
-- session 1: user 1, full funnel including purchase
(1, 1, 'login',        '2026-03-01 09:00:00'),
(1, 1, 'page_view',    '2026-03-01 09:01:00'),
(1, 1, 'page_view',    '2026-03-01 09:03:00'),
(1, 1, 'add_to_cart',  '2026-03-01 09:05:00'),
(1, 1, 'purchase',     '2026-03-01 09:07:00'),
(1, 1, 'logout',       '2026-03-01 09:08:00'),

-- session 2: user 1, browse only, no purchase
(1, 2, 'login',        '2026-03-03 14:00:00'),
(1, 2, 'page_view',    '2026-03-03 14:02:00'),
(1, 2, 'logout',       '2026-03-03 14:05:00'),

-- session 3: user 2, longest session, two add_to_cart before purchasing
(2, 3, 'login',        '2026-03-01 10:00:00'),
(2, 3, 'page_view',    '2026-03-01 10:01:00'),
(2, 3, 'page_view',    '2026-03-01 10:04:00'),
(2, 3, 'page_view',    '2026-03-01 10:08:00'),
(2, 3, 'add_to_cart',  '2026-03-01 10:10:00'),
(2, 3, 'add_to_cart',  '2026-03-01 10:12:00'),
(2, 3, 'purchase',     '2026-03-01 10:15:00'),
(2, 3, 'logout',       '2026-03-01 10:16:00'),

-- session 4: user 3, very short, just looked and left
(3, 4, 'login',        '2026-03-02 08:00:00'),
(3, 4, 'page_view',    '2026-03-02 08:02:00'),
(3, 4, 'logout',       '2026-03-02 08:03:00'),

-- session 5: user 3, returns two days later and buys
(3, 5, 'login',        '2026-03-04 16:00:00'),
(3, 5, 'page_view',    '2026-03-04 16:01:00'),
(3, 5, 'add_to_cart',  '2026-03-04 16:05:00'),
(3, 5, 'purchase',     '2026-03-04 16:07:00'),
(3, 5, 'logout',       '2026-03-04 16:08:00'),

-- session 6: user 4, browse only
(4, 6, 'login',        '2026-03-02 11:00:00'),
(4, 6, 'page_view',    '2026-03-02 11:02:00'),
(4, 6, 'page_view',    '2026-03-02 11:05:00'),
(4, 6, 'logout',       '2026-03-02 11:10:00'),

-- session 7: user 5, classic cart abandonment
(5, 7, 'login',        '2026-03-05 09:30:00'),
(5, 7, 'page_view',    '2026-03-05 09:32:00'),
(5, 7, 'add_to_cart',  '2026-03-05 09:35:00'),
(5, 7, 'logout',       '2026-03-05 09:40:00'),

-- session 8: user 2, second purchase later in the week
(2, 8, 'login',        '2026-03-06 13:00:00'),
(2, 8, 'page_view',    '2026-03-06 13:01:00'),
(2, 8, 'page_view',    '2026-03-06 13:03:00'),
(2, 8, 'add_to_cart',  '2026-03-06 13:06:00'),
(2, 8, 'purchase',     '2026-03-06 13:10:00'),
(2, 8, 'logout',       '2026-03-06 13:11:00'),

-- session 9: user 1, fastest purchase (login to purchase in 6 minutes)
(1, 9, 'login',        '2026-03-07 10:00:00'),
(1, 9, 'page_view',    '2026-03-07 10:02:00'),
(1, 9, 'add_to_cart',  '2026-03-07 10:04:00'),
(1, 9, 'purchase',     '2026-03-07 10:06:00'),
(1, 9, 'logout',       '2026-03-07 10:07:00'),

-- session 10: user 4, returns and converts
(4, 10, 'login',        '2026-03-08 15:00:00'),
(4, 10, 'page_view',    '2026-03-08 15:02:00'),
(4, 10, 'page_view',    '2026-03-08 15:05:00'),
(4, 10, 'add_to_cart',  '2026-03-08 15:08:00'),
(4, 10, 'purchase',     '2026-03-08 15:10:00'),
(4, 10, 'logout',       '2026-03-08 15:12:00');
