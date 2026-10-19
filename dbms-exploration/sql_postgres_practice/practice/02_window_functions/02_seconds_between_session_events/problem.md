# 2. Seconds Between Consecutive Events In a Session

**Fixture:** `event_log`
**Pattern:** `LAG() OVER (PARTITION BY ... ORDER BY ...)`

## Problem

For every event, compute how many seconds elapsed since the *previous*
event in the same session. The first event of a session has no previous
event — it should show `NULL`, not `0`.

## Why this needs `LAG`, not a self-join

"The previous row for this row, within this session" is exactly what
`LAG` computes directly — the alternative (a self-join on
`session_id` matching and some "next event_time after this one" condition)
works but is both harder to write correctly and much more expensive to
execute. See `../../docs/03_window_functions.md`'s `LAG`/`LEAD` section.

## Expected output (session 1 only, for brevity — the real query covers every session)

```
 session_id | event_type  |     event_time      | seconds_since_prev
------------+-------------+---------------------+---------------------
          1 | login       | 2026-03-01 09:00:00 |
          1 | page_view   | 2026-03-01 09:01:00 |             60
          1 | page_view   | 2026-03-01 09:03:00 |            120
          1 | add_to_cart | 2026-03-01 09:05:00 |            120
          1 | purchase    | 2026-03-01 09:07:00 |            120
          1 | logout      | 2026-03-01 09:08:00 |             60
```

## Solution

See `solution.sql` in this folder. `EXTRACT(EPOCH FROM interval)` converts
a Postgres interval (the result of subtracting two timestamps) into a
plain number of seconds.
