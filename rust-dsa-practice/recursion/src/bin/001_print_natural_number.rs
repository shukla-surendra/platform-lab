// Print natural numbers from 1 to x in ascending order using recursion.
fn recurse(x: i32) {
    if x <= 0 {
        return;
    }
    recurse(x - 1); // recurse first: print happens on the way back up (unwind) -> ascending
    println!("{}", x);
}

fn main() {
    recurse(5);
}
