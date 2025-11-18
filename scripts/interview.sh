#!/bin/bash

# 客户访谈系统启动脚本

# 检查是否在正确的目录
if [ ! -f "interview_client.py" ]; then
    echo "❌ 请在 questionAgent 目录下运行此脚本"
    exit 1
fi

# 检查环境变量
if [ -z "$STEPFUN_API_KEY" ]; then
    echo "⚠️  警告: 未设置 STEPFUN_API_KEY 环境变量"
    echo "请运行: export STEPFUN_API_KEY='your-api-key'"
    exit 1
fi

# 检查问题配置文件
if [ ! -f "questions.yaml" ]; then
    echo "❌ 找不到 questions.yaml 配置文件"
    exit 1
fi

echo "🚀 启动客户访谈系统..."
echo ""

# 使用 uv 运行
if command -v uv &> /dev/null; then
    uv run python interview_client.py
else
    # 降级到 python
    echo "⚠️  未找到 uv，使用 python 运行"
    python3 interview_client.py
fi

