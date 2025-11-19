# 🎯 V2 版本说明 - 指令驱动流程控制

## 核心改进

V2 版本采用**指令驱动**的方式，确保 AI 严格按照预设问题提问。

## 两个版本对比

| 特性 | V1 (`interview_client.py`) | V2 (`interview_client_v2.py`) |
|------|----------------------------|--------------------------------|
| **流程控制** | AI 自由发挥，可能偏离问题 | 指令驱动，严格控制每一步 |
| **问题准确性** | ⚠️ AI 可能改编问题 | ✅ 精确朗读预设问题 |
| **确认机制** | AI 自动确认 | 简化流程，避免重复 |
| **Instructions** | 静态配置 | 每个问题动态更新 |
| **适用场景** | 灵活对话 | 严格的结构化访谈 |

## 工作原理

### V2 的核心策略

```python
# 1. 每个问题更新一次 instructions
instructions = """你是访谈助手。
你的任务：
1. 用自然、友好的语气朗读给你的问题
2. 朗读完后立即停止
3. 不要修改、改编或添加任何内容
"""

# 2. 直接让 AI 朗读问题
prompt = f"请用自然、友好的语气问用户：{question.question}"

# 3. 等待用户回答，记录转写结果
# 4. 自动进入下一个问题
```

### 流程图

```
开始访谈
    ↓
加载问题列表 (questions.yaml)
    ↓
欢迎语
    ↓
┌─────────────────────────────┐
│  问题循环                     │
│                              │
│  1. 更新 instructions        │
│  2. 发送问题文本              │
│  3. AI 朗读问题              │
│  4. 等待用户语音回答          │
│  5. Whisper 转写             │
│  6. 保存回答                 │
│  7. 进入下一题                │
└─────────────────────────────┘
    ↓
结束语
    ↓
保存会话记录
```

## 使用方法

### 运行 V2 版本

```bash
# 使用 V2 版本（推荐用于严格访谈）
uv run python interview_client_v2.py

# 或使用 V1 版本（更灵活的对话）
uv run python interview_client.py
```

### 配置问题

`questions.yaml` 的问题会被**原封不动**地朗读：

```yaml
questions:
  - id: 1
    question: "您好！请问您贵姓？"  # AI 会精确说出这句话
    type: "open"
    
  - id: 2
    question: "请问您对产品满意吗？"  # 一字不差地提问
    type: "yesno"
```

## 关键技术点

### 1. 动态 Instructions 更新

每个问题都会更新 instructions，确保 AI 知道当前任务：

```python
def _update_instructions_for_question(self, question: Question):
    instructions = """你是访谈助手。
    1. 朗读给你的问题
    2. 朗读完后立即停止
    3. 不要修改、改编内容"""
    
    self._send_event({
        "type": "session.update",
        "session": {"instructions": instructions}
    })
```

### 2. 直接问题传递

不在 instructions 中写问题内容，而是作为用户消息传递：

```python
# ✅ V2 方式：问题作为消息内容
prompt = f"请用自然、友好的语气问用户：{question.question}"
self._send_event({
    "type": "conversation.item.create",
    "item": {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": prompt}]
    }
})
```

### 3. 同步控制

使用事件机制确保流程顺序：

```python
# 等待 AI 提问完成
self.ai_finished_speaking.clear()
self.ai_finished_speaking.wait(timeout=10)

# 等待用户回答
self.answer_received.clear()
self.answer_received.wait(timeout=90)
```

## 优势

### ✅ V2 版本的优点

1. **精确性高** - AI 会严格按照问题文本提问
2. **可控性强** - 每一步都在掌控之中
3. **避免偏离** - 不会自由发挥或改编问题
4. **适合正式场景** - 客户满意度调查、正式访谈等

### ⚠️ V2 版本的限制

1. **灵活性较低** - 不能根据回答追问
2. **对话感稍弱** - 流程较为机械
3. **需要精心设计问题** - 问题本身要足够清晰

## 最佳实践

### 问题设计技巧

```yaml
# ✅ 好的问题 - 清晰、完整、口语化
questions:
  - id: 1
    question: "您好！请问您对我们的产品整体满意吗？"
    type: "yesno"

# ❌ 不好的问题 - 含糊、书面语
questions:
  - id: 1
    question: "满意度评价"  # 太简短，AI 可能会扩展
    type: "open"
```

### 参数调优

```python
client = InterviewClientV2(
    API_KEY,
    model=ModelType.STEP_AUDIO_2.value,
    temperature=0.6,  # 降低创造性，更忠实原文
    vad_threshold=0.5,
    vad_silence_duration_ms=700  # 给用户思考时间
)
```

## 故障排查

### 问题：AI 还是改编了问题

**解决方案**：降低 temperature

```python
temperature=0.3  # 更低 = 更忠实原文
```

### 问题：流程卡住

**解决方案**：检查事件同步

```python
# 确保每个 response.create 之前都清理事件
self.ai_finished_speaking.clear()
self._send_event({"type": "response.create"})
self.ai_finished_speaking.wait(timeout=10)
```

### 问题：错误 "ongoing response already exists"

**解决方案**：等待前一个响应完成

```python
# 在创建新响应前检查
if self.is_ai_speaking:
    self.ai_finished_speaking.wait(timeout=5)
    time.sleep(0.5)
```

## 示例输出

```
============================================================
📝 进度: 1/8
💭 问题类型: open
🤖 提问: 您好！我是智能客服助手，今天想了解一下您对我们产品的使用体验。首先请问您贵姓？
============================================================

🔄 已更新指令 [问题 1]
⏳ AI正在提问...
✅ AI提问完成，等待用户回答

🎤 [用户开始回答...] [语音结束]
👤 客户: 我姓张

✅ 已记录回答: 我姓张

============================================================
📝 进度: 2/8
💭 问题类型: open
🤖 提问: 很高兴认识您！请问您使用我们的产品多长时间了？
============================================================
```

## 下一步

- 查看 [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) 了解实际使用案例
- 参考 [questions.yaml](questions.yaml) 设计你的问题
- 阅读 [README.md](README.md) 了解项目全貌

---

**推荐使用场景**：需要严格控制提问内容的正式访谈、调研、评估等场景。

