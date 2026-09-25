
"""
DECORATOR
│
├── 1. Function is an object
│      └── can pass function as argument
│
├── 2. Nested function
│      └── function defined inside another function
│
├── 3. Closure
│      └── inner function remembers outer function/variables
│
├── 4. Decorator
│      └── function that takes a function
│          and returns a modified/wrapped function
│
├── 5. @ syntax
│      └── @decorator
│          ≈ func = decorator(func)
│
├── 6. wrapper
│      └── code before/after original function
│
├── 7. *args, **kwargs
│      └── wrapper can accept any arguments
│
└── 8. functools.wraps
       └── preserves original function metadata


Decorator = separate cross-cutting behavior from business logic.
Decorators are commonly useful for:

@log_execution      → logging / timing
@retry(3)           → retry failed operations
@cache              → caching
@authenticate       → authentication/authorization
@validate           → input validation
@transaction        → database transaction handling
@rate_limit(100)    → rate limiting
    
"""


import time
from functools import wraps


def log_execution(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()

        try:
            result = func(*args, **kwargs)
            return result

        finally:
            duration = time.time() - start
            print(f"{func.__name__} took {duration:.2f}s")

    return wrapper

def log_function_boundary(func):

    def wrapper(*args, **kwargs):
        # before
        print(func, " || Start")
        result = func(*args, **kwargs)
        print(func, "|| End")
        # after
        return result

    return wrapper



@log_function_boundary
def hello(name):
    print(f"Hello {name}")

hello("Surendra")

# Function With Repeate

def repeat(n):
    def decorator(func):

        def wrapper(*args, **kwargs):
            for _ in range(n):
                func(*args, **kwargs)

        return wrapper

    return decorator


@repeat(3)
def hello(name):
    print(f"Hello {name}")


@log_execution
def greeting(name):
    print(f"Hello {name}")

greeting("India")

hello("Surendra")

#################################################################################
#################################################################################

def retry(max_retries, delay):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)

        return wrapper

    return decorator


@retry(3, 2)
def connect_to_database(host, port):
    print(f"Connecting to {host}:{port}")
    raise Exception("Connection failed")


connect_to_database("localhost", 5432)