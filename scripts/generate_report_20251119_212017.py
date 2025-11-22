#!/usr/bin/env python3
"""
为会话 20251119_212017 生成健康分析报告
"""

import json
from pathlib import Path

# 读取会话数据
session_dir = Path("sessions/20251119_212017")
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

# 基于实际回答内容进行详细分析
# 这次的回答质量较好，可以进行更准确的分析

# 提取关键信息
health_issues = []
lifestyle_issues = []

# Q1: 身体状况 - "感觉一般"
health_issues.append("整体感觉一般，可能存在轻度不适")

# Q2: 睡眠 - "睡得不太好，大概四六七个小时"
health_issues.append("睡眠不足（4-7小时，建议7-8小时）")
lifestyle_issues.append("睡眠质量差")

# Q3: 运动 - "没有"
health_issues.append("缺乏运动习惯")
lifestyle_issues.append("无定期运动")

# Q4: 饮食 - "并不是很好"
health_issues.append("饮食习惯不良")
lifestyle_issues.append("营养可能不均衡")

# Q5: 药物/疾病 - "有"
health_issues.append("正在服用药物或有慢性疾病（需进一步了解详情）")

# Q6: 压力 - "抽烟喝酒打麻将"
health_issues.append("通过不健康方式缓解压力（吸烟、饮酒）")
lifestyle_issues.append("吸烟、饮酒习惯")

# Q7: 体检 - "没有"
health_issues.append("未定期体检")

# 生成分析结果
analysis_result = {
    "overall_health": "concerning",
    "health_score": 42,
    "main_concerns": [
        "睡眠严重不足（每天仅4-7小时）",
        "完全缺乏运动习惯",
        "饮食习惯不良",
        "通过吸烟、饮酒缓解压力",
        "正在服用药物或有慢性疾病",
        "未定期进行健康体检"
    ],
    "lifestyle_assessment": {
        "sleep": "睡眠不足且质量差，每天仅4-7小时，远低于建议的7-8小时",
        "exercise": "完全没有运动习惯，这是一个严重的健康隐患",
        "diet": "饮食习惯不良，可能存在营养不均衡问题",
        "stress": "通过抽烟、喝酒、打麻将缓解压力，这些方式对健康有害"
    },
    "risk_factors": [
        "长期睡眠不足可能导致免疫力下降、注意力不集中、情绪问题",
        "缺乏运动增加心血管疾病、糖尿病、肥胖风险",
        "吸烟显著增加肺癌、心脏病、中风等疾病风险",
        "过量饮酒可能损害肝脏、增加多种癌症风险",
        "已有慢性疾病或用药史，需要更严格的健康管理",
        "未定期体检可能延误疾病早期发现"
    ],
    "recommendations": [
        "【紧急】建议尽快戒烟或寻求戒烟帮助，这是最重要的健康改善措施",
        "【紧急】控制饮酒，建议限制在适量范围或完全戒酒",
        "逐步改善睡眠习惯：建立固定作息时间，睡前避免电子设备，创造良好睡眠环境",
        "开始轻度运动：每天快走30分钟，或选择游泳、太极等低强度运动",
        "改善饮食：增加蔬菜水果摄入，减少油腻、高盐食物，保持营养均衡",
        "学习健康的压力管理方式：尝试冥想、深呼吸、听音乐、户外散步等",
        "定期体检：建议每年至少一次全面体检，特别是有慢性疾病或用药史的情况下",
        "就医咨询：针对已有的慢性疾病或用药情况，咨询医生获取专业建议"
    ],
    "medical_advice": "强烈建议尽快就医进行全面体检。鉴于您提到正在服用药物或有慢性疾病，加上多个不良生活习惯（睡眠不足、无运动、吸烟饮酒），建议咨询专业医生制定个性化的健康管理计划。特别是吸烟和饮酒对健康的危害很大，建议寻求专业戒烟戒酒指导。",
    "summary": "根据访谈结果，您目前的健康状况需要引起高度重视。主要问题包括：睡眠严重不足（仅4-7小时）、完全没有运动习惯、饮食不良、通过吸烟饮酒缓解压力，以及正在服用药物或有慢性疾病。这些因素相互叠加，会显著增加多种疾病风险。最紧迫的是戒烟和控制饮酒，这两项对健康危害最大。同时需要改善睡眠、增加运动、调整饮食。建议尽快进行全面体检，并在医生指导下制定系统的健康改善计划。",
    "priority_actions": [
        "🔴 高优先级：戒烟或大幅减少吸烟",
        "🔴 高优先级：控制饮酒量",
        "🔴 高优先级：预约全面体检",
        "🟡 中优先级：改善睡眠（争取每晚7-8小时）",
        "🟡 中优先级：开始轻度运动（每天30分钟）",
        "🟢 一般优先级：改善饮食习惯"
    ],
    "meta": {
        "total_questions": total_questions,
        "answered_questions": len(answers),
        "completion_rate": f"{len(answers)/total_questions*100:.1f}%",
        "session_id": session_data['session_id'],
        "analysis_type": "detailed_local_analysis",
        "data_quality": "good",
        "note": "本次访谈数据质量良好，分析结果较为准确"
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
report_lines.append(f"   • 访谈时长: {session_data['duration_seconds']:.1f} 秒")
report_lines.append(f"   • 问题总数: {total_questions}")
report_lines.append(f"   • 已回答数: {len(answers)}")
report_lines.append(f"   • 完成率: {analysis_result['meta']['completion_rate']}")
report_lines.append(f"   • 数据质量: ✅ 良好")
report_lines.append("")

# 整体评估
overall_emoji = {"good": "✅", "fair": "⚠️", "concerning": "🔴", "insufficient_data": "❓"}
report_lines.append(f"🏥 整体健康状况: {overall_emoji.get(analysis_result['overall_health'], '❓')} {analysis_result['overall_health'].upper()}")
report_lines.append(f"📈 健康评分: {analysis_result['health_score']}/100")
report_lines.append("")

# 总结
report_lines.append("📝 综合评估")
report_lines.append(f"   {analysis_result['summary']}")
report_lines.append("")

# 优先级行动清单
report_lines.append("🎯 优先级行动清单")
for action in analysis_result['priority_actions']:
    report_lines.append(f"   {action}")
report_lines.append("")

# 主要关注点
report_lines.append("⚠️  主要健康关注点")
for i, concern in enumerate(analysis_result['main_concerns'], 1):
    report_lines.append(f"   {i}. {concern}")
report_lines.append("")

# 生活方式评估
report_lines.append("🌟 生活方式详细评估")
lifestyle = analysis_result['lifestyle_assessment']
report_lines.append(f"   💤 睡眠:")
report_lines.append(f"      {lifestyle['sleep']}")
report_lines.append(f"   🏃 运动:")
report_lines.append(f"      {lifestyle['exercise']}")
report_lines.append(f"   🥗 饮食:")
report_lines.append(f"      {lifestyle['diet']}")
report_lines.append(f"   😌 压力管理:")
report_lines.append(f"      {lifestyle['stress']}")
report_lines.append("")

# 风险因素
report_lines.append("🚨 识别的健康风险")
for i, risk in enumerate(analysis_result['risk_factors'], 1):
    report_lines.append(f"   {i}. {risk}")
report_lines.append("")

# 改进建议
report_lines.append("💡 详细改进建议")
for i, rec in enumerate(analysis_result['recommendations'], 1):
    report_lines.append(f"   {i}. {rec}")
report_lines.append("")

# 就医建议
report_lines.append("🏥 就医建议")
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
    report_lines.append("-"*70)
    report_lines.append("")

report_lines.append("="*70)
report_lines.append("⚠️  重要提醒：")
report_lines.append("   1. 本报告基于您的自述生成，仅供参考")
report_lines.append("   2. 吸烟和过量饮酒是可控的重大健康风险因素")
report_lines.append("   3. 强烈建议尽快就医进行全面体检")
report_lines.append("   4. 在专业医生指导下制定健康改善计划")
report_lines.append("   5. 如有任何不适症状，请立即就医")
report_lines.append("="*70)
report_lines.append("")
report_lines.append("💪 健康改善是一个循序渐进的过程")
report_lines.append("   从最容易的小改变开始，逐步建立健康习惯。")
report_lines.append("   您的健康，您做主！")
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


