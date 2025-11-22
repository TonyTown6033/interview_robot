# 🚀 快速开始指南

3分钟上手客户访谈系统！

## 第一步：安装依赖

```bash
cd /Users/town/code4/questionAgent

# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

**macOS 额外依赖：**
```bash
brew install portaudio
```

## 第二步：配置 API Key

```bash
export STEPFUN_API_KEY='sk-your-actual-api-key-here'
```

💡 **提示**：把这行加到 `~/.zshrc` 或 `~/.bash_profile`，下次就不用再设置了。

## 第三步：选择问题模板

### 方式一：使用默认模板
直接使用 `questions.yaml`（通用客户满意度调查）

### 方式二：使用示例模板
```bash
# 产品反馈
cp examples/product_feedback.yaml questions.yaml

# 服务评价
cp examples/service_evaluation.yaml questions.yaml

# 需求调研
cp examples/requirement_survey.yaml questions.yaml
```

### 方式三：自定义问题
编辑 `questions.yaml`：

```yaml
questions:
  - id: 1
    question: "第一个问题？"
    type: "open"
  - id: 2
    question: "第二个问题？"
    type: "open"

settings:
  welcome_message: "欢迎参与访谈！"
  completion_message: "感谢您的参与！"
```

## 第四步：开始访谈

```bash
# 方式一：直接运行
uv run python interview_client.py

# 方式二：使用脚本
./scripts/interview.sh
```

## 访谈流程

1. **启动** - 系统会显示配置信息
2. **欢迎语** - AI 说欢迎语
3. **开始提问** - AI 逐个提问
4. **语音回答** - 对着麦克风说话
5. **自动记录** - 回答会被自动转写和保存
6. **下一个问题** - 自动继续
7. **完成** - 播放结束语，保存记录

## 查看访谈记录

```bash
# 列出所有会话
ls sessions/

# 查看最新的访谈摘要
cat sessions/$(ls -t sessions/ | head -1)/summary.txt

# 查看 JSON 详细数据
cat sessions/$(ls -t sessions/ | head -1)/session.json
```

## 常见问题

### ❌ 连接失败
```bash
# 检查 API Key
echo $STEPFUN_API_KEY

# 应该显示类似：sk-xxx...
# 如果是空的，重新设置
export STEPFUN_API_KEY='your-key'
```

### ❌ 音频设备错误
```bash
# 检查麦克风权限（macOS）
# 系统设置 → 隐私与安全性 → 麦克风
# 确保终端或 Python 有权限
```

### ❌ 问题文件错误
```bash
# 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('questions.yaml'))"

# 如果有错误会显示具体位置
```

## 配置调优

### 提高响应速度
```python
# 编辑 interview_client.py
vad_silence_duration_ms=500  # 改小（默认700）
```

### 提高识别稳定性
```python
# 编辑 interview_client.py
vad_silence_duration_ms=900  # 改大（默认700）
vad_threshold=0.6  # 改大（默认0.5）
```

### 使用更快的模型
```python
# 编辑 interview_client.py
model=ModelType.STEP_AUDIO_2_MINI.value  # 使用 mini 版本
```

## 下一步

- 📖 阅读 [README.md](README.md) 了解详细功能
- 📝 查看 [examples/](examples/) 目录的更多模板
- 🔧 根据场景自定义问题列表

---

**遇到问题？** 查看 [README.md](README.md) 的故障排查章节

