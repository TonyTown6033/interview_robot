#!/usr/bin/env python3
"""
RAG 增强访谈系统 - 快速启动脚本
"""

import sys
import os

# 确保可以导入 src 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.interview_client_rag import main

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       RAG 增强智能访谈系统                                    ║
║       Intelligent Interview System with RAG                 ║
║                                                              ║
║  特性:                                                       ║
║  ✓ 智能问题检索 (基于对话上下文)                              ║
║  ✓ 灵活的 AI 对话 (自然表述，不是机械朗读)                    ║
║  ✓ 自动追问澄清 (检测回答完整性)                              ║
║  ✓ 上下文感知 (记忆对话历史)                                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 检查环境
    api_key = os.getenv("STEPFUN_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("❌ 错误: 未设置 STEPFUN_API_KEY 环境变量")
        print("\n请先设置:")
        print("  export STEPFUN_API_KEY='your-actual-api-key'")
        print("\n或在 ~/.bashrc 或 ~/.zshrc 中添加该行")
        sys.exit(1)

    # 检查问题文件
    if not os.path.exists("questions.yaml"):
        print("❌ 错误: 未找到 questions.yaml 文件")
        print("\n请确保 questions.yaml 存在于当前目录")
        sys.exit(1)

    print("✅ 环境检查通过，启动访谈系统...\n")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
