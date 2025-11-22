# 嵌入模型选择指南

## 📚 关于当前使用的模型

### sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

**来源**: HuggingFace Sentence-Transformers 项目
**开发**: UKPLab (德国达姆施塔特工业大学)
**大小**: 约 120MB
**维度**: 384
**语言**: 50+ 语言（包括中文、英文）

#### 优点
- ✅ 免费开源
- ✅ 支持多语言（包括中文）
- ✅ 模型较小，加载快速
- ✅ 社区支持好

#### 缺点
- ❌ 不是专门的中文模型，中文效果一般
- ❌ 需要从 HuggingFace 下载（国内可能较慢）
- ❌ 在中文语义理解上不如专用模型

## 🔍 阶跃星辰 (StepFun) 的 Embeddings 支持

### 调研结果

经过详细调查，**阶跃星辰目前没有提供公开的文本嵌入 (Embeddings) API**。

#### 阶跃星辰提供的 API：
- ✅ **Chat Completions** - 对话生成
- ✅ **Realtime API** - 实时语音交互
- ✅ **TTS/STT** - 语音合成和识别
- ✅ **Image Generation** - 图像生成
- ✅ **Vector Store** - 知识库（但 embeddings 不对外暴露）

#### 为什么没有 Embeddings API？

可能的原因：
1. 阶跃星辰的主营业务是 LLM 对话，不是向量检索
2. Vector Store 功能内部使用 embeddings，但不对外提供 API
3. 尚未发布相关产品（未来可能会有）

## 💡 推荐的中文嵌入模型

由于阶跃星辰没有 embeddings API，推荐使用以下国产开源模型：

### 1. BAAI/bge-small-zh-v1.5 (推荐)

**开发**: 北京智源人工智能研究院 (BAAI)
**大小**: 约 100MB
**维度**: 512
**性能**: ⭐⭐⭐⭐

```python
from src.core.question_rag_optimized import QuestionRAGOptimized, EmbeddingModel

rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.BGE_SMALL_ZH.value
)
```

**优点**:
- ✅ 专为中文优化
- ✅ 模型小，速度快
- ✅ 在中文检索任务上表现优异
- ✅ 国内下载速度快

**适用场景**: 速度优先，资源受限

---

### 2. BAAI/bge-base-zh-v1.5

**开发**: 北京智源人工智能研究院 (BAAI)
**大小**: 约 400MB
**维度**: 768
**性能**: ⭐⭐⭐⭐⭐

```python
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.BGE_BASE_ZH.value
)
```

**优点**:
- ✅ 中文效果最佳
- ✅ 在多个中文 benchmark 上表现领先
- ✅ 适合生产环境

**适用场景**: 效果优先，推荐生产使用

---

### 3. shibing624/text2vec-base-chinese

**开发**: 个人开发者 shibing624
**大小**: 约 400MB
**维度**: 768
**性能**: ⭐⭐⭐⭐⭐

```python
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.TEXT2VEC_BASE_CHINESE.value
)
```

**优点**:
- ✅ 纯中文训练
- ✅ 针对中文文本相似度任务优化
- ✅ 在中文问答检索上表现优异

**适用场景**: 平衡选择，中文语义理解优先

---

### 4. OpenAI Embeddings（需要 API Key）

如果有 OpenAI API key，也可以使用：

```python
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model="text-embedding-3-small",
    use_openai=True,
    openai_api_key="sk-..."
)
```

**优点**:
- ✅ 效果好，支持多语言
- ✅ 无需本地加载模型

**缺点**:
- ❌ 需要付费
- ❌ 需要网络连接
- ❌ 有 API 调用限制

## 🧪 模型对比测试

运行对比测试查看不同模型的性能：

```bash
python compare_embedding_models.py
```

测试结果示例：

| 模型 | 初始化时间 | 检索速度 | 中文效果 | 推荐度 |
|------|----------|---------|---------|-------|
| BGE-Small-ZH | ~5秒 | 0.05秒 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| BGE-Base-ZH | ~8秒 | 0.08秒 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| text2vec-chinese | ~8秒 | 0.08秒 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Multilingual | ~3秒 | 0.04秒 | ⭐⭐⭐ | ⭐⭐⭐ |

## 🔧 如何切换模型

### 方式 1: 修改配置文件

编辑 `src/clients/interview_client_rag.py`:

```python
# 找到这一行
from src.core.question_rag import QuestionRAG

# 改为
from src.core.question_rag_optimized import QuestionRAGOptimized, EmbeddingModel

# 找到初始化部分
self.question_rag = QuestionRAG(question_file)

# 改为
self.question_rag = QuestionRAGOptimized(
    question_file,
    embedding_model=EmbeddingModel.BGE_SMALL_ZH.value  # 使用 BGE Small
)
```

### 方式 2: 使用环境变量（TODO）

未来可以添加环境变量支持：

```bash
export EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"
python run_rag_interview.py
```

## 📊 性能优化建议

### 1. 首次运行慢怎么办？

首次运行会下载模型，可能需要 5-10 分钟：

```bash
# 预下载模型
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
print('模型下载完成')
"
```

### 2. 加速模型下载

如果 HuggingFace 下载慢，可以使用镜像：

```bash
# 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com
python run_rag_interview.py
```

### 3. 减少向量索引时间

- 使用更小的模型（BGE-Small 而不是 BGE-Base）
- 向量数据库会自动缓存，第二次运行会很快

### 4. 提高检索速度

- 使用 ChromaDB 的持久化存储（已默认开启）
- 减少 `n_results` 参数（默认 3）
- 使用更小维度的模型

## 🌟 最佳实践

### 开发阶段

```python
# 使用轻量模型，快速迭代
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.BGE_SMALL_ZH.value
)
```

### 生产环境

```python
# 使用最佳效果模型
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.BGE_BASE_ZH.value
)
```

### 资源受限环境

```python
# 使用最小模型
rag = QuestionRAGOptimized(
    question_file='questions.yaml',
    embedding_model=EmbeddingModel.PARAPHRASE_MULTILINGUAL.value
)
```

## 🔮 未来展望

可能的改进方向：

1. **等待阶跃星辰发布 Embeddings API**
   - 持续关注官方文档更新
   - 一旦发布，可以无缝切换

2. **支持自定义嵌入模型**
   - 允许用户自己微调模型
   - 支持加载本地模型文件

3. **混合检索策略**
   - 结合关键词检索和语义检索
   - 提高检索准确性

4. **动态模型选择**
   - 根据问题类型自动选择模型
   - 平衡效果和速度

## 📞 常见问题

### Q: 为什么不直接用 OpenAI？

A:
- 成本考虑（OpenAI embeddings 按 token 计费）
- 隐私考虑（本地模型不发送数据到外部）
- 稳定性考虑（本地模型不依赖网络）

### Q: BGE 和 text2vec 哪个更好？

A:
- **BGE-Base-ZH**: 在大多数中文任务上表现更好
- **text2vec**: 在特定场景可能更适合
- 建议运行对比测试，选择适合你数据的模型

### Q: 模型存储在哪里？

A:
- 默认: `~/.cache/huggingface/hub/`
- 向量数据库: `./chroma_db/`

### Q: 如何清理缓存？

```bash
# 清理模型缓存
rm -rf ~/.cache/huggingface/hub/

# 清理向量数据库
rm -rf ./chroma_db/
```

## 📚 参考资源

- [Sentence-Transformers 文档](https://www.sbert.net/)
- [BGE 模型页面](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- [text2vec 项目](https://github.com/shibing624/text2vec)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [阶跃星辰官方文档](https://platform.stepfun.com/docs)

---

**最后更新**: 2025-11-22
**版本**: 1.0
