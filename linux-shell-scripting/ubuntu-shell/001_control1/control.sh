#! /bin/bash

while true; do
    echo "Control script is running..."
    read -p "Press 1 for memory usage, 2 for CPU usage, or q to quit: " choice
    case $choice in
        1)
            echo "Memory Usage:"
            free -h
            ;;
        2)
            echo "CPU Usage:"
            top -bn1 | grep "Cpu(s)"
            ;;
        q)
            echo "Exiting control script."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
    sleep 5
done