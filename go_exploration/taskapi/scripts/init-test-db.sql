-- Runs once, on first start of an empty Postgres volume.
-- Integration tests TRUNCATE tables, so they get their own database and
-- never wipe the data you're playing with through the running API.
CREATE DATABASE taskapi_test OWNER taskapi;
