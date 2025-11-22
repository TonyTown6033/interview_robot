#!/usr/bin/env python3
"""
健康分析 MCP 服务器
使用 Step API 分析访谈内容，生成健康评估报告
"""

import os
import json
import asyncio
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
import requests

# 配置
API_KEY = os.getenv("STEPFUN_API_KEY", "")
API_URL = "https://api.stepfun.com/v1/chat/completions"


async def analyze_health_interview(answers: list[dict], questions_count: int) -> dict:
    """
    使用 Step API 分析健康访谈内容
    
    Args:
        answers: 问答列表 [{"question": "...", "answer": "..."}]
        questions_count: 总问题数
        
    Returns:
        分析结果字典
    """
    # 构建分析提示词
    interview_text = "\n\n".join([
        f"问题 {i+1}: {item['question']}\n回答: {item['answer']}"
        for i, item in enumerate(answers)
    ])
    
    system_prompt = """你是一位专业的健康顾问，负责分析患者的健康咨询访谈记录。

请从以下几个维度进行分析：
1. **整体健康状况评估**：综合评价患者的健康状态（良好/一般/需要关注）
2. **主要健康关注点**：识别患者提到的主要健康问题或风险
3. **生活方式评估**：分析睡眠、运动、饮食等生活习惯
4. **风险因素识别**：指出可能存在的健康风险
5. **改进建议**：提供3-5条具体的健康改进建议
6. **就医建议**：是否需要进一步体检或就医

请以 JSON 格式输出分析结果，包含以下字段：
- overall_health: 整体评估（good/fair/concerning）
- health_score: 健康评分（0-100）
- main_concerns: 主要关注点列表
- lifestyle_assessment: 生活方式评估
- risk_factors: 风险因素列表
- recommendations: 改进建议列表
- medical_advice: 就医建议
- summary: 总结（200字以内）

注意：
1. 基于患者实际回答进行分析，不要臆测
2. 建议要具体、可操作
3. 如果信息不足，说明需要更多信息
4. 保持专业、客观的态度
"""

    user_prompt = f"""请分析以下健康咨询访谈记录：

{interview_text}

总计 {questions_count} 个问题，已回答 {len(answers)} 个。

请提供详细的健康分析报告。"""

    try:
        # 调用 Step API
        headers = {
            "Authorization": f"Bearer {API_KEY}",
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
        
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            analysis = json.loads(content)
            
            # 添加元数据
            analysis["meta"] = {
                "total_questions": questions_count,
                "answered_questions": len(answers),
                "completion_rate": len(answers) / questions_count if questions_count > 0 else 0,
                "model": "step-2-16k"
            }
            
            return analysis
        else:
            return {
                "error": f"API 调用失败: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        return {
            "error": "分析失败",
            "message": str(e)
        }


# 创建 MCP 服务器
app = Server("health-analyzer")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="analyze_health_interview",
            description="分析健康咨询访谈内容，生成专业的健康评估报告。输入访谈的问答对，返回包含健康评估、风险因素和改进建议的详细报告。",
            inputSchema={
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "description": "问答列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string", "description": "问题文本"},
                                "answer": {"type": "string", "description": "回答文本"}
                            },
                            "required": ["question", "answer"]
                        }
                    },
                    "questions_count": {
                        "type": "integer",
                        "description": "总问题数"
                    }
                },
                "required": ["answers", "questions_count"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    if name == "analyze_health_interview":
        answers = arguments.get("answers", [])
        questions_count = arguments.get("questions_count", 0)
        
        # 执行分析
        result = await analyze_health_interview(answers, questions_count)
        
        # 返回格式化的结果
        return [
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """运行 MCP 服务器"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

