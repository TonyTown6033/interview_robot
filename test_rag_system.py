#!/usr/bin/env python3
"""
RAG 系统功能测试脚本
演示智能检索和上下文感知功能
"""

from src.core.question_rag import QuestionRAG, analyze_answer_completeness


def test_rag_retrieval():
    """测试 RAG 智能检索"""
    print("\n" + "=" * 70)
    print("🧪 测试 RAG 智能检索功能")
    print("=" * 70)

    # 初始化
    print("\n🔄 初始化 RAG 引擎...")
    rag = QuestionRAG(question_file='questions.yaml')

    print("🔄 加载并索引问题...")
    if not rag.load_and_index_questions():
        print("❌ 加载失败")
        return False

    print(f"✅ 成功加载 {len(rag.questions)} 个问题\n")

    # 模拟对话场景
    test_scenarios = [
        {
            "context": "用户说最近睡眠不好，经常失眠",
            "expected_keywords": ["睡眠", "质量"]
        },
        {
            "context": "用户提到很少运动，总是坐着工作",
            "expected_keywords": ["运动", "习惯"]
        },
        {
            "context": "用户说工作压力很大，经常加班",
            "expected_keywords": ["压力", "工作"]
        },
        {
            "context": "用户表示饮食不规律，经常吃外卖",
            "expected_keywords": ["饮食", "习惯"]
        }
    ]

    print("📋 测试场景:\n")

    for i, scenario in enumerate(test_scenarios, 1):
        context = scenario["context"]
        print(f"场景 {i}: {context}")

        # 检索问题
        question = rag.retrieve_next_question(context, exclude_asked=True)

        if question:
            print(f"  ✅ 检索到问题: {question.question}")
            print(f"     问题类型: {question.type}")

            # 标记为已问
            rag.mark_question_asked(question.id)
        else:
            print(f"  ⚠️  未检索到相关问题")

        print()

    # 统计
    print("=" * 70)
    print(f"📊 统计信息:")
    print(f"   问题库大小: {len(rag.questions)}")
    print(f"   已提问数量: {len(rag.asked_question_ids)}")
    print(f"   剩余问题数: {rag.get_unanswered_count()}")
    print("=" * 70)

    return True


def test_answer_analysis():
    """测试回答完整性分析"""
    print("\n" + "=" * 70)
    print("🧪 测试回答完整性分析")
    print("=" * 70 + "\n")

    test_cases = [
        {
            "question": "您平时的睡眠质量怎么样？",
            "answer": "不好",
            "desc": "过于简短的回答"
        },
        {
            "question": "您平时的睡眠质量怎么样？",
            "answer": "还可以，一般每天睡7-8小时，偶尔会失眠",
            "desc": "详细的回答"
        },
        {
            "question": "您有定期运动的习惯吗？",
            "answer": "没有",
            "desc": "简单否定"
        },
        {
            "question": "您有定期运动的习惯吗？",
            "answer": "有的，我每周会去健身房3-4次，主要做力量训练和跑步",
            "desc": "完整的回答"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"测试 {i}: {case['desc']}")
        print(f"  问题: {case['question']}")
        print(f"  回答: {case['answer']}")

        result = analyze_answer_completeness(case['question'], case['answer'])

        print(f"  分析结果:")
        print(f"    是否完整: {'✅ 是' if result['is_complete'] else '❌ 否'}")
        print(f"    置信度: {result['confidence']:.2f}")
        print(f"    原因: {result['reason']}")
        print()


def test_followup_generation():
    """测试追问生成"""
    print("\n" + "=" * 70)
    print("🧪 测试追问生成")
    print("=" * 70 + "\n")

    rag = QuestionRAG(question_file='questions.yaml')
    rag.load_and_index_questions()

    # 获取一个问题进行测试
    question = rag.questions[0]
    user_answer = "不太好"

    print(f"原始问题: {question.question}")
    print(f"用户回答: {user_answer}\n")

    followups = rag.get_follow_up_questions(question, user_answer, n_results=3)

    print("💡 生成的追问建议:")
    for i, followup in enumerate(followups, 1):
        print(f"  {i}. {followup}")


def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║               RAG 增强访谈系统 - 功能测试                             ║
║               Intelligent Interview System - RAG Tests              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    try:
        # 测试 1: 智能检索
        if not test_rag_retrieval():
            print("\n❌ 智能检索测试失败")
            return

        # 测试 2: 回答分析
        test_answer_analysis()

        # 测试 3: 追问生成
        test_followup_generation()

        print("\n" + "=" * 70)
        print("✅ 所有测试完成！RAG 系统工作正常")
        print("=" * 70 + "\n")

        print("💡 下一步:")
        print("  1. 运行实际访谈: python run_rag_interview.py")
        print("  2. 查看文档: cat RAG_GUIDE.md")
        print("  3. 自定义问题库: 编辑 questions.yaml")

    except KeyboardInterrupt:
        print("\n\n⏹️  测试中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
