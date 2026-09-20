#! /opt/homebrew/bin/bash
# Bash variables are essentially strings by default.
x=10
y="hello"
z=10.5
# you dont need to define anything
echo "$x"
echo "$y"
echo "$z"

# 1. String
name="Surendra"
echo "$name"

#2. Integer
# You can explicitly declare an integer:
declare -i age=30


age=30
((age++))
echo "$age"

a=10
b=20
sum=$((a+b))
echo "$sum"


# 3. Array
# Bash supports indexed arrays:

servers=("web1" "web2" "web3")

# Access:
echo "${servers[0]}"

# Loop through it:
for server in "${servers[@]}"
do
    echo "$server"
done


# 4. Associative array
# Similar to a dictionary/map in Python.

declare -A server_ip

server_ip[web1]="10.0.0.10"
server_ip[web2]="10.0.0.20"

# Access:
echo "${server_ip[web1]}"

# Loop:
for server in "${!server_ip[@]}"
do
    echo "$server -> ${server_ip[$server]}"
done

