"""
问题检索引擎 - 优化版（使用更好的中文嵌入模型）
支持多种嵌入模型选择：
1. text2vec-base-chinese（推荐）- 中文优化
2. bge-small-zh-v1.5（推荐）- BAAI 出品
3. paraphrase-multilingual（默认）- 多语言
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import yaml
import os
from dataclasses import dataclass
from enum import Enum


class EmbeddingModel(Enum):
    """支持的嵌入模型"""
    # 推荐：中文专用模型（更适合中文访谈）
    TEXT2VEC_BASE_CHINESE = "shibing624/text2vec-base-chinese"  # 约 400MB
    BGE_SMALL_ZH = "BAAI/bge-small-zh-v1.5"  # 约 100MB，轻量快速
    BGE_BASE_ZH = "BAAI/bge-base-zh-v1.5"  # 约 400MB，效果更好

    # 备选：多语言模型
    PARAPHRASE_MULTILINGUAL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # 备选：OpenAI（需要 API key）
    OPENAI_TEXT_EMBEDDING_3_SMALL = "openai:text-embedding-3-small"
    OPENAI_TEXT_EMBEDDING_3_LARGE = "openai:text-embedding-3-large"


@dataclass
class Question:
    """问题数据类"""
    id: int
    question: str
    type: str
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    follow_up_hints: Optional[List[str]] = None


class QuestionRAGOptimized:
    """优化的问题检索引擎"""

    def __init__(
        self,
        question_file: str = "questions.yaml",
        collection_name: str = "interview_questions",
        embedding_model: str = EmbeddingModel.BGE_SMALL_ZH.value,  # 默认使用中文模型
        persist_directory: str = "./chroma_db",
        use_openai: bool = False,
        openai_api_key: Optional[str] = None
    ):
        """
        初始化优化的 RAG 引擎

        Args:
            question_file: YAML 问题文件路径
            collection_name: ChromaDB 集合名称
            embedding_model: 嵌入模型名称
            persist_directory: 向量数据库持久化目录
            use_openai: 是否使用 OpenAI embeddings
            openai_api_key: OpenAI API key（使用 OpenAI 时需要）
        """
        self.question_file = question_file
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.use_openai = use_openai

        # 初始化嵌入模型
        if use_openai:
            print(f"🔄 使用 OpenAI Embeddings: {embedding_model}")
            self.embedding_model = None
            self.openai_client = self._init_openai(openai_api_key)
            self.embedding_model_name = embedding_model.replace("openai:", "")
        else:
            print(f"🔄 加载嵌入模型: {embedding_model}")
            self._print_model_info(embedding_model)
            self.embedding_model = SentenceTransformer(embedding_model)
            self.embedding_model_name = embedding_model
            self.openai_client = None

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
                metadata={
                    "description": "Interview questions for RAG-based retrieval",
                    "embedding_model": self.embedding_model_name
                }
            )
            print(f"✅ 创建新集合: {collection_name}")

        # 加载问题
        self.questions: List[Question] = []
        self.asked_question_ids: set = set()

    def _print_model_info(self, model_name: str):
        """打印模型信息"""
        model_info = {
            "shibing624/text2vec-base-chinese": {
                "name": "text2vec-base-chinese",
                "size": "约 400MB",
                "language": "中文专用",
                "performance": "⭐⭐⭐⭐⭐"
            },
            "BAAI/bge-small-zh-v1.5": {
                "name": "BGE Small Chinese",
                "size": "约 100MB",
                "language": "中文专用",
                "performance": "⭐⭐⭐⭐"
            },
            "BAAI/bge-base-zh-v1.5": {
                "name": "BGE Base Chinese",
                "size": "约 400MB",
                "language": "中文专用",
                "performance": "⭐⭐⭐⭐⭐"
            },
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": {
                "name": "Paraphrase Multilingual",
                "size": "约 120MB",
                "language": "多语言",
                "performance": "⭐⭐⭐"
            }
        }

        if model_name in model_info:
            info = model_info[model_name]
            print(f"   模型: {info['name']}")
            print(f"   大小: {info['size']}")
            print(f"   语言: {info['language']}")
            print(f"   性能: {info['performance']}")

    def _init_openai(self, api_key: Optional[str]):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("需要提供 OPENAI_API_KEY")
            return OpenAI(api_key=key)
        except ImportError:
            raise ImportError("使用 OpenAI 需要安装: pip install openai")

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        if self.use_openai:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=text
            )
            return response.data[0].embedding
        else:
            return self.embedding_model.encode(
                text,
                convert_to_numpy=True
            ).tolist()

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量获取嵌入向量"""
        if self.use_openai:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        else:
            return self.embedding_model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True
            ).tolist()

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
                # 检查模型是否一致
                metadata = self.collection.metadata
                if metadata.get('embedding_model') == self.embedding_model_name:
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
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Interview questions",
                    "embedding_model": self.embedding_model_name
                }
            )
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

        # 批量生成嵌入向量
        print(f"   正在向量化 {len(documents)} 个问题...")
        embeddings = self._get_embeddings_batch(documents)

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
        """根据对话上下文检索最相关的下一个问题"""
        try:
            # 生成查询向量
            query_embedding = self._get_embedding(context)

            # 检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results * 2, len(self.questions))
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
        """根据当前问题和用户回答生成追问建议"""
        if current_question.follow_up_hints:
            return current_question.follow_up_hints[:n_results]

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
        """重置已提问记录"""
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


def analyze_answer_completeness(question: str, answer: str) -> Dict[str, Any]:
    """分析回答完整性"""
    answer_length = len(answer)

    if answer_length < 10:
        return {
            'is_complete': False,
            'confidence': 0.8,
            'reason': '回答过于简短'
        }

    negative_words = ['不', '没有', '没', '无']
    if any(word in answer for word in negative_words) and answer_length < 20:
        return {
            'is_complete': False,
            'confidence': 0.6,
            'reason': '简单否定，可能需要展开'
        }

    return {
        'is_complete': True,
        'confidence': 0.7,
        'reason': '回答长度合理'
    }


# 向后兼容：导出为 QuestionRAG
QuestionRAG = QuestionRAGOptimized
