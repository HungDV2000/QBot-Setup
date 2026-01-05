#!/bin/bash

# QBot - Stop All Bots Script
# Dừng tất cả modules đang chạy

echo "========================================"
echo "QBot - Stopping All Modules"
echo "========================================"

# Find all Python processes running hd_ scripts
PIDS=$(ps aux | grep python | grep 'hd_' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "❌ No QBot modules running"
    exit 0
fi

echo "Found running modules:"
ps aux | grep python | grep 'hd_' | grep -v grep

echo ""
read -p "Do you want to stop all these processes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    for PID in $PIDS
    do
        echo "Killing PID $PID..."
        kill $PID
    done
    
    sleep 2
    
    # Force kill if still running
    REMAINING=$(ps aux | grep python | grep 'hd_' | grep -v grep | awk '{print $2}')
    if [ ! -z "$REMAINING" ]; then
        echo "Force killing remaining processes..."
        kill -9 $REMAINING
    fi
    
    echo ""
    echo "✅ All modules stopped!"
else
    echo "Cancelled."
fi

echo "========================================"

