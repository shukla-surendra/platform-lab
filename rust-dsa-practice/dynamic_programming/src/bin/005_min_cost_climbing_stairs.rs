// Problem: Min Cost Climbing Stairs.
//
// You're given an array `cost` where `cost[i]` is the cost to step ON
// stair i. You can start standing on step 0 or step 1 (both free to start
// from - no cost paid just for starting there), and from any step you can
// climb 1 or 2 steps at a time. The "top" is one step past the last index
// (index cost.len()). Find the MINIMUM total cost to reach the top.
//
// e.g. cost = [10, 15, 20]
//   Option A: start at 0 (free), pay 10, step to 1, pay 15, step to top (2 steps) = 25
//   Option B: start at 1 (free), pay 15, step directly to top (2 steps)          = 15
//   -> cheapest is 15.
//
// This is the "optimization problem" version of
// 004_climbing_stairs.rs - that problem COUNTED the number of ways to
// reach the top (sum of subproblem counts); this one asks for the BEST
// (minimum) way to reach the top (min of subproblem costs). Same
// recursive shape, different combining operation:
//   counting:      ways(n)    = ways(n-1)    + ways(n-2)          (sum)
//   optimization:  minCost(n) = cost[n] + min(minCost(n-1), minCost(n-2))  (min)
//
// That's the general pattern for DP optimization problems: define
// subproblem i as "best value achievable up to/at i," express it in terms
// of smaller subproblems using min (or max, for a maximization problem)
// over the valid choices, then tabulate bottom-up exactly like before.
//
// Recurrence:
//   minCost(0) = 0   // standing on step 0 costs nothing until you LEAVE it
//   minCost(1) = 0   // same for step 1 - you can start here for free
//   minCost(i) = min(minCost(i - 1) + cost[i - 1], minCost(i - 2) + cost[i - 2])   for i >= 2
// where minCost(i) means "cheapest cost to reach step i" (i can range up
// to cost.len(), the "top"). The two options being compared are the two
// possible LAST moves: arrive at i via a 1-step from i-1 (pay whatever it
// cost to reach i-1, plus cost[i-1] to leave it), or via a 2-step from
// i-2 (pay whatever it cost to reach i-2, plus cost[i-2] to leave it) -
// each branch pays the toll for the step it's actually leaving FROM, not
// a single shared cost for both.
//
// The answer is minCost(cost.len()) - the cheapest way to reach the top.
//
// e.g. cost = [10, 15, 20], table[0] and table[1] are the two starting
// points (free), then:
//   table[0] = 0
//   table[1] = 0
//   table[2] = min(table[1] + cost[1], table[0] + cost[0])
//            = min(0 + 15, 0 + 10) = 10
//   table[3] = min(table[2] + cost[2], table[1] + cost[1])
//            = min(10 + 20, 0 + 15) = 15
//   answer = table[3] = 15 - matches the 15 from the walkthrough above.
//
// Complexity: O(n) time, O(n) space with a full table (as written), same
// O(1)-space rolling-variables trick as 003_nth_fibonacci_loop.rs applies
// here too, since minCost(i) only ever looks back 2 steps.

fn min_cost_climbing_stairs(cost: &[u32]) -> u32 {
    let n = cost.len();

    // table[i] = cheapest cost to REACH step i (before paying to leave it).
    // table[n] is the top - one step past the last real stair.
    let mut table = vec![0u32; n + 1];
    // table[0] and table[1] stay 0: both are free starting points.

    for i in 2..=n {
        table[i] = std::cmp::min(
            table[i - 1] + cost[i - 1], // arrived via a 1-step from i-1
            table[i - 2] + cost[i - 2], // arrived via a 2-step from i-2
        );
    }

    table[n]
}

fn main() {
    let examples: [&[u32]; 2] = [&[10, 15, 20], &[1, 100, 1, 1, 1, 100, 1, 1, 100, 1]];
    for cost in examples {
        println!(
            "min_cost_climbing_stairs({:?}) = {}",
            cost,
            min_cost_climbing_stairs(cost)
        );
    }
}
