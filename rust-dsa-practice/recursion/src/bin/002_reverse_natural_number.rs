// Print natural numbers from x down to 1 in descending order using recursion.
fn recurse(x: i32) {
    if x <= 0 {
        return;
    }
    println!("{}", x); // print first: happens on the way down (call) -> descending
    recurse(x - 1);
}

fn main() {
    recurse(5);
}
