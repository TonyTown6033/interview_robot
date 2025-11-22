#!/usr/bin/env python3
"""
为指定会话生成健康分析报告
用法: python generate_report_for_session.py sessions/20251119_211758
"""

import sys
import json
from pathlib import Path
from health_analyzer_client import HealthAnalyzerClient

def generate_report_for_session(session_dir: str):
    """为指定会话生成健康分析报告"""
    
    session_path = Path(session_dir)
    
    if not session_path.exists():
        print(f"❌ 会话目录不存在: {session_dir}")
        return False
    
    # 读取会话数据
    session_file = session_path / "session.json"
    if not session_file.exists():
        print(f"❌ 会话文件不存在: {session_file}")
        return False
    
    print(f"📖 读取会话数据: {session_file}")
    
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    # 提取问答数据
    answers = []
    for ans in session_data.get('answers', []):
        answers.append({
            'question': ans['question_text'],
            'answer': ans['transcript']
        })
    
    questions_count = session_data.get('total_questions', len(answers))
    
    print(f"📊 会话统计:")
    print(f"   会话ID: {session_data.get('session_id')}")
    print(f"   问题数: {questions_count}")
    print(f"   回答数: {len(answers)}")
    print(f"   完成率: {len(answers)/questions_count*100:.1f}%")
    
    # 初始化健康分析客户端
    print("\n🤖 初始化健康分析客户端...")
    analyzer = HealthAnalyzerClient()
    
    # 执行分析
    print("🔄 正在调用 AI 分析...")
    analysis_result = analyzer.analyze_interview(answers, questions_count)
    
    if "error" in analysis_result:
        print(f"\n❌ 分析失败: {analysis_result.get('message')}")
        return False
    
    print("✅ AI 分析完成！")
    
    # 格式化报告
    formatted_report = analyzer.format_report(analysis_result)
    
    # 保存报告
    print("\n💾 保存报告...")
    
    # 保存 JSON
    analysis_json_file = session_path / "health_analysis.json"
    with open(analysis_json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    print(f"   ✅ {analysis_json_file}")
    
    # 保存文本
    report_file = session_path / "health_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(formatted_report)
    print(f"   ✅ {report_file}")
    
    # 显示报告
    print("\n" + "="*70)
    print("📋 生成的健康报告:")
    print("="*70)
    print(formatted_report)
    
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_dir = sys.argv[1]
    else:
        # 默认使用指定的会话
        session_dir = "sessions/20251119_211758"
    
    print("🚀 健康报告生成工具")
    print("="*70)
    
    success = generate_report_for_session(session_dir)
    
    if success:
        print("\n✅ 报告生成成功！")
    else:
        print("\n❌ 报告生成失败")
        sys.exit(1)

