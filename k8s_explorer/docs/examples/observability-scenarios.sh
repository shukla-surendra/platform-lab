#!/bin/bash

# Observability Incident Simulation Scripts
# Run these to practice diagnosing different failure modes

set -e

NAMESPACE="observability"
APP="rsa-rust-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# SCENARIO 1: HIGH LATENCY (API is slow)
# ============================================================================

scenario_high_latency() {
    echo -e "${YELLOW}=== SCENARIO 1: High Latency ===${NC}"
    echo "Simulating slow API responses (artificial delay)"
    echo ""
    echo "What you should observe:"
    echo "  1. Request rate graph stays same (same traffic)"
    echo "  2. Latency (if available) increases"
    echo "  3. CPU might increase if the delay is computational"
    echo "  4. No ERROR logs (request succeeds, just slow)"
    echo ""
    echo "How to diagnose:"
    echo "  1. Check metrics: is CPU maxed out or not?"
    echo "  2. Check logs: any ERROR or WARN lines?"
    echo "  3. If CPU is low but latency is high → blocked on I/O (DB, network, etc.)"
    echo "  4. If CPU is high → code optimization needed"
    echo ""

    # Generate slow requests
    echo -e "${GREEN}Generating 30 requests with 1.5s delay each...${NC}"
    for i in {1..30}; do
        curl -s "http://localhost:8080/delay?seconds=1.5" > /dev/null &
    done
    wait

    echo -e "${GREEN}Done. Check Grafana dashboards for latency impact.${NC}"
    echo "  → Health & Requests dashboard: look at request rate and CPU panels"
    echo "  → Logs dashboard: search for ERROR or high latency"
    echo ""
}

# ============================================================================
# SCENARIO 2: POD CRASH LOOP
# ============================================================================

scenario_crash_loop() {
    echo -e "${YELLOW}=== SCENARIO 2: Pod Crash Loop ===${NC}"
    echo "Simulating pod crash by forcing a restart"
    echo ""
    echo "What you should observe:"
    echo "  1. Pod restarts counter increments in metrics"
    echo "  2. Request rate drops to zero for ~10s"
    echo "  3. Logs stop, then resume"
    echo "  4. No application logs before restart (unless exit message)"
    echo ""
    echo "How to diagnose:"
    echo "  1. Check metrics: restart count incrementing? How fast?"
    echo "  2. Run: kubectl -n observability logs -l app=rust-api --previous"
    echo "  3. Check events: kubectl -n observability describe pod -l app=rust-api"
    echo "  4. If logs are empty, check exit code in events (OOMKilled, exit code 1, etc.)"
    echo ""

    echo -e "${GREEN}Deleting pod to force restart...${NC}"
    kubectl -n observability delete pod -l app=rust-api --wait=false

    echo "Waiting 15 seconds for pod to restart..."
    sleep 15

    echo -e "${GREEN}Done. Check Grafana for restart counter and downtime.${NC}"
    echo "  → Health & Requests dashboard: pod restarts counter (top right)"
    echo "  → Request rate dip while pod was down"
    echo ""
}

# ============================================================================
# SCENARIO 3: MEMORY PRESSURE / LEAK
# ============================================================================

scenario_memory_pressure() {
    echo -e "${YELLOW}=== SCENARIO 3: Memory Pressure ===${NC}"
    echo "Simulating memory-intensive operations"
    echo ""
    echo "What you should observe:"
    echo "  1. Memory usage graph climbs"
    echo "  2. CPU might also increase (memory allocation/GC work)"
    echo "  3. Eventually pod might be OOMKilled if it hits the limit"
    echo ""
    echo "How to diagnose:"
    echo "  1. Check metrics: is memory climbing steadily or in spikes?"
    echo "  2. Steady climb = potential leak. Spikes = normal allocation patterns"
    echo "  3. Check pod limits: kubectl -n observability describe pod -l app=rust-api"
    echo "  4. If OOMKilled, check if app is leaking or if limit is too low"
    echo ""

    echo -e "${GREEN}Making memory-heavy requests (allocating large objects)...${NC}"
    for i in {1..10}; do
        curl -s "http://localhost:8080/heavy?size=100000" > /dev/null &
    done
    wait

    echo -e "${GREEN}Done. Check memory usage on metrics dashboard.${NC}"
    echo "  → Health & Requests dashboard: Memory Usage panel (top row, right)"
    echo ""
}

# ============================================================================
# SCENARIO 4: ERROR SPIKE (Broken endpoint or bad database)
# ============================================================================

scenario_error_spike() {
    echo -e "${YELLOW}=== SCENARIO 4: Error Rate Spike ===${NC}"
    echo "Simulating application errors"
    echo ""
    echo "What you should observe:"
    echo "  1. Request rate might stay same or drop"
    echo "  2. Status code breakdown: 5xx (server error) goes up"
    echo "  3. ERROR level logs appear"
    echo "  4. Error messages in log JSON (if structured)"
    echo ""
    echo "How to diagnose:"
    echo "  1. Check metrics: error rate (request rate with status=5xx)"
    echo "  2. Check logs: filter by level=ERROR, look for error messages"
    echo "  3. Look for stack traces or exception details"
    echo "  4. Check if it's affecting a specific endpoint or all requests"
    echo ""

    echo -e "${GREEN}Generating burst of requests that might error...${NC}"
    curl -X POST "http://localhost:8080/debug/random-logs"

    echo -e "${GREEN}Done. Check logs dashboard for errors.${NC}"
    echo "  → Logs dashboard: ERROR panel (filter by level=ERROR)"
    echo "  → Logs dashboard: search for 'ERROR' or status code 500"
    echo ""
}

# ============================================================================
# SCENARIO 5: TRAFFIC SPIKE (Legitimate high load)
# ============================================================================

scenario_traffic_spike() {
    echo -e "${YELLOW}=== SCENARIO 5: Traffic Spike ===${NC}"
    echo "Simulating sudden increase in legitimate traffic"
    echo ""
    echo "What you should observe:"
    echo "  1. Request rate goes up significantly"
    echo "  2. CPU increases proportionally"
    echo "  3. Memory might increase (if requests allocate memory)"
    echo "  4. All requests succeed (status 200)"
    echo "  5. No ERROR logs"
    echo ""
    echo "How to diagnose:"
    echo "  1. Metrics show request rate + CPU together: normal scaling"
    echo "  2. Metrics diverge (high rate, low CPU): something is wrong"
    echo "  3. Check if the service can handle the load"
    echo "  4. Look for bottlenecks: database connection pool, queue depth, etc."
    echo ""

    echo -e "${GREEN}Generating 500 concurrent requests...${NC}"
    for i in {1..500}; do
        curl -s "http://localhost:8080/healthz" > /dev/null &
    done
    wait

    echo -e "${GREEN}Done. Check request rate on metrics dashboard.${NC}"
    echo "  → Health & Requests dashboard: Request Rate panel"
    echo "  → CPU should scale proportionally"
    echo ""
}

# ============================================================================
# SCENARIO 6: SILENT FAILURE (Wrong status code, no logs)
# ============================================================================

scenario_silent_failure() {
    echo -e "${YELLOW}=== SCENARIO 6: Silent Failure ===${NC}"
    echo "Simulating requests that fail but don't log errors"
    echo ""
    echo "What you should observe:"
    echo "  1. Request rate might look normal"
    echo "  2. But status code breakdown shows non-2xx responses"
    echo "  3. No ERROR level logs (silent failure)"
    echo "  4. Users see failures but logs look clean"
    echo ""
    echo "How to diagnose:"
    echo "  1. First check: metrics show high request rate?"
    echo "  2. Second check: what status codes? 5xx = server error"
    echo "  3. Third check: logs for those requests"
    echo "  4. If no logs: app might not be logging that code path"
    echo "  5. Look at raw response: curl -v http://localhost:8080/status?code=500"
    echo ""

    echo -e "${GREEN}Generating requests with various status codes...${NC}"
    for code in 400 500 503; do
        for i in {1..10}; do
            curl -s "http://localhost:8080/status?code=$code" > /dev/null &
        done
    done
    wait

    echo -e "${GREEN}Done. Check logs dashboard to find failures.${NC}"
    echo "  → Logs dashboard: filter by status code != 200"
    echo "  → Grafana Explore: {app=\"rust-api\"} | json | fields_status!=\"200\""
    echo ""
}

# ============================================================================
# SCENARIO 7: NODE/CLUSTER PRESSURE
# ============================================================================

scenario_node_pressure() {
    echo -e "${YELLOW}=== SCENARIO 7: Node Pressure / Resource Limits ===${NC}"
    echo "Simulating pod hitting resource limits"
    echo ""
    echo "What you should observe:"
    echo "  1. Pod is Running, but throttled (CPU capped)"
    echo "  2. Latency increases even though traffic is same"
    echo "  3. CPU metric shows high value but requests lag"
    echo "  4. Node shows pressure (disk, memory, cpu)"
    echo ""
    echo "How to diagnose:"
    echo "  1. Check pod CPU limits: kubectl describe pod -l app=rust-api"
    echo "  2. Check CPU throttling: rate(container_cpu_cfs_throttled_seconds_total)"
    echo "  3. Check node capacity: kubectl top nodes"
    echo "  4. Check for eviction: kubectl describe nodes | grep Pressure"
    echo ""

    echo -e "${GREEN}Checking pod resource limits...${NC}"
    kubectl -n observability describe pod -l app=rust-api | grep -A5 "Limits\|Requests"

    echo -e "${GREEN}Checking node resource usage...${NC}"
    kubectl top nodes 2>/dev/null || echo "(kubectl top not available on this cluster)"

    echo -e "${GREEN}Done. If limits are set low, the pod will be throttled.${NC}"
    echo "  → Check Grafana: Pod CPU will show the limit"
    echo "  → Check Prometheus: rate(container_cpu_cfs_throttled_seconds_total)"
    echo ""
}

# ============================================================================
# SCENARIO 8: CASCADING FAILURE (Dependency is slow/down)
# ============================================================================

scenario_cascading_failure() {
    echo -e "${YELLOW}=== SCENARIO 8: Cascading Failure ===${NC}"
    echo "Simulating downstream dependency (DB, cache, queue) being slow or down"
    echo ""
    echo "What you should observe:"
    echo "  1. API request rate stays high (clients keep sending)"
    echo "  2. Request latency increases (waiting for downstream)"
    echo "  3. CPU on API pod stays low (not doing work, waiting)"
    echo "  4. Status codes might include 503 (service unavailable)"
    echo "  5. Timeout errors in logs (if configured)"
    echo ""
    echo "How to diagnose:"
    echo "  1. Metrics: high latency + low CPU = waiting on something external"
    echo "  2. Logs: look for 'timeout', 'connection refused', 'service unavailable'"
    echo "  3. Distributed traces (if available): see where the time went"
    echo "  4. Check downstream service: is the database/cache/queue responding?"
    echo ""

    echo -e "${GREEN}This API has no dependencies, so we'll simulate with delayed responses...${NC}"
    for i in {1..20}; do
        curl -s "http://localhost:8080/delay?seconds=3" > /dev/null &
    done
    wait

    echo -e "${GREEN}Done. This simulates what waiting on a slow dependency looks like.${NC}"
    echo "  → High latency, requests eventually succeed (if timeout is long enough)"
    echo "  → CPU stays low (API is waiting, not computing)"
    echo "  → In real world, you'd see these as 503 errors from a dead service"
    echo ""
}

# ============================================================================
# CLEANUP FUNCTION
# ============================================================================

cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    # Just stop any lingering background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
    echo -e "${GREEN}Cleanup done.${NC}"
}

# ============================================================================
# MAIN MENU
# ============================================================================

usage() {
    echo "Usage: $0 [scenario]"
    echo ""
    echo "Available scenarios:"
    echo "  1 - high-latency       High API latency"
    echo "  2 - crash-loop         Pod crash and restart"
    echo "  3 - memory-pressure    Memory-intensive operations"
    echo "  4 - error-spike        Sudden error rate increase"
    echo "  5 - traffic-spike      Sudden increase in traffic"
    echo "  6 - silent-failure     Failures with no logs"
    echo "  7 - node-pressure      Pod hitting resource limits"
    echo "  8 - cascading-failure  Slow/failed downstream dependency"
    echo "  all                    Run all scenarios"
    echo ""
    echo "Example: $0 high-latency"
    echo ""
}

if [ $# -eq 0 ]; then
    usage
    exit 1
fi

case "$1" in
    1|high-latency)
        scenario_high_latency
        ;;
    2|crash-loop)
        scenario_crash_loop
        ;;
    3|memory-pressure)
        scenario_memory_pressure
        ;;
    4|error-spike)
        scenario_error_spike
        ;;
    5|traffic-spike)
        scenario_traffic_spike
        ;;
    6|silent-failure)
        scenario_silent_failure
        ;;
    7|node-pressure)
        scenario_node_pressure
        ;;
    8|cascading-failure)
        scenario_cascading_failure
        ;;
    all)
        scenario_high_latency
        sleep 5
        scenario_crash_loop
        sleep 5
        scenario_memory_pressure
        sleep 5
        scenario_error_spike
        sleep 5
        scenario_traffic_spike
        sleep 5
        scenario_silent_failure
        sleep 5
        scenario_node_pressure
        sleep 5
        scenario_cascading_failure
        ;;
    *)
        echo "Unknown scenario: $1"
        usage
        exit 1
        ;;
esac

cleanup
