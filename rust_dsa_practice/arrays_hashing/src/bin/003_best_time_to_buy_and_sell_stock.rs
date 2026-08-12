// Problem: LeetCode 121 - Best Time to Buy and Sell Stock.
//
// Given daily prices, choose ONE day to buy and a LATER day to sell to
// maximize profit. Return 0 if no profit is possible (prices only fall).
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// The brute force is "try every (buy_day, sell_day) pair with buy_day <
// sell_day, keep the best difference" - O(n^2), and it's checking a lot
// of pairs that can't possibly be optimal: if you already know the
// cheapest price up through yesterday, no pair involving a MORE
// expensive buy day from that same range can ever beat selling today
// against that cheapest price. The n^2 loop is redoing a "what's the
// min so far" computation from scratch for every sell day, when that
// running minimum only needs to be tracked once, going forward.
//
// ---------------------------------------------------------------------
// THE REFRAME THAT COLLAPSES IT TO ONE PASS
// ---------------------------------------------------------------------
// Fix the sell day and ask: "what's the best possible buy day for THIS
// sell day?" - it's always the lowest price at any point strictly
// before it. So walk left to right, carrying two running values: the
// lowest price seen so far (the best possible buy point up to now), and
// the best profit achievable by selling today against that low. Update
// both on every day, in the right order (profit BEFORE updating the
// minimum - selling on the same day you buy isn't allowed, and even if
// it were, it would produce a profit of 0, never help).
//
// This is structurally the same move as Max Subarray (53, in this same
// crate): both are "track a running best-so-far single value, update a
// global answer against it, one pass." Seeing Best-Time-to-Buy as
// "Kadane's algorithm on the array of day-to-day price DIFFERENCES" is
// the connection worth having ready - see 006_maximum_subarray.rs.
//
// Complexity: O(n) time, O(1) space.

pub fn max_profit(prices: &[i32]) -> i32 {
    let Some(&first) = prices.first() else {
        return 0; // no days at all -> no possible trade
    };

    let mut min_price_so_far = first;
    let mut best_profit = 0;

    for &price in &prices[1..] {
        // Profit from selling TODAY against the cheapest day so far.
        let profit_today = price - min_price_so_far;
        best_profit = best_profit.max(profit_today);

        // Then, separately, today might itself become the new cheapest
        // buy point for future days.
        min_price_so_far = min_price_so_far.min(price);
    }

    best_profit
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn max_profit_leetcode(prices: Vec<i32>) -> i32 {
    max_profit(&prices)
}

fn main() {
    let examples: [&[i32]; 3] = [&[7, 1, 5, 3, 6, 4], &[7, 6, 4, 3, 1], &[2, 4, 1]];
    for ex in examples {
        println!("{:?} -> {}", ex, max_profit(ex));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1_buy_low_sell_high() {
        assert_eq!(max_profit(&[7, 1, 5, 3, 6, 4]), 5); // buy at 1, sell at 6
    }

    #[test]
    fn example_2_strictly_decreasing_no_profit() {
        assert_eq!(max_profit(&[7, 6, 4, 3, 1]), 0);
    }

    #[test]
    fn single_day_no_trade_possible() {
        assert_eq!(max_profit(&[5]), 0);
    }

    #[test]
    fn empty_no_trade_possible() {
        assert_eq!(max_profit(&[]), 0);
    }

    // Guards against updating the running minimum BEFORE computing
    // today's profit - if the lowest price is on the very last day,
    // that day must never be used as its own sell day.
    #[test]
    fn lowest_price_on_last_day_yields_zero() {
        assert_eq!(max_profit(&[9, 7, 5, 3, 1]), 0);
    }

    #[test]
    fn best_trade_is_at_the_very_end() {
        assert_eq!(max_profit(&[3, 2, 6, 5, 0, 3]), 4); // buy at 2, sell at 6
    }
}
