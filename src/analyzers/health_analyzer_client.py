"""
健康分析客户端 - 用于调用 MCP 服务器
简化版：直接使用 Step API，不依赖 MCP 基础设施
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional


class HealthAnalyzerClient:
    """健康分析客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STEPFUN_API_KEY", "")
        self.api_url = "https://api.stepfun.com/v1/chat/completions"
        
    def analyze_interview(self, answers: List[Dict[str, str]], questions_count: int) -> Dict[str, Any]:
        """
        分析健康访谈内容
        
        Args:
            answers: 问答列表 [{"question": "...", "answer": "..."}]
            questions_count: 总问题数
            
        Returns:
            分析结果字典
        """
        if not self.api_key:
            return {
                "error": "未设置 API Key",
                "message": "请设置环境变量 STEPFUN_API_KEY"
            }
        
        # 构建访谈文本
        interview_text = "\n\n".join([
            f"问题 {i+1}: {item['question']}\n回答: {item['answer']}"
            for i, item in enumerate(answers)
        ])
        
        system_prompt = """你是一位专业的健康顾问，负责分析患者的健康咨询访谈记录。

请从以下几个维度进行分析：
1. **整体健康状况评估**：综合评价患者的健康状态
2. **主要健康关注点**：识别患者提到的主要健康问题或风险
3. **生活方式评估**：分析睡眠、运动、饮食等生活习惯
4. **风险因素识别**：指出可能存在的健康风险
5. **改进建议**：提供3-5条具体的健康改进建议
6. **就医建议**：是否需要进一步体检或就医

请以 JSON 格式输出分析结果，包含以下字段：
{
  "overall_health": "整体评估（good/fair/concerning）",
  "health_score": "健康评分（0-100）",
  "main_concerns": ["关注点1", "关注点2"],
  "lifestyle_assessment": {
    "sleep": "睡眠评估",
    "exercise": "运动评估",
    "diet": "饮食评估",
    "stress": "压力评估"
  },
  "risk_factors": ["风险因素1", "风险因素2"],
  "recommendations": ["建议1", "建议2", "建议3"],
  "medical_advice": "就医建议",
  "summary": "总结（200字以内）"
}

注意：
1. 基于患者实际回答进行分析，不要臆测
2. 建议要具体、可操作
3. 如果信息不足，在 summary 中说明
4. 保持专业、客观、关怀的态度
5. 避免给出诊断，仅提供健康建议"""

        user_prompt = f"""请分析以下健康咨询访谈记录：

{interview_text}

访谈统计：
- 总问题数: {questions_count}
- 已回答数: {len(answers)}
- 完成率: {len(answers)/questions_count*100:.1f}%

请提供详细的健康分析报告。"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "step-2-16k",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            
            print("\n🤖 正在调用 AI 分析健康访谈内容...")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                analysis = json.loads(content)
                
                # 添加元数据
                analysis["meta"] = {
                    "total_questions": questions_count,
                    "answered_questions": len(answers),
                    "completion_rate": f"{len(answers)/questions_count*100:.1f}%" if questions_count > 0 else "0%",
                    "model": "step-2-16k",
                    "tokens_used": result.get("usage", {})
                }
                
                return analysis
            else:
                return {
                    "error": f"API 调用失败: {response.status_code}",
                    "message": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "error": "请求超时",
                "message": "AI 分析超时，请稍后重试"
            }
        except json.JSONDecodeError as e:
            return {
                "error": "解析失败",
                "message": f"无法解析 AI 返回的 JSON: {e}"
            }
        except Exception as e:
            return {
                "error": "分析失败",
                "message": str(e)
            }
    
    def format_report(self, analysis: Dict[str, Any]) -> str:
        """
        格式化分析报告为可读文本
        
        Args:
            analysis: 分析结果字典
            
        Returns:
            格式化的文本报告
        """
        if "error" in analysis:
            return f"❌ 分析失败: {analysis.get('message', '未知错误')}"
        
        report = []
        report.append("=" * 70)
        report.append("📋 健康访谈分析报告")
        report.append("=" * 70)
        report.append("")
        
        # 元数据
        if "meta" in analysis:
            meta = analysis["meta"]
            report.append("📊 访谈统计")
            report.append(f"   • 问题总数: {meta.get('total_questions', 0)}")
            report.append(f"   • 已回答数: {meta.get('answered_questions', 0)}")
            report.append(f"   • 完成率: {meta.get('completion_rate', '0%')}")
            report.append("")
        
        # 整体评估
        overall = analysis.get("overall_health", "unknown")
        score = analysis.get("health_score", 0)
        overall_emoji = {"good": "✅", "fair": "⚠️", "concerning": "🔴"}.get(overall, "❓")
        
        report.append(f"🏥 整体健康状况: {overall_emoji} {overall.upper()}")
        report.append(f"📈 健康评分: {score}/100")
        report.append("")
        
        # 总结
        if "summary" in analysis:
            report.append("📝 综合评估")
            report.append(f"   {analysis['summary']}")
            report.append("")
        
        # 主要关注点
        if "main_concerns" in analysis and analysis["main_concerns"]:
            report.append("⚠️  主要健康关注点")
            for i, concern in enumerate(analysis["main_concerns"], 1):
                report.append(f"   {i}. {concern}")
            report.append("")
        
        # 生活方式评估
        if "lifestyle_assessment" in analysis:
            lifestyle = analysis["lifestyle_assessment"]
            report.append("🌟 生活方式评估")
            if isinstance(lifestyle, dict):
                if "sleep" in lifestyle:
                    report.append(f"   💤 睡眠: {lifestyle['sleep']}")
                if "exercise" in lifestyle:
                    report.append(f"   🏃 运动: {lifestyle['exercise']}")
                if "diet" in lifestyle:
                    report.append(f"   🥗 饮食: {lifestyle['diet']}")
                if "stress" in lifestyle:
                    report.append(f"   😌 压力: {lifestyle['stress']}")
            else:
                report.append(f"   {lifestyle}")
            report.append("")
        
        # 风险因素
        if "risk_factors" in analysis and analysis["risk_factors"]:
            report.append("🚨 识别的风险因素")
            for i, risk in enumerate(analysis["risk_factors"], 1):
                report.append(f"   {i}. {risk}")
            report.append("")
        
        # 改进建议
        if "recommendations" in analysis and analysis["recommendations"]:
            report.append("💡 健康改进建议")
            for i, rec in enumerate(analysis["recommendations"], 1):
                report.append(f"   {i}. {rec}")
            report.append("")
        
        # 就医建议
        if "medical_advice" in analysis:
            report.append("🏥 就医建议")
            report.append(f"   {analysis['medical_advice']}")
            report.append("")
        
        report.append("=" * 70)
        report.append("")
        report.append("⚠️  免责声明：本报告仅供参考，不构成医疗诊断或治疗建议。")
        report.append("   如有健康问题，请咨询专业医疗机构。")
        report.append("=" * 70)
        
        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    # 测试分析功能
    client = HealthAnalyzerClient()
    
    test_answers = [
        {
            "question": "您好，请问您最近的身体状况如何？有没有感到不适？",
            "answer": "最近感觉还可以，就是偶尔会觉得腰有点酸"
        },
        {
            "question": "您平时的睡眠质量怎么样？每天大概睡几个小时？",
            "answer": "睡眠不太好，经常失眠，一般只能睡5-6个小时"
        },
        {
            "question": "您有定期运动的习惯吗？一般做什么类型的运动？",
            "answer": "几乎不运动，工作太忙了"
        }
    ]
    
    result = client.analyze_interview(test_answers, 7)
    
    if "error" not in result:
        print(client.format_report(result))
    else:
        print(f"❌ 错误: {result['message']}")

