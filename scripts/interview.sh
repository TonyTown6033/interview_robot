#!/bin/bash

# 客户访谈系统启动脚本
# 使用方法: ./scripts/interview.sh

echo "🚀 启动客户访谈系统"
echo "=================================================="

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查是否设置了 API Key
if [ -z "$STEPFUN_API_KEY" ]; then
    echo "⚠️  错误: 请先设置环境变量 STEPFUN_API_KEY"
    echo "   export STEPFUN_API_KEY='your-api-key-here'"
    exit 1
fi

# 检查问题配置文件
if [ ! -f "questions.yaml" ]; then
    echo "❌ 找不到 questions.yaml 配置文件"
    exit 1
fi

# 检查 Python 环境
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv 未安装，使用系统 Python"
    python3 main.py
else
    echo "✅ 使用 uv 运行"
    uv run python main.py
fi
