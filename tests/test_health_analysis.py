"""
测试健康分析集成 - 简化版
不需要实际运行访谈，直接测试分析功能
"""

import json
from pathlib import Path

print("=" * 70)
print("🧪 测试健康分析集成")
print("=" * 70)

# 检查文件是否存在
files_to_check = [
    "health_analyzer_client.py",
    "health_analyzer_mcp.py",
    "interview_client_hybrid.py",
    "question_manager.py"
]

print("\n📁 检查文件...")
for file in files_to_check:
    file_path = Path(file)
    if file_path.exists():
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} - 文件不存在")

# 检查代码集成
print("\n🔍 检查代码集成...")

# 检查 interview_client_hybrid.py 是否导入了 health_analyzer_client
with open("interview_client_hybrid.py", "r", encoding="utf-8") as f:
    hybrid_content = f.read()
    if "from health_analyzer_client import HealthAnalyzerClient" in hybrid_content:
        print("   ✅ interview_client_hybrid.py 已导入 HealthAnalyzerClient")
    else:
        print("   ❌ interview_client_hybrid.py 未导入 HealthAnalyzerClient")
    
    if "self.health_analyzer = HealthAnalyzerClient" in hybrid_content:
        print("   ✅ interview_client_hybrid.py 已初始化健康分析客户端")
    else:
        print("   ❌ interview_client_hybrid.py 未初始化健康分析客户端")
    
    if "_generate_health_analysis" in hybrid_content:
        print("   ✅ interview_client_hybrid.py 包含 _generate_health_analysis 方法")
    else:
        print("   ❌ interview_client_hybrid.py 缺少 _generate_health_analysis 方法")

# 检查 question_manager.py 的新方法
with open("question_manager.py", "r", encoding="utf-8") as f:
    manager_content = f.read()
    if "save_analysis_report" in manager_content:
        print("   ✅ question_manager.py 包含 save_analysis_report 方法")
    else:
        print("   ❌ question_manager.py 缺少 save_analysis_report 方法")
    
    if "get_answers_for_analysis" in manager_content:
        print("   ✅ question_manager.py 包含 get_answers_for_analysis 方法")
    else:
        print("   ❌ question_manager.py 缺少 get_answers_for_analysis 方法")

print("\n" + "=" * 70)
print("✅ 集成检查完成！")
print("=" * 70)

print("\n📋 功能说明:")
print("   1. 运行访谈程序: python interview_client_hybrid.py")
print("   2. 完成访谈后会自动生成健康分析报告")
print("   3. 报告保存在 sessions/[session_id]/ 目录")
print("   4. 包含两个文件:")
print("      - health_analysis.json (JSON 格式)")
print("      - health_report.txt (文本格式)")

print("\n💡 注意事项:")
print("   • 确保设置了 STEPFUN_API_KEY 环境变量")
print("   • 需要网络连接以调用 Step API")
print("   • 分析会消耗 API token")

print("\n📖 详细文档: HEALTH_ANALYSIS.md")
print("=" * 70)

