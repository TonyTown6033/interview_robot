# 更新日志

## [Logging Enhancement v1.1.0] - 2025-11-22 深夜

### 🎯 日志系统改进

#### 1. Print → Logger 迁移
**改进**: 将所有 print 语句替换为专业的 logging 系统

**变更**:
- ✅ 替换 120+ 处 print 语句为 logger 调用
- ✅ 修复 12 处 f-string 格式问题
- ✅ 实现分级日志（INFO/WARNING/ERROR/DEBUG）
- ✅ 控制台显示简洁信息（INFO+）
- ✅ 文件记录详细调试（DEBUG+）
- ✅ 自动创建带时间戳的日志文件：`logs/interview_YYYYMMDD_HHMMSS.log`

**影响文件**: `src/clients/interview_client_rag.py`

#### 2. 转录验证增强（修复"未回答就跳过"问题）
**问题**: 用户反馈"有时候我还没回答问题就到了下一个问题"

**根本原因**:
1. 未验证转录文本有效性
2. 接受过短的转录（VAD 误触发）
3. 缺少调试信息追踪问题

**修复**:
- ✅ 添加转录文本 `.strip()` 处理
- ✅ **最小长度验证**：拒绝少于 2 字符的转录（关键修复！）
- ✅ 空转录检测和拒绝
- ✅ 状态检查日志（`waiting_for_answer` 状态）
- ✅ 详细的调试日志追踪转录接收流程
- ✅ 改进警告信息，明确说明被忽略的原因

**位置**: `src/clients/interview_client_rag.py:800-823`

#### 3. 调试日志增强

新增 10+ 处关键调试日志：

**问答流程**:
```python
logger.debug(f"🔧 初始化问题状态: waiting_for_answer=True")
logger.debug(f"⏳ 开始等待用户回答（超时：{timeout}秒）...")
logger.debug(f"📨 收到 answer_received 事件，当前转录: '{self.current_transcript}'")
logger.debug(f"🔧 重置状态: waiting_for_answer=False")
```

**转录处理**:
```python
logger.debug(f"📝 收到转录: '{transcript}' (长度: {len(transcript)} 字符)")
logger.debug(f"   当前状态 - waiting_for_answer: {self.waiting_for_answer}")
logger.debug(f"✅ 设置 answer_received 事件")
logger.debug(f"⏭️  当前不在等待回答状态，忽略转录: '{transcript}'")
```

**位置**: `src/clients/interview_client_rag.py` 多处

### 📄 新增文档

- `LOGGING_AND_DEBUGGING_IMPROVEMENTS.md` - 详细的日志改进文档

### 📊 改进效果

| 方面 | 改进前 | 改进后 |
|------|--------|--------|
| 日志系统 | print 语句混乱 | ✅ 分级专业日志 |
| 调试能力 | 无调试信息 | ✅ 详细 DEBUG 日志 |
| 转录验证 | 接受所有转录 | ✅ 严格验证（长度、非空） |
| 问题诊断 | 难以追踪 | ✅ 完整状态跟踪 |
| 日志持久化 | 无 | ✅ 自动保存到文件 |
| 误触发防护 | 无 | ✅ 拒绝过短转录 |

### 🔍 日志级别说明

- **INFO** (控制台 + 文件): 用户可见的重要信息、进度、状态
- **WARNING** (控制台 + 文件): 潜在问题、被拒绝的操作
- **ERROR** (控制台 + 文件): 错误情况、失败的操作
- **DEBUG** (仅文件): 详细的内部状态、变量值、事件追踪

### 🚀 使用示例

#### 查看实时日志
```bash
python run_rag_interview.py
```

#### 查看详细调试日志
```bash
tail -f logs/interview_20251122_*.log
```

#### 过滤特定问题
```bash
# 查找所有被拒绝的转录
grep "忽略" logs/interview_*.log

# 查找所有警告
grep "WARNING" logs/interview_*.log
```

### 🐛 Bug 修复验证

#### 测试场景：短转录拦截

**预期行为**:
```
# 日志文件中
17:27:45 - RAGInterview - DEBUG - 📝 收到转录: '嗯' (长度: 1 字符)
17:27:45 - RAGInterview - WARNING - ⚠️  转录文本过短 (1 字符)，可能是误触发，忽略: '嗯'
```

✅ 短转录被正确拦截，不会触发 `answer_received`

---

## [Bug Fix v1.0.1] - 2025-11-22 晚

### 🐛 Bug 修复

#### 1. 追问计数混淆问题
**问题**: 用户反馈"追问会计数到问题里"，虽然代码逻辑正确，但显示不够清晰

**修复**:
- ✅ 改进追问提示信息，明确标注"属于当前问题的一部分"
- ✅ 完善统计报告，区分"主问题数"和"追问次数"
- ✅ 添加说明文字，解释主问题和追问的区别

**影响文件**: `src/clients/interview_client_rag.py`

#### 2. 连接不稳定问题
**问题**: 连接不稳定时容易崩溃，一次错误就终止程序

**修复**:
- ✅ 发送循环添加错误重试机制（最多 5 次）
- ✅ 接收循环添加心跳检测（30 秒超时提示）
- ✅ 改进错误处理，区分不同类型错误
- ✅ WebSocket 关闭后尝试恢复
- ✅ JSON 解析错误不中断程序
- ✅ 特殊处理"ongoing response"错误

**影响文件**: `src/clients/interview_client_rag.py`

### 📄 新增文档

- `BUGFIX_FOLLOWUP_CONNECTION.md` - 详细的 Bug 修复文档

### 📊 改进效果

| 方面 | 改进前 | 改进后 |
|------|--------|--------|
| 追问显示 | 不明确 | ✅ 清晰标注 |
| 统计报告 | 可能混淆 | ✅ 明确区分 |
| 连接稳定性 | 一次错误就崩溃 | ✅ 自动重试 3-5 次 |
| 心跳检测 | 无 | ✅ 30 秒超时提示 |
| 错误提示 | 不友好 | ✅ 详细的错误类型和建议 |

---

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
