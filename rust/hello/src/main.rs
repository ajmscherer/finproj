fn main() {
    println!("Hello, world! It's me Alex");
    println!("Factorial of 6 is {}", factorial(6));
}

fn factorial(n: u32) -> u32 {
    if n == 0 {
        return 1;
    }
    return n * factorial(n - 1);
}
