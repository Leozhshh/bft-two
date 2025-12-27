#!/bin/bash

# 激活 conda
source /home/zhshh/miniconda3/etc/profile.d/conda.sh
conda activate bft

# 切换到你的项目目录
cd /home/zhshh/bft_release/bft_v0.1.74_20251223_0159/BinanceFuturesTestnet

# 启动 main.py
python3 main.py >> logs/service.log 2>&1