from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract b from a and return the difference."""
    return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b and return the quotient."""
    if b == 0:
        raise ValueError("b must not be zero")
    return a / b

@mcp.tool()
def reverse_string(text: str) -> str:
    """Reverse the characters in a string."""
    return text[::-1]

@mcp.tool()
def word_count(text: str) -> int:
    """Count the number of whitespace-separated words in a string."""
    return len(text.split())

if __name__ == "__main__":
    mcp.run()