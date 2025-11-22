"""
问题检索引擎 - 基于 RAG (Retrieval-Augmented Generation)
使用向量数据库存储和检索访谈问题
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import yaml
import os
from dataclasses import dataclass


@dataclass
class Question:
    """问题数据类"""
    id: int
    question: str
    type: str
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    follow_up_hints: Optional[List[str]] = None


class QuestionRAG:
    """问题检索引擎"""

    def __init__(
        self,
        question_file: str = "questions.yaml",
        collection_name: str = "interview_questions",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        persist_directory: str = "./chroma_db"
    ):
        """
        初始化 RAG 引擎

        Args:
            question_file: YAML 问题文件路径
            collection_name: ChromaDB 集合名称
            embedding_model: 嵌入模型名称（使用支持中文的模型）
            persist_directory: 向量数据库持久化目录
        """
        self.question_file = question_file
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # 初始化嵌入模型
        print(f"🔄 加载嵌入模型: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # 初始化 ChromaDB
        print(f"🔄 初始化向量数据库: {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"✅ 加载已有集合: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Interview questions for RAG-based retrieval"}
            )
            print(f"✅ 创建新集合: {collection_name}")

        # 加载问题
        self.questions: List[Question] = []
        self.asked_question_ids: set = set()  # 已提问的问题ID

    def load_and_index_questions(self) -> bool:
        """从 YAML 加载问题并建立索引"""
        try:
            with open(self.question_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            questions_data = data.get('questions', [])
            if not questions_data:
                print("❌ 未找到问题数据")
                return False

            self.questions = [
                Question(
                    id=q['id'],
                    question=q['question'],
                    type=q.get('type', 'open'),
                    category=q.get('category'),
                    keywords=q.get('keywords'),
                    follow_up_hints=q.get('follow_up_hints')
                )
                for q in questions_data
            ]

            print(f"📚 加载了 {len(self.questions)} 个问题")

            # 检查是否需要重新索引
            current_count = self.collection.count()
            if current_count == len(self.questions):
                print(f"✅ 向量数据库已包含所有问题，跳过索引")
                return True

            # 建立向量索引
            print("🔄 正在建立向量索引...")
            self._build_index()
            print("✅ 向量索引建立完成")

            return True

        except Exception as e:
            print(f"❌ 加载问题失败: {e}")
            return False

    def _build_index(self):
        """将问题向量化并存入 ChromaDB"""
        # 清空旧数据
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(name=self.collection_name)
        except Exception:
            pass

        # 准备数据
        documents = []
        metadatas = []
        ids = []

        for q in self.questions:
            # 构建富文本（用于更好的语义理解）
            doc_text = f"{q.question}"
            if q.category:
                doc_text += f" [类别: {q.category}]"
            if q.keywords:
                doc_text += f" [关键词: {', '.join(q.keywords)}]"

            documents.append(doc_text)
            metadatas.append({
                "id": q.id,
                "type": q.type,
                "category": q.category or "",
                "question_text": q.question
            })
            ids.append(f"q_{q.id}")

        # 生成嵌入向量
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()

        # 批量插入
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ 已索引 {len(documents)} 个问题")

    def retrieve_next_question(
        self,
        context: str,
        n_results: int = 3,
        exclude_asked: bool = True
    ) -> Optional[Question]:
        """
        根据对话上下文检索最相关的下一个问题

        Args:
            context: 对话上下文（可以是最近的回答或整个对话摘要）
            n_results: 检索候选问题数量
            exclude_asked: 是否排除已提问的问题

        Returns:
            最相关的问题对象
        """
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(
                context,
                convert_to_numpy=True
            ).tolist()

            # 检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results * 2, len(self.questions))  # 多检索一些，以防需要过滤
            )

            # 解析结果
            if not results['metadatas'] or not results['metadatas'][0]:
                return None

            # 选择最佳问题
            for metadata in results['metadatas'][0]:
                question_id = metadata['id']

                # 跳过已问过的问题
                if exclude_asked and question_id in self.asked_question_ids:
                    continue

                # 找到对应的问题对象
                question = next((q for q in self.questions if q.id == question_id), None)
                if question:
                    return question

            # 如果所有相关问题都问过了，返回任意未问过的问题
            for q in self.questions:
                if q.id not in self.asked_question_ids:
                    return q

            return None

        except Exception as e:
            print(f"❌ 检索问题失败: {e}")
            return None

    def get_follow_up_questions(
        self,
        current_question: Question,
        user_answer: str,
        n_results: int = 2
    ) -> List[str]:
        """
        根据当前问题和用户回答生成追问建议

        Args:
            current_question: 当前问题对象
            user_answer: 用户的回答文本
            n_results: 返回的追问建议数量

        Returns:
            追问建议列表
        """
        # 如果问题预设了追问提示
        if current_question.follow_up_hints:
            return current_question.follow_up_hints[:n_results]

        # 基于回答内容生成通用追问（后续可以接入 LLM 生成）
        generic_followups = [
            "能详细说说吗？",
            "这种情况持续多久了？",
            "有什么具体的例子吗？"
        ]

        return generic_followups[:n_results]

    def mark_question_asked(self, question_id: int):
        """标记问题已提问"""
        self.asked_question_ids.add(question_id)

    def reset_asked_questions(self):
        """重置已提问记录（新会话时调用）"""
        self.asked_question_ids.clear()

    def get_all_questions(self) -> List[Question]:
        """获取所有问题"""
        return self.questions

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """根据ID获取问题"""
        return next((q for q in self.questions if q.id == question_id), None)

    def get_unanswered_count(self) -> int:
        """获取未回答问题数量"""
        return len(self.questions) - len(self.asked_question_ids)


# 辅助函数：分析回答完整性
def analyze_answer_completeness(question: str, answer: str) -> Dict[str, Any]:
    """
    简单分析回答是否完整
    后续可以接入 LLM 做更智能的分析

    Returns:
        {
            'is_complete': bool,  # 是否完整
            'confidence': float,  # 置信度
            'reason': str  # 判断理由
        }
    """
    # 简单规则判断
    answer_length = len(answer)

    # 太短的回答可能不完整
    if answer_length < 10:
        return {
            'is_complete': False,
            'confidence': 0.8,
            'reason': '回答过于简短'
        }

    # 包含否定词但没有展开
    negative_words = ['不', '没有', '没', '无']
    if any(word in answer for word in negative_words) and answer_length < 20:
        return {
            'is_complete': False,
            'confidence': 0.6,
            'reason': '简单否定，可能需要展开'
        }

    # 默认认为完整
    return {
        'is_complete': True,
        'confidence': 0.7,
        'reason': '回答长度合理'
    }
