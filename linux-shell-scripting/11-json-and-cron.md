# 11 — Working with JSON (`jq`) and Scheduling (`cron`)

## Working with JSON — `jq` basics

Scripts constantly deal with an API or CLI tool that outputs JSON (a
`curl` response, `kubectl get pod -o json`, `aws ... --output json`).
`grep`/`sed`/`awk` are line-oriented and awkward on JSON's structure;
`jq` is a filter built specifically for it — same "small tool in a
pipeline" idea as `grep`/`sort` from
[03 — Files and Text Processing](03-files-and-text-processing.md), just
JSON-shaped instead of line-shaped:

```bash
echo '{"name":"web1","status":"healthy","port":8080}' | jq '.name'        # "web1" (quoted string)
echo '{"name":"web1","status":"healthy","port":8080}' | jq -r '.name'     # web1 (raw, unquoted — what you want in a script variable)

curl -s https://api.example.com/hosts | jq -r '.[] | .name'     # pull a field out of every element of a JSON array
curl -s https://api.example.com/status | jq -e '.status == "ok"'   # -e: exit code reflects the filter's boolean result — usable directly in an `if`
```

The pattern that shows up constantly in real scripts: fetch, filter with
`jq -r`, capture with `$(...)`, use like any other shell variable:

```bash
status=$(curl -s "https://api.example.com/health" | jq -r '.status')
if [ "$status" != "ok" ]; then
    echo "ERROR: service unhealthy (status=$status)" >&2
    exit 1
fi
```

## Scheduling — running a script unattended (cron)

Back in "the problem it solves"
([01 — Introduction and Mental Model](01-introduction-and-mental-model.md)):
a script's real payoff is running with no human present. `cron` is the
standard Linux scheduler for that — a background daemon that reads a
crontab (a list of "run this at these times" rules) and executes each
script when its time comes.

```bash
crontab -e     # open your crontab in an editor
crontab -l     # list your current scheduled jobs
```

A crontab line has five time fields, then the command:

```
# minute  hour  day-of-month  month  day-of-week   command
   0       2      *            *      *             /home/you/backup_and_alert.sh /data /backups >> /var/log/backup.log 2>&1
  */15     *      *            *      *             /home/you/health_check.sh
   0       9      *            *      1-5            /home/you/weekday_report.sh
```

Read the first one as "at minute 0 of hour 2, every day, every month,
every weekday" — i.e. 2:00 AM daily. `*` means "every value of this
field"; `*/15` means "every 15 units." Two habits matter for any real
cron job: **always redirect output** (`>> logfile 2>&1`) since cron
normally only emails failures and often that's not configured, and
**always use absolute paths** inside the script and for the script
itself — cron runs with a minimal environment, not your interactive
shell's `$PATH` or working directory.

**Run it:** [`examples/11_jq_and_cron_demo.sh`](examples/11_jq_and_cron_demo.sh)
runs the `jq` examples above (skipping the live-API call cleanly if
you're offline) and prints the crontab line that would schedule itself
every 15 minutes with output logged to a file.

```bash
./examples/11_jq_and_cron_demo.sh
```

---
**Previous:** [10 — Error Handling and Debugging](10-error-handling-and-debugging.md) · **Next:** [12 — Worked Examples and Real-World References](12-worked-examples-and-real-world.md)
