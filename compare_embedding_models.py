#!/usr/bin/env python3
"""
嵌入模型对比测试
比较不同模型在中文问题检索上的表现
"""

from src.core.question_rag_optimized import QuestionRAGOptimized, EmbeddingModel
import time


def test_model(model_name: str, model_enum: EmbeddingModel):
    """测试单个模型的性能"""
    print("\n" + "=" * 70)
    print(f"🧪 测试模型: {model_enum.value}")
    print("=" * 70)

    start_time = time.time()

    try:
        # 初始化 RAG
        rag = QuestionRAGOptimized(
            question_file='questions.yaml',
            embedding_model=model_enum.value,
            collection_name=f"test_{model_name}"
        )

        # 加载和索引
        if not rag.load_and_index_questions():
            print(f"❌ 模型 {model_name} 加载失败")
            return None

        init_time = time.time() - start_time
        print(f"⏱️  初始化耗时: {init_time:.2f}秒")

        # 测试检索
        test_contexts = [
            "用户说最近睡眠不好，经常失眠",
            "用户提到很少运动，总是坐着",
            "用户表示工作压力很大"
        ]

        print(f"\n🔍 检索测试:")
        retrieval_times = []

        for context in test_contexts:
            start = time.time()
            question = rag.retrieve_next_question(context, exclude_asked=False)
            retrieval_time = time.time() - start
            retrieval_times.append(retrieval_time)

            if question:
                print(f"  ✅ {context[:20]}... → {question.question[:30]}...")
                print(f"     耗时: {retrieval_time:.3f}秒")
            else:
                print(f"  ❌ 未检索到问题")

        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times)

        return {
            "model": model_name,
            "init_time": init_time,
            "avg_retrieval_time": avg_retrieval_time,
            "success": True
        }

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            "model": model_name,
            "error": str(e),
            "success": False
        }


def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║               嵌入模型对比测试                                         ║
║               Embedding Models Comparison                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

本测试将对比以下嵌入模型在中文问题检索上的表现：

1. BGE-Small-ZH (推荐) - BAAI 出品，轻量快速
2. BGE-Base-ZH - BAAI 出品，效果更好但较大
3. text2vec-base-chinese - 中文专用
4. Paraphrase-Multilingual (当前使用) - 多语言

注意：
- 首次运行会下载模型，需要一些时间
- 每个模型会创建独立的向量索引
- 测试完成后可以删除 test_* 开头的集合
    """)

    input("\n按 Enter 开始测试...")

    models_to_test = [
        ("bge_small", EmbeddingModel.BGE_SMALL_ZH),
        ("bge_base", EmbeddingModel.BGE_BASE_ZH),
        ("text2vec", EmbeddingModel.TEXT2VEC_BASE_CHINESE),
        ("multilingual", EmbeddingModel.PARAPHRASE_MULTILINGUAL),
    ]

    results = []

    for model_name, model_enum in models_to_test:
        result = test_model(model_name, model_enum)
        if result:
            results.append(result)

        # 清理显存
        import gc
        gc.collect()

    # 打印对比结果
    print("\n" + "=" * 70)
    print("📊 对比结果汇总")
    print("=" * 70 + "\n")

    print(f"{'模型':<30} {'初始化(秒)':<15} {'检索速度(秒)':<15} {'状态'}")
    print("-" * 70)

    for result in results:
        if result['success']:
            print(f"{result['model']:<30} "
                  f"{result['init_time']:<15.2f} "
                  f"{result['avg_retrieval_time']:<15.3f} "
                  f"✅")
        else:
            print(f"{result['model']:<30} "
                  f"{'N/A':<15} "
                  f"{'N/A':<15} "
                  f"❌ {result.get('error', 'Unknown')[:20]}")

    print("\n" + "=" * 70)
    print("💡 推荐:")
    print("  - 速度优先: BAAI/bge-small-zh-v1.5 (轻量快速)")
    print("  - 效果优先: BAAI/bge-base-zh-v1.5 (中文效果最好)")
    print("  - 平衡选择: shibing624/text2vec-base-chinese")
    print("=" * 70)

    print("\n🔧 如何切换模型:")
    print("  编辑 src/clients/interview_client_rag.py")
    print("  修改 QuestionRAG 初始化时的 embedding_model 参数")
    print("""
  例如：
  from src.core.question_rag_optimized import QuestionRAGOptimized, EmbeddingModel

  rag = QuestionRAGOptimized(
      question_file='questions.yaml',
      embedding_model=EmbeddingModel.BGE_SMALL_ZH.value  # 使用 BGE Small
  )
    """)


if __name__ == "__main__":
    main()
