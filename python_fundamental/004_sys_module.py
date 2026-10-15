import sys
import json

print(sys.argv)  # Prints the list of command-line arguments passed to the script

# ---------------------------------------------------------------------------
# KEY IDEA: every value in sys.argv is a STRING.
# The shell can only hand text to Python. A "list" or "dict" arrives as text
# that LOOKS like one, and we must convert it ourselves.
#
# Run this file like this (one line):
#
#   python3 004_sys_module.py surendra apple,banana,mango '{"env": "dev", "replicas": 3}'
#
# What sys.argv looks like for that command:
#
#   sys.argv[0] -> '004_sys_module.py'                (always the script name)
#   sys.argv[1] -> 'surendra'                         (string)
#   sys.argv[2] -> 'apple,banana,mango'               (string that we turn into a list)
#   sys.argv[3] -> '{"env": "dev", "replicas": 3}'    (string that we turn into a dict)
# ---------------------------------------------------------------------------

# Stop early with a helpful message if not enough arguments were given.
# len(sys.argv) is 4 here: the script name + 3 values.
if len(sys.argv) < 4:
    print("Usage: python3 004_sys_module.py <name> <item1,item2,...> '<json-dict>'")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 1. STRING
# Passed as:   surendra
#              "hello world"   <- use quotes if the text has spaces,
#                                 otherwise it becomes TWO arguments
# Accepted as: use sys.argv[1] directly, it is already a str
# ---------------------------------------------------------------------------
name = sys.argv[1]
print("\n--- STRING ---")
print("value:", name)          # surendra
print("type :", type(name))    # <class 'str'>

# ---------------------------------------------------------------------------
# 2. LIST
# Passed as:   apple,banana,mango     <- comma-separated, NO spaces
# Accepted as: .split(",") breaks the text at each comma into a list
#
#   'apple,banana,mango'.split(",") -> ['apple', 'banana', 'mango']
#
# Note: every item stays a string. If you need numbers, pass JSON instead,
# e.g. '[1, 2, 3]' and use json.loads (same as the dict below).
# ---------------------------------------------------------------------------
fruits = sys.argv[2].split(",")
print("\n--- LIST ---")
print("value:", fruits)          # ['apple', 'banana', 'mango']
print("type :", type(fruits))    # <class 'list'>
print("first item:", fruits[0])  # apple
for fruit in fruits:             # we can loop over it like any list
    print("  -", fruit)

# ---------------------------------------------------------------------------
# 3. DICT
# Passed as:   '{"env": "dev", "replicas": 3}'
#              ^ single quotes OUTSIDE  -> keeps it as ONE argument and stops
#                                          the shell from eating the inner quotes
#                 double quotes INSIDE  -> JSON requires double quotes
# Accepted as: json.loads() turns JSON text into a Python dict
#
#   json.loads('{"env": "dev", "replicas": 3}') -> {'env': 'dev', 'replicas': 3}
#
# Note: "replicas": 3 comes back as a real int, not the string '3'.
# ---------------------------------------------------------------------------
config = json.loads(sys.argv[3])
print("\n--- DICT ---")
print("value:", config)                # {'env': 'dev', 'replicas': 3}
print("type :", type(config))          # <class 'dict'>
print("env  :", config["env"])         # dev
print("replicas + 1 =", config["replicas"] + 1)  # 4  (works because it's an int)
