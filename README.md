# 🎤 客户访谈系统（Question Agent）

基于阶跃星辰 Realtime API 的智能语音访谈系统，用于向客户提问并自动记录回答。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 功能特性

- 🎯 **结构化访谈** - 按预设问题列表逐个提问
- 🎤 **实时语音交互** - 自然的语音问答体验
- 📝 **自动记录** - 语音转写 + 文本记录
- 🤖 **AI健康分析** - 自动生成健康分析报告
- 💾 **会话保存** - JSON + 文本双格式保存
- 📊 **进度跟踪** - 实时显示访谈进度
- ⚙️ **灵活配置** - YAML 配置文件管理问题
- 🎵 **TTS生成** - 100%准确的问题语音生成

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

额外依赖（音频处理需要）：
```bash
# macOS
brew install libsndfile portaudio

# Ubuntu/Debian
sudo apt-get install libsndfile1 portaudio19-dev
```

### 2. 配置 API Key

```bash
export STEPFUN_API_KEY='your-api-key-here'
```

### 3. 配置问题列表

编辑 `questions.yaml` 文件，自定义您的问题：

```yaml
questions:
  - id: 1
    question: "您好！请问您贵姓？"
    type: "open"

  - id: 2
    question: "您对产品的整体满意度如何？"
    type: "open"

settings:
  welcome_message: "您好！欢迎参与本次访谈。"
  completion_message: "感谢您的参与！访谈已完成。"
```

### 4. 开始访谈

```bash
# 方式1：直接运行主程序
python main.py

# 方式2：使用 uv
uv run python main.py

# 方式3：使用启动脚本
./scripts/interview_hybrid.sh
```

## 📁 项目结构

```
questionAgent/
├── main.py                   # 主入口程序
├── questions.yaml            # 问题配置文件
├── README.md                 # 本文档
├── pyproject.toml            # 项目配置
│
├── src/                      # 源代码目录
│   ├── core/                 # 核心模块
│   │   └── question_manager.py   # 问题管理和会话记录
│   ├── clients/              # 客户端实现
│   │   ├── interview_client.py         # 原始版本
│   │   ├── interview_client_v2.py      # V2版本（指令驱动）
│   │   └── interview_client_hybrid.py  # 混合模式（推荐）
│   ├── analyzers/            # 分析器
│   │   ├── health_analyzer_client.py   # 健康分析客户端
│   │   └── health_analyzer_mcp.py      # MCP健康分析
│   └── utils/                # 工具模块
│
├── sessions/                 # 访谈记录目录（自动创建）
│   └── 20241119_211758/      # 会话文件夹（按时间命名）
│       ├── session.json           # 详细记录（JSON格式）
│       ├── summary.txt            # 文本摘要
│       ├── health_analysis.json   # AI分析结果
│       └── health_report.txt      # 健康报告
│
├── tts_cache/                # TTS音频缓存目录
├── scripts/                  # 启动脚本
│   ├── interview.sh          # 启动脚本
│   └── interview_hybrid.sh   # 混合模式启动脚本
│
├── docs/                     # 文档目录
│   ├── QUICKSTART.md              # 快速开始指南
│   ├── HEALTH_ANALYSIS.md         # 健康分析文档
│   ├── README_V2.md               # V2版本说明
│   └── README_HYBRID.md           # 混合模式说明
│
├── tests/                    # 测试目录
│   └── test_health_analysis.py    # 健康分析测试
│
└── examples/                 # 示例配置
    ├── product_feedback.yaml      # 产品反馈模板
    ├── service_evaluation.yaml    # 服务评价模板
    └── requirement_survey.yaml    # 需求调研模板
```

## 📝 使用说明

### 访谈流程

1. **启动系统** - 系统连接到 API 并加载问题
2. **欢迎语** - TTS播放欢迎语
3. **逐个提问** - 按配置顺序提问（TTS生成，100%准确）
4. **等待回答** - 用户对着麦克风回答
5. **自动记录** - 语音转写并保存
6. **继续下一题** - 自动进入下一个问题
7. **完成访谈** - 播放结束语并保存记录
8. **生成报告** - 自动生成AI健康分析报告

### 技术方案

**混合模式（推荐）：**
- **问题播放**：使用 TTS API 生成音频，确保100%忠实原文
- **回答识别**：使用 Realtime API 进行语音识别
- **优势**：问题播放准确，回答识别灵活

### 问题配置格式

`questions.yaml` 配置说明：

```yaml
# 问题列表
questions:
  - id: 1                     # 问题编号（必需）
    question: "问题内容"      # 问题文本（必需）
    type: "open"              # 问题类型（可选）

# 类型选项：
# - open: 开放式问题
# - yesno: 是非题
# - choice: 选择题

# 全局配置
settings:
  welcome_message: "欢迎语内容"
  completion_message: "结束语内容"
```

### 会话记录格式

**JSON 格式** (`session.json`)：
```json
{
  "session_id": "20241119_211758",
  "start_time": "2024-11-19T21:17:58",
  "end_time": "2024-11-19T21:25:15",
  "duration_seconds": 437,
  "total_questions": 8,
  "answers": [
    {
      "question_id": 1,
      "question_text": "请问您贵姓？",
      "transcript": "我姓张",
      "timestamp": "2024-11-19T21:18:05"
    }
  ]
}
```

**健康分析报告** (`health_report.txt`)：
- 症状分析
- 健康评估
- 建议措施
- 就医建议

## ⚙️ 配置参数

### 模型选择

```python
class ModelType(Enum):
    STEP_AUDIO_2 = "step-audio-2"          # 标准版（推荐）
    STEP_AUDIO_2_MINI = "step-audio-2-mini"  # 轻量版
```

### VAD 参数调整

```python
client = HybridInterviewClient(
    API_KEY,
    vad_threshold=0.7,              # 语音检测阈值（0.3-0.9）
    vad_silence_duration_ms=800     # 静音持续时长（推荐700-1000）
)
```

**参数说明：**
- `vad_threshold`: 0.6-0.8推荐，避免误触发
- `vad_silence_duration_ms`: 越长越稳定，但响应会慢一点

### TTS 配置

```python
client = HybridInterviewClient(
    API_KEY,
    tts_voice="cixingnansheng",     # 音色选择
    tts_model="step-tts-mini"       # TTS模型
)
```

**支持的音色：**
- 磁性男声: `cixingnansheng`
- 温柔男声: `wenrounansheng`
- 甜美女声: `tianmeinvsheng`
- 温柔女声: `wenrounvsheng`

## 🎯 使用场景

### 1. 健康问诊
参见 `questions.yaml` - 收集症状、病史等信息

### 2. 客户满意度调查
参见 `examples/service_evaluation.yaml`

### 3. 产品反馈收集
参见 `examples/product_feedback.yaml`

### 4. 需求调研
参见 `examples/requirement_survey.yaml`

## 🛠️ 高级功能

### 查看访谈记录

```bash
# 查看所有会话
ls sessions/

# 查看特定会话的文本摘要
cat sessions/20241119_211758/summary.txt

# 查看健康分析报告
cat sessions/20241119_211758/health_report.txt

# 查看 JSON 详细记录
cat sessions/20241119_211758/session.json | python -m json.tool
```

### 清空TTS缓存

```bash
rm -rf tts_cache/*.mp3
```

## ⚠️ 注意事项

1. **网络要求** - 需要稳定的网络连接
2. **音频设备** - 确保麦克风和扬声器正常工作
3. **环境安静** - 建议在安静环境下进行访谈
4. **问题数量** - 建议不超过 15 个问题（约 10-15 分钟）
5. **回答超时** - 每个问题默认 90 秒超时
6. **提前结束** - 可以用 `Ctrl+C` 提前结束访谈

## 🔧 故障排查

### 问题：连接失败
```bash
# 检查 API Key
echo $STEPFUN_API_KEY

# 检查网络
ping api.stepfun.com
```

### 问题：音频设备错误
```bash
# 测试音频设备
python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_default_input_device_info())"
```

### 问题：问题文件加载失败
```bash
# 验证 YAML 格式
python -c "import yaml; yaml.safe_load(open('questions.yaml'))"
```

### 问题：导入错误
```bash
# 确保在项目根目录运行
cd /Users/town/code4/questionAgent
python main.py
```

## 📚 技术架构

### 核心组件

1. **QuestionManager** (`src/core/question_manager.py`)
   - 加载 YAML 配置
   - 管理问题队列
   - 跟踪进度

2. **SessionRecorder** (`src/core/question_manager.py`)
   - 记录问答对
   - 保存 JSON 和文本格式
   - 生成摘要

3. **HybridInterviewClient** (`src/clients/interview_client_hybrid.py`)
   - WebSocket 通信
   - TTS音频生成
   - 音频录制/播放
   - 事件处理

4. **HealthAnalyzerClient** (`src/analyzers/health_analyzer_client.py`)
   - AI健康分析
   - 报告生成
   - 建议输出

### 数据流

```
问题配置(YAML) → QuestionManager → HybridInterviewClient
                                        ↓
                              TTS API → 问题语音播放
                                        ↓
                              实时语音对话（WebSocket）
                                        ↓
                              语音转写 ← Whisper
                                        ↓
                              SessionRecorder → 保存记录
                                        ↓
                              HealthAnalyzerClient → 生成健康报告
```

## 📄 许可证

MIT License

## 🙏 致谢

基于阶跃星辰 Realtime API 开发

---

**快速开始**: `python main.py`

**文档**: 详见 `docs/` 目录

**问题反馈**: 请提交 Issue
