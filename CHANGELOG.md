# 更新日志

## [RAG Enhancement] - 2025-11-22

### 🎉 新功能

#### 1. RAG 智能检索系统
- ✅ 实现基于 RAG (Retrieval-Augmented Generation) 的问题检索
- ✅ 使用 ChromaDB 向量数据库存储问题
- ✅ 根据对话上下文智能选择下一个问题
- ✅ 避免固定顺序提问，更自然灵活

#### 2. 智能追问机制
- ✅ 自动检测回答完整性
- ✅ 对过于简短的回答进行追问
- ✅ 基于知识库的追问建议

#### 3. 上下文感知对话
- ✅ 维护对话历史
- ✅ 根据之前的回答调整后续问题
- ✅ 避免重复提问

#### 4. 灵活的 AI 表述
- ✅ AI 可以自然表述问题，不再机械朗读
- ✅ 自动添加对话过渡语
- ✅ 保持对话流畅性

#### 5. 多嵌入模型支持
- ✅ 支持多种中文嵌入模型
- ✅ BGE-Small-ZH (推荐，轻量)
- ✅ BGE-Base-ZH (推荐，效果好)
- ✅ text2vec-base-chinese
- ✅ Paraphrase-Multilingual
- ✅ OpenAI Embeddings (可选)

### 📄 新增文件

```
src/
├── core/
│   ├── question_rag.py                 # RAG 引擎核心
│   └── question_rag_optimized.py       # 优化版 RAG 引擎（多模型支持）
└── clients/
    └── interview_client_rag.py         # RAG 增强访谈客户端

文档:
├── RAG_GUIDE.md                        # RAG 系统使用指南
├── EMBEDDING_MODELS_GUIDE.md           # 嵌入模型选择指南
└── CHANGELOG.md                        # 本文件

示例和测试:
├── questions_rag_example.yaml          # 增强版问题库示例
├── run_rag_interview.py                # RAG 访谈快速启动脚本
├── test_rag_system.py                  # RAG 系统功能测试
└── compare_embedding_models.py         # 嵌入模型对比测试

数据:
└── chroma_db/                          # 向量数据库（自动生成）
```

### 🔧 依赖更新

新增依赖包：
```toml
chromadb>=0.4.22           # 向量数据库
sentence-transformers>=2.5.1  # 嵌入模型
openai>=1.12.0             # OpenAI API（可选）
```

### 🐛 Bug 修复

#### 修复 1: Answer 对象访问错误
**问题**:
```python
TypeError: 'Answer' object is not subscriptable
```

**原因**:
`SessionRecorder.answers` 存储的是 `Answer` 对象，不是字典

**修复**:
```python
# 错误
answers[-1]["transcript"] += "追问"

# 正确
answers[-1].transcript += "追问"
```

**位置**: `src/clients/interview_client_rag.py:602`

#### 修复 2: 并发响应冲突
**问题**:
```
❌ 错误: {'message': 'ongoing response already exists', 'type': 'invalid_request_error'}
```

**原因**:
在 AI 还在响应时发送新的 `response.create`

**修复**:
在追问前等待上一个响应完成

```python
# 确保上一个响应已完成
if self.is_ai_speaking:
    print("⏳ 等待 AI 完成当前响应...")
    self.ai_finished_speaking.wait(timeout=5)
    time.sleep(0.5)
```

**位置**: `src/clients/interview_client_rag.py:574-577`

### 📊 测试结果

#### RAG 智能检索测试
```
✅ 场景 1: "用户说最近睡眠不好，经常失眠"
   → 检索到: "您平时的睡眠质量怎么样？"

✅ 场景 2: "用户提到很少运动，总是坐着工作"
   → 检索到: "您平时工作压力大吗？"

✅ 场景 3: "用户表示饮食不规律，经常吃外卖"
   → 检索到: "您的饮食习惯如何？"
```

#### 回答完整性分析测试
```
✅ "不好" → ❌ 不完整 (置信度 0.80) → 触发追问
✅ "还可以，一般每天睡7-8小时" → ✅ 完整 (置信度 0.70)
```

#### 追问生成测试
```
✅ 原始问题: "您最近的身体状况如何？"
✅ 用户回答: "不太好"
✅ 生成追问:
   1. "能详细说说吗？"
   2. "这种情况持续多久了？"
   3. "有什么具体的例子吗？"
```

### 🔍 关于阶跃星辰 Embeddings

**调研结果**: 阶跃星辰目前**没有**公开的 Embeddings API

**已提供的 API**:
- ✅ Chat Completions
- ✅ Realtime API
- ✅ TTS/STT
- ✅ Image Generation
- ✅ Vector Store (内部使用 embeddings，不对外暴露)

**替代方案**: 使用国产开源中文嵌入模型
- 推荐: BAAI/bge-small-zh-v1.5
- 备选: BAAI/bge-base-zh-v1.5, text2vec-base-chinese

### 🚀 性能提升

| 指标 | 传统模式 | RAG 模式 |
|------|---------|---------|
| 问题选择 | 固定顺序 | 智能检索 |
| 对话自然度 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 追问能力 | ❌ | ✅ |
| 上下文理解 | ❌ | ✅ |
| 灵活性 | ⭐ | ⭐⭐⭐⭐⭐ |

### 📝 使用示例

#### 快速开始
```bash
# 安装依赖
pip install chromadb sentence-transformers

# 运行 RAG 访谈
python run_rag_interview.py
```

#### 切换嵌入模型
```python
from src.core.question_rag_optimized import QuestionRAGOptimized, EmbeddingModel

rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.BGE_SMALL_ZH.value  # 中文优化
)
```

#### 测试 RAG 功能
```bash
# 功能测试
python test_rag_system.py

# 模型对比
python compare_embedding_models.py
```

### 💡 最佳实践

1. **开发阶段**: 使用 `BGE-Small-ZH` (快速迭代)
2. **生产环境**: 使用 `BGE-Base-ZH` (最佳效果)
3. **资源受限**: 使用 `Paraphrase-Multilingual` (最小模型)

### ⚠️ 已知限制

1. **首次运行慢**: 需要下载嵌入模型（约 100-400MB）
2. **内存占用**: 模型加载需要 500MB-1GB 内存
3. **追问精度**: 简单规则判断，未来可接入 LLM 提高准确性

### 🔮 未来计划

- [ ] 集成 LLM 生成更智能的追问
- [ ] 支持多轮对话的深度上下文理解
- [ ] 添加对话质量评分
- [ ] 支持动态调整问题库（在线学习）
- [ ] 集成 MCP (Model Context Protocol) 服务器
- [ ] 等待阶跃星辰发布 Embeddings API

### 🙏 致谢

- **ChromaDB**: 提供高性能向量数据库
- **Sentence-Transformers**: 提供优秀的嵌入模型框架
- **BAAI**: 开源 BGE 系列中文嵌入模型
- **阶跃星辰**: 提供优质的实时语音 API

---

## [Previous] - 2025-11-21

### 📦 初始版本

- ✅ V2 版本（指令驱动）
- ✅ Hybrid 版本（TTS + Realtime）
- ✅ 基础问题管理系统
- ✅ 会话记录功能
- ✅ 健康分析报告

---

**版本**: RAG Enhancement v1.0
**日期**: 2025-11-22
**维护者**: Claude Code
