# 🎯 混合模式使用指南

## 概述

**混合模式**结合了两种技术的优势：
- **TTS（文本转语音）**：生成问题音频，**100% 忠实原文** ✅
- **Realtime API**：接收和转写用户回答

这是目前**最可靠的解决方案**，确保 AI 严格按照 `questions.yaml` 中的问题提问。

## 工作原理

```
┌─────────────────┐
│ questions.yaml  │
└────────┬────────┘
         │
         ▼
   ┌─────────┐
   │ TTS API │ ← 生成问题语音（100% 准确）
   └────┬────┘
        │
        ▼
   ┌──────────┐
   │ 播放音频  │ → 👤 用户听到问题
   └──────────┘
        │
        ▼
   ┌──────────┐
   │ 用户回答  │ → 🎤 麦克风录制
   └────┬─────┘
        │
        ▼
┌──────────────┐
│ Realtime API │ ← 转写语音为文本
└──────┬───────┘
       │
       ▼
  ┌─────────┐
  │ 保存记录 │
  └─────────┘
```

## 快速开始

### 1. 安装依赖

```bash
cd /Users/town/code4/questionAgent

# 安装新增的依赖
uv sync
```

新增依赖：
- `requests` - 调用 TTS API
- `scipy` - 音频重采样

### 2. 配置 API Key

```bash
export STEPFUN_API_KEY='your-api-key'
```

### 3. 准备问题

编辑 `questions.yaml`：

```yaml
questions:
  - id: 1
    question: "您好！请问您贵姓？"
    type: "open"
    
  - id: 2
    question: "请问您对产品满意吗？"
    type: "yesno"
```

### 4. 运行混合模式

```bash
uv run python interview_client_hybrid.py
```

## 首次运行流程

```
🚀 客户访谈系统 - 混合模式
============================================================
🎵 音频设备初始化成功
🔌 正在连接到 Realtime API...
✅ WebSocket 连接成功！
⚙️  会话配置完成（仅语音识别模式）

📊 访谈配置:
   模型: step-audio-2
   问题总数: 8
   会话ID: 20241119_143052
   问题语音: TTS 生成（100% 准确）
   回答识别: Realtime API

============================================================

🎙️  正在预生成问题语音...
🎙️  正在生成语音: 您好！感谢您参与我们的产品体验调研...
✅ 语音生成成功: question_0.mp3
🎙️  正在生成语音: 您好！我是产品体验调研助手。首先请问...
✅ 语音生成成功: question_1.mp3
...
✅ 所有语音文件已准备就绪

🤖 欢迎: 您好！感谢您参与...
🔊 播放欢迎语...
```

## 功能特点

### ✅ 优势

1. **100% 准确** - TTS 完全按照原文生成语音
2. **高质量音频** - 专业的语音合成
3. **多种声音** - 支持多个语音选项
4. **缓存机制** - 第二次运行无需重新生成
5. **可靠稳定** - 不依赖 AI "理解"问题

### 📊 对比表

| 特性 | V1 版本 | V2 版本 | 混合模式 |
|------|---------|---------|----------|
| **问题准确性** | ❌ 可能改编 | ⚠️ 有时改编 | ✅ 100% 准确 |
| **实现复杂度** | 简单 | 中等 | 中等 |
| **网络依赖** | 仅 Realtime | 仅 Realtime | Realtime + TTS |
| **首次运行** | 快速 | 快速 | 需要生成音频 |
| **后续运行** | 快速 | 快速 | 快速（使用缓存）|
| **适用场景** | 灵活对话 | 结构化访谈 | **正式访谈** ⭐ |

## 配置选项

### 选择 TTS 声音

编辑 `interview_client_hybrid.py` 第 645 行：

```python
client = HybridInterviewClient(
    API_KEY,
    tts_voice="female-tianmei"  # 修改这里
)
```

可用声音选项：
- `female-tianmei` - 女声（甜美）⭐ 推荐
- `female-shuangkuai` - 女声（爽快）
- `male-botong` - 男声（播通）
- `male-qingse` - 男声（青涩）

### VAD 参数

```python
client = HybridInterviewClient(
    API_KEY,
    vad_threshold=0.5,              # 语音检测灵敏度
    vad_silence_duration_ms=700     # 静音持续时长
)
```

## 缓存管理

### 缓存目录结构

```
tts_cache/
├── question_0.mp3      # 欢迎语
├── question_1.mp3      # 问题 1
├── question_2.mp3      # 问题 2
├── ...
└── question_9999.mp3   # 结束语
```

### 清空缓存

如果修改了问题文本，需要清空缓存：

```bash
# 方法 1：手动删除
rm -rf tts_cache/

# 方法 2：Python 脚本
python -c "from interview_client_hybrid import TTSGenerator; TTSGenerator('').clear_cache()"
```

### 缓存优势

- **第一次运行**：生成所有音频（约 5-10 秒）
- **后续运行**：直接使用缓存（秒级启动）
- **修改问题**：只需重新生成改动的问题

## 使用场景

### ✅ 推荐使用混合模式

1. **正式客户访谈** - 问题措辞需要精确
2. **满意度调查** - 标准化问题
3. **法律合规场景** - 必须一字不差
4. **多语言访谈** - 确保翻译准确
5. **质量要求高** - 不容许偏差

### ⚠️ 可以使用 V1/V2

1. **非正式交流** - 灵活对话
2. **快速原型** - 测试阶段
3. **追问场景** - 需要根据回答调整

## 故障排查

### 问题：TTS 生成失败

**错误信息**：`❌ TTS 错误: 401`

**解决方案**：
```bash
# 检查 API Key
echo $STEPFUN_API_KEY

# 重新设置
export STEPFUN_API_KEY='your-valid-key'
```

### 问题：音频播放失败

**错误信息**：`❌ 播放错误: No module named 'soundfile'`

**解决方案**：
```bash
# 重新安装依赖
uv sync

# 或手动安装
pip install soundfile scipy
```

### 问题：音频质量差

**解决方案**：尝试不同的声音

```python
tts_voice="male-botong"  # 换一个声音
```

### 问题：缓存占用空间

每个音频约 50-200KB，8 个问题约 0.5-2MB。

如果需要清理：
```bash
rm -rf tts_cache/
```

## 高级用法

### 自定义 TTS 参数

目前 TTS API 支持的参数：

```python
data = {
    "model": "step-1-flash",
    "input": text,
    "voice": "female-tianmei",
    "response_format": "mp3",  # 或 "wav", "opus"
    "speed": 1.0,              # 语速 (0.5-2.0)
}
```

修改 `interview_client_hybrid.py` 的 `TTSGenerator.generate_speech` 方法添加参数。

### 批量预生成

如果有多个问题列表：

```bash
# 生成多个问题集的音频
for file in questions_*.yaml; do
    python -c "
from interview_client_hybrid import HybridInterviewClient
client = HybridInterviewClient('$STEPFUN_API_KEY', '$file')
client.question_manager.load_questions()
client._pregenerate_tts()
"
done
```

## 性能对比

### 首次运行

| 步骤 | V2 版本 | 混合模式 |
|------|---------|----------|
| 启动 | < 1s | < 1s |
| TTS 生成 | - | 5-10s |
| 总计 | < 1s | 5-10s |

### 后续运行

| 步骤 | V2 版本 | 混合模式 |
|------|---------|----------|
| 启动 | < 1s | < 1s |
| TTS 生成 | - | 0s（缓存）|
| 总计 | < 1s | < 1s |

## 示例输出

```
============================================================
📝 进度: 1/8
💭 问题类型: open
🎯 问题: 您好！我是产品体验调研助手。首先请问，我可以怎么称呼您？
============================================================

🔊 播放问题...
✅ 问题播放完成，等待用户回答

🎤 [用户开始回答...] [语音结束]
👤 客户: 我姓张

✅ 已记录回答: 我姓张

============================================================
📝 进度: 2/8
💭 问题类型: open
🎯 问题: 感谢参与我们的调研！请问您使用我们的产品多长时间了？
============================================================
```

## 最佳实践

1. **首次运行预留时间** - 生成音频需要 5-10 秒
2. **检查音频质量** - 首次运行后听一遍确认
3. **定期清理缓存** - 修改问题后记得删除缓存
4. **网络稳定** - TTS 生成需要网络连接
5. **音量适中** - 调整系统音量确保客户能听清

## 与其他版本切换

```bash
# V1 版本（灵活对话）
uv run python interview_client.py

# V2 版本（指令驱动）
uv run python interview_client_v2.py

# 混合模式（TTS + Realtime）⭐ 推荐
uv run python interview_client_hybrid.py
```

## 总结

**混合模式**是最可靠的解决方案：
- ✅ 100% 准确提问
- ✅ 高质量音频
- ✅ 缓存机制提高效率
- ✅ 适合正式场景

**推荐用于所有需要精确提问的场景！**

---

需要帮助？查看 [DEBUG_GUIDE.md](DEBUG_GUIDE.md)

