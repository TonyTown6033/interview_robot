#!/usr/bin/env python3
"""
为会话 20251119_211758 生成示例健康报告
基于会话数据直接生成，不调用 API
"""

import json
from pathlib import Path
from datetime import datetime

# 读取会话数据
session_dir = Path("sessions/20251119_211758")
session_file = session_dir / "session.json"

print("🚀 健康报告生成工具")
print("="*70)
print(f"📖 读取会话数据: {session_file}\n")

with open(session_file, 'r', encoding='utf-8') as f:
    session_data = json.load(f)

# 分析会话数据
answers = session_data.get('answers', [])
total_questions = session_data.get('total_questions', 7)

print(f"📊 会话统计:")
print(f"   会话ID: {session_data['session_id']}")
print(f"   开始时间: {session_data['start_time']}")
print(f"   总时长: {session_data['duration_seconds']:.1f} 秒")
print(f"   问题数: {total_questions}")
print(f"   回答数: {len(answers)}")
print(f"   完成率: {len(answers)/total_questions*100:.1f}%\n")

# 基于实际回答内容进行分析
# 注意：这个会话的回答质量较低，似乎是语音识别问题
analysis_notes = []
for ans in answers:
    q = ans['question_text']
    a = ans['transcript']
    analysis_notes.append(f"Q{ans['question_id']}: {q}\nA: {a}")

# 生成分析结果
analysis_result = {
    "overall_health": "insufficient_data",
    "health_score": 45,
    "main_concerns": [
        "访谈回答不完整，可能是语音识别问题",
        "未能获取完整的健康信息",
        "建议重新进行访谈以获取准确数据"
    ],
    "lifestyle_assessment": {
        "sleep": "信息不完整 - 仅提到'睡几个小时'但未给出具体数字",
        "exercise": "信息不完整 - 未获取运动习惯相关信息",
        "diet": "提到'注意营养均衡'但缺少详细信息",
        "stress": "提到'工作压力'但未详细说明"
    },
    "risk_factors": [
        "数据不完整导致无法准确评估健康风险",
        "语音识别质量影响了信息采集的准确性"
    ],
    "recommendations": [
        "建议调整麦克风设置，提高语音识别准确度",
        "建议重新进行访谈，确保回答完整准确",
        "说话时尽量清晰、缓慢，确保系统能正确识别",
        "检查 VAD（语音活动检测）参数设置",
        "考虑使用更安静的环境进行访谈"
    ],
    "medical_advice": "由于本次访谈数据不完整，无法提供准确的健康建议。建议重新进行完整的健康咨询访谈。",
    "summary": "本次访谈共包含7个问题，均有回答记录。但回答内容显示可能存在语音识别准确度问题，导致很多回答只是重复了问题内容，而没有给出实际的回答。这可能是由于：1) 麦克风音量设置不当；2) 语音识别 VAD 参数过于灵敏；3) 环境噪音干扰；4) 用户说话不够清晰。建议调整系统设置后重新进行访谈，以获取准确的健康信息。",
    "meta": {
        "total_questions": total_questions,
        "answered_questions": len(answers),
        "completion_rate": f"{len(answers)/total_questions*100:.1f}%",
        "session_id": session_data['session_id'],
        "analysis_type": "local_analysis",
        "note": "由于回答质量问题，本报告为基于现有数据的初步分析"
    }
}

# 格式化文本报告
report_lines = []
report_lines.append("="*70)
report_lines.append("📋 健康访谈分析报告")
report_lines.append("="*70)
report_lines.append("")

# 会话信息
report_lines.append("📊 访谈统计")
report_lines.append(f"   • 会话ID: {session_data['session_id']}")
report_lines.append(f"   • 访谈日期: {session_data['start_time'][:10]}")
report_lines.append(f"   • 问题总数: {total_questions}")
report_lines.append(f"   • 已回答数: {len(answers)}")
report_lines.append(f"   • 完成率: {analysis_result['meta']['completion_rate']}")
report_lines.append("")

# 整体评估
overall_emoji = {"good": "✅", "fair": "⚠️", "concerning": "🔴", "insufficient_data": "❓"}
report_lines.append(f"🏥 整体健康状况: {overall_emoji.get(analysis_result['overall_health'], '❓')} {analysis_result['overall_health'].upper()}")
report_lines.append(f"📈 健康评分: {analysis_result['health_score']}/100")
report_lines.append("")

# 数据质量说明
report_lines.append("⚠️  数据质量说明")
report_lines.append("   本次访谈存在数据质量问题，很多回答只是重复了问题内容。")
report_lines.append("   这可能影响了健康评估的准确性。")
report_lines.append("")

# 总结
report_lines.append("📝 综合评估")
report_lines.append(f"   {analysis_result['summary']}")
report_lines.append("")

# 主要关注点
report_lines.append("⚠️  主要关注点")
for i, concern in enumerate(analysis_result['main_concerns'], 1):
    report_lines.append(f"   {i}. {concern}")
report_lines.append("")

# 生活方式评估
report_lines.append("🌟 生活方式评估")
lifestyle = analysis_result['lifestyle_assessment']
report_lines.append(f"   💤 睡眠: {lifestyle['sleep']}")
report_lines.append(f"   🏃 运动: {lifestyle['exercise']}")
report_lines.append(f"   🥗 饮食: {lifestyle['diet']}")
report_lines.append(f"   😌 压力: {lifestyle['stress']}")
report_lines.append("")

# 风险因素
report_lines.append("🚨 识别的问题")
for i, risk in enumerate(analysis_result['risk_factors'], 1):
    report_lines.append(f"   {i}. {risk}")
report_lines.append("")

# 改进建议
report_lines.append("💡 改进建议")
for i, rec in enumerate(analysis_result['recommendations'], 1):
    report_lines.append(f"   {i}. {rec}")
report_lines.append("")

# 建议
report_lines.append("🏥 建议")
report_lines.append(f"   {analysis_result['medical_advice']}")
report_lines.append("")

# 访谈详细内容
report_lines.append("="*70)
report_lines.append("📋 访谈详细记录")
report_lines.append("="*70)
report_lines.append("")
for ans in answers:
    report_lines.append(f"问题 {ans['question_id']}: {ans['question_text']}")
    report_lines.append(f"回答: {ans['transcript']}")
    report_lines.append(f"时间: {ans['timestamp']}")
    report_lines.append("-"*70)
    report_lines.append("")

report_lines.append("="*70)
report_lines.append("⚠️  免责声明：")
report_lines.append("   本报告基于不完整的访谈数据生成，仅供参考。")
report_lines.append("   建议重新进行完整、准确的健康咨询访谈。")
report_lines.append("   如有健康问题，请咨询专业医疗机构。")
report_lines.append("="*70)

formatted_report = "\n".join(report_lines)

# 保存报告
print("💾 保存报告...")

# 保存 JSON
analysis_json_file = session_dir / "health_analysis.json"
with open(analysis_json_file, 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)
print(f"   ✅ {analysis_json_file}")

# 保存文本
report_file = session_dir / "health_report.txt"
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(formatted_report)
print(f"   ✅ {report_file}")

# 显示报告
print("\n" + formatted_report)

print("\n✅ 报告生成完成！")
print(f"\n📁 报告位置: {session_dir}/")
print("   - health_analysis.json")
print("   - health_report.txt")

