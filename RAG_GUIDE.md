# RAG 增强访谈系统使用指南

## 概述

基于 RAG（Retrieval-Augmented Generation）的智能访谈系统，结合向量数据库和实时语音对话，提供更灵活、更智能的访谈体验。

## 核心特性

### 1. **智能问题检索**
- 使用 ChromaDB 向量数据库存储问题
- 根据对话上下文自动检索最相关的问题
- 不再按固定顺序提问，而是根据用户回答动态调整

### 2. **灵活的 AI 对话**
- AI 可以用自然的方式表述问题（不是机械朗读）
- 自动添加对话过渡语（"好的，明白了"、"接下来"等）
- 保持对话流畅自然

### 3. **智能追问**
- 自动检测回答是否完整
- 对过于简短或不清晰的回答进行追问
- 追问内容基于知识库，不是随机生成

### 4. **上下文感知**
- 维护对话历史
- 根据之前的回答选择后续问题
- 避免重复提问

## 系统架构

```
┌─────────────────────────────────────────────┐
│         RAG 增强访谈客户端                    │
│      (interview_client_rag.py)             │
│                                             │
│  ┌──────────────┐      ┌────────────────┐  │
│  │ 对话上下文   │◄────►│  RAG 检索引擎  │  │
│  │ 管理器       │      │  (question_rag)│  │
│  └──────────────┘      └────────────────┘  │
│         │                      ▲            │
│         │                      │            │
│         ▼                      │            │
│  ┌──────────────┐      ┌────────────────┐  │
│  │  Realtime    │      │   ChromaDB     │  │
│  │  API 对话    │      │   向量数据库    │  │
│  └──────────────┘      └────────────────┘  │
└─────────────────────────────────────────────┘
```

## 安装依赖

```bash
# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

主要新增依赖：
- `chromadb>=0.4.22` - 向量数据库
- `sentence-transformers>=2.5.1` - 中文嵌入模型
- `openai>=1.12.0` - （可选）用于嵌入

## 使用方法

### 1. 准备问题库

在 `questions.yaml` 中定义问题。系统会自动：
- 将问题向量化
- 建立语义索引
- 支持基于语义的检索

示例格式：
```yaml
questions:
  - id: 1
    question: "您好，请问您最近的身体状况如何？"
    type: "open"
    category: "基础健康"
    keywords: ["健康状况", "身体", "不适"]
    follow_up_hints: ["能详细说说吗？", "这种情况持续多久了？"]

  - id: 2
    question: "您平时的睡眠质量怎么样？"
    type: "open"
    category: "生活习惯"
    keywords: ["睡眠", "休息"]
```

### 2. 设置环境变量

```bash
export STEPFUN_API_KEY='your-api-key-here'
```

### 3. 运行 RAG 增强版访谈

```bash
# 直接运行
python -m src.clients.interview_client_rag

# 或使用入口脚本
python run_rag_interview.py
```

### 4. 首次运行

首次运行时，系统会：
1. 加载 `questions.yaml` 中的所有问题
2. 使用 Sentence-Transformers 生成嵌入向量
3. 将向量存储到 ChromaDB（存储在 `./chroma_db` 目录）
4. 后续运行会直接使用已建立的索引

## 配置参数

在 `interview_client_rag.py` 的 `main()` 函数中可以调整：

```python
client = RAGInterviewClient(
    API_KEY,
    question_file="questions.yaml",           # 问题文件路径
    model=ModelType.STEP_AUDIO_2.value,       # 语音模型
    temperature=0.7,                          # AI 灵活度 (0.0-1.0)
    vad_threshold=0.5,                        # 语音检测阈值
    vad_silence_duration_ms=700,              # 静音检测时长
    max_questions=10,                         # 最多提问数量
)
```

### 参数说明

- **temperature**: 控制 AI 回答的灵活性
  - `0.3-0.5`: 保守，更贴近原始问题
  - `0.7`: 平衡（推荐）
  - `0.8-1.0`: 灵活，表述更多样化

- **max_questions**: 控制访谈长度
  - 系统会从问题库中智能选择最相关的问题
  - 不会超过问题库总数

- **vad_threshold**: 语音激活检测阈值
  - `0.3-0.4`: 灵敏
  - `0.5`: 标准（推荐）
  - `0.6-0.8`: 不灵敏

## 对比三种模式

| 特性 | V2 版（指令驱动） | Hybrid 版（TTS+Realtime） | RAG 版（智能+灵活） |
|------|------------------|-------------------------|-------------------|
| 问题来源 | YAML 固定顺序 | YAML 固定顺序 | RAG 智能检索 |
| 问题表述 | AI 严格朗读 | TTS 完全准确 | AI 灵活表述 |
| 对话自然度 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 准确性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 灵活性 | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 追问能力 | ❌ | ❌ | ✅ |
| 上下文感知 | ❌ | ❌ | ✅ |

## 工作流程示例

### 传统模式（固定顺序）
```
AI: 您好，请问您最近的身体状况如何？
用户: 还可以
AI: 您平时的睡眠质量怎么样？
用户: 不太好
AI: 您有定期运动的习惯吗？
...
```

### RAG 增强模式（智能+灵活）
```
AI: 您好，欢迎参加健康咨询。首先想了解一下，您最近的身体状况如何呢？
用户: 还可以，就是有点累

AI: 明白了。那我想问问，您平时睡眠质量怎么样？
用户: 不好

AI: 能详细说说吗？比如是入睡困难还是容易醒？
用户: 入睡很难，经常要一两个小时

AI: 好的，了解了。那您平时工作压力大吗？
用户: 挺大的
...
```

注意 RAG 模式的特点：
1. AI 会根据"累"这个关键词，智能检索到"睡眠"相关问题
2. 检测到回答过于简短，自动追问
3. 添加自然的过渡语
4. 根据"睡眠不好"的上下文，接着问"压力"相关问题

## 高级功能

### 自定义嵌入模型

在 `question_rag.py` 中可以更换嵌入模型：

```python
question_rag = QuestionRAG(
    question_file="questions.yaml",
    embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 默认
    # 或使用其他中文模型：
    # embedding_model="shibing624/text2vec-base-chinese"
)
```

### 调整检索策略

修改 `retrieve_next_question()` 的参数：

```python
question = self.question_rag.retrieve_next_question(
    context=context,
    n_results=3,        # 检索候选数量
    exclude_asked=True  # 是否排除已问过的
)
```

### 自定义追问逻辑

在 `question_rag.py` 的 `analyze_answer_completeness()` 函数中自定义规则：

```python
def analyze_answer_completeness(question: str, answer: str) -> Dict[str, Any]:
    # 添加你的判断逻辑
    if len(answer) < 10:
        return {'is_complete': False, 'confidence': 0.8, 'reason': '回答过于简短'}
    # ...
```

## 数据存储

### 向量数据库
- 位置: `./chroma_db/`
- 格式: ChromaDB 持久化存储
- 清空: 删除该目录即可重建索引

### 会话记录
- 位置: `./sessions/`
- 格式: JSON
- 包含: 问题、回答、时间戳、会话元数据

## 常见问题

### Q: 如何更新问题库？
A: 修改 `questions.yaml` 后，删除 `./chroma_db/` 目录，系统会自动重建索引。

### Q: 如何让 AI 更严格地遵循原始问题？
A: 降低 `temperature` 参数到 0.3-0.5。

### Q: 如何禁用追问功能？
A: 在 `_ask_question_rag()` 中注释掉 `self._check_and_followup()` 调用。

### Q: 向量化很慢怎么办？
A: 首次运行会下载模型并建立索引，后续运行会很快。可以使用更小的嵌入模型。

## 下一步改进

- [ ] 集成 LLM 生成更智能的追问
- [ ] 支持多轮对话的深度上下文理解
- [ ] 添加对话质量评分
- [ ] 支持动态调整问题库（在线学习）
- [ ] 集成 MCP (Model Context Protocol) 服务器

## 许可证

MIT License
