#!/bin/bash

# 无限循环，每分钟执行一次 main.py
while true
do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running Binance Quant..."
    python3 main.py
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] main.py exited. Restarting in 5 seconds..."
    sleep 5
done
