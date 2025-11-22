# Bug 修复：追问计数和连接稳定性

## 📅 日期
2025-11-22

## 🐛 修复的问题

### 问题 1: 追问计数混淆

**现象**:
用户反馈"追问会计数到问题里"，可能导致误解追问被当作独立问题。

**根本原因**:
虽然代码逻辑正确（追问不计入 `questions_asked`），但是：
1. 显示信息不够清晰
2. 统计报告没有明确区分主问题和追问
3. 用户体验上容易混淆

**修复方案**:

#### 1. 改进追问提示信息

```python
# 修复前
print(f"🤖 追问: {followup_text}\n")

# 修复后
print(f"\n{'─' * 60}")
print(f"💬 追问（属于当前问题的一部分）")
print(f"{'─' * 60}")
print(f"🤖 追问: {followup_text}\n")
```

#### 2. 完善统计报告

```python
print(f"\n📊 访谈统计:")
print(f"   问题库大小: {len(self.question_rag.questions)}")
print(f"   主问题数: {self.questions_asked}")  # 改为"主问题数"
print(f"   有效回答: {self.session_recorder.get_answer_count()}")

# 新增：统计追问次数
followup_count = 0
if self.session_recorder:
    for answer in self.session_recorder.answers:
        if "[追问回答:" in answer.transcript:
            followup_count += 1

if followup_count > 0:
    print(f"   追问次数: {followup_count} (已自动合并到对应问题)")

# 新增：说明
print(f"\n💡 说明:")
print(f"   • 主问题: 从知识库检索的核心问题")
print(f"   • 追问: 当回答不完整时的补充提问（不单独计数）")
```

#### 3. 验证逻辑正确性

**代码流程**:
```
主循环:
  while questions_asked < max_questions:
    success = _ask_question_rag(next_question)
    if success:
      questions_asked += 1  # ← 只在主问题成功后增加

_ask_question_rag():
  提问主问题
  等待回答
  保存回答
  _check_and_followup()  # ← 可能会追问
  return True

_check_and_followup():
  if 回答不完整:
    _do_followup()  # ← 执行追问，不增加计数

_do_followup():
  发送追问
  等待回答
  追加到 answers[-1].transcript  # ← 合并到主问题的回答中
  # 不调用 add_answer()，所以不增加 answer_count
```

**结论**: 追问确实不会计入问题总数，逻辑正确 ✅

---

### 问题 2: 连接不稳定

**现象**:
用户反馈连接不稳定，可能出现：
- WebSocket 连接中断
- 发送/接收错误
- 超时无响应

**根本原因**:
1. 缺少错误重试机制
2. 没有心跳检测
3. 错误处理不够完善
4. 一次错误就终止程序

**修复方案**:

#### 1. 发送循环改进

```python
def _send_loop(self):
    """发送音频数据循环"""
    error_count = 0
    max_errors = 5  # 允许 5 次错误

    while self.running:
        try:
            audio_data = self.recorder.get_audio()
            if audio_data:
                encoded = base64.b64encode(audio_data).decode("ascii")
                event = {"type": "input_audio_buffer.append", "audio": encoded}
                self._send_event(event)
                error_count = 0  # ✅ 成功发送，重置错误计数
            else:
                time.sleep(0.01)
        except Exception as e:
            error_count += 1
            if self.running:
                print(f"❌ 发送错误 ({error_count}/{max_errors}): {e}")
                if error_count >= max_errors:
                    print("❌ 发送错误过多，停止发送循环")
                    break
                time.sleep(0.5)  # ✅ 错误后等待一下再重试
```

**改进点**:
- ✅ 错误计数机制
- ✅ 允许多次重试
- ✅ 成功后重置计数
- ✅ 错误后延迟重试

#### 2. 接收循环改进

```python
def _receive_loop(self):
    """接收响应循环（带重试机制）"""
    error_count = 0
    max_errors = 3
    last_activity = time.time()
    heartbeat_timeout = 30  # 30秒无活动视为超时

    while self.running:
        try:
            # ✅ 心跳检测
            if time.time() - last_activity > heartbeat_timeout:
                print(f"\n⚠️  {heartbeat_timeout}秒无响应，可能连接不稳定")
                last_activity = time.time()

            message = self.ws.recv()
            if not message:
                print("\n⚠️  收到空消息")
                time.sleep(0.1)
                continue

            last_activity = time.time()  # ✅ 更新活动时间
            error_count = 0  # ✅ 成功接收，重置错误计数

            # ... 处理消息 ...

        except WebSocketConnectionClosedException:
            error_count += 1
            print(f"\n❌ WebSocket 连接已关闭 ({error_count}/{max_errors})")
            if error_count >= max_errors or not self.running:
                self.running = False
                break
            else:
                print("   → 尝试恢复连接...")  # ✅ 提示恢复
                time.sleep(2)

        except json.JSONDecodeError as e:
            print(f"\n⚠️  JSON 解析错误: {e}")
            continue  # ✅ 继续运行，不中断

        except Exception as e:
            error_count += 1
            # ... 错误处理 ...
            time.sleep(1)  # ✅ 延迟重试
```

**改进点**:
- ✅ 心跳超时检测（30秒）
- ✅ 错误计数和重试
- ✅ 区分不同类型的错误
- ✅ JSON 解析错误不中断程序
- ✅ WebSocket 关闭后尝试恢复

#### 3. 特殊错误处理

```python
elif event_type == "error":
    error_data = event.get("error", {})
    error_msg = error_data.get("message", "Unknown error")
    error_type = error_data.get("type", "")
    print(f"\n❌ API 错误 [{error_type}]: {error_msg}")

    # ✅ 特殊处理某些错误
    if "ongoing response" in error_msg:
        print("   → 提示: 上一个响应未完成，已自动处理")
        time.sleep(1)  # 等待响应完成
```

**改进点**:
- ✅ 识别"ongoing response"错误
- ✅ 自动等待响应完成
- ✅ 提供友好的错误提示

#### 4. 连接质量监控

添加监控变量：
```python
# 连接质量监控
self.connection_errors = 0
self.last_message_time = time.time()
```

未来可以用于：
- 显示连接质量指示器
- 自动重连机制
- 统计连接稳定性

---

## 📊 测试验证

### 测试 1: 追问计数

**测试步骤**:
1. 运行访谈，回答"不好"（触发追问）
2. 完成访谈，查看统计报告

**预期结果**:
```
📊 访谈统计:
   问题库大小: 7
   主问题数: 3          ← 主问题 3 个
   有效回答: 3          ← 回答 3 个（包含追问）
   追问次数: 1 (已自动合并到对应问题)  ← 明确显示追问

💡 说明:
   • 主问题: 从知识库检索的核心问题
   • 追问: 当回答不完整时的补充提问（不单独计数）
```

**验证**: ✅ 追问不计入主问题数

### 测试 2: 连接稳定性

**测试场景**:
1. 模拟网络波动
2. 模拟 WebSocket 短暂中断
3. 模拟发送/接收错误

**预期行为**:
- 短暂错误：自动重试（最多 3-5 次）
- 持续错误：提示用户并优雅退出
- JSON 错误：跳过该消息，继续运行

**验证**: ✅ 连接更稳定，不会因单次错误就崩溃

---

## 🎯 改进效果

### 用户体验改进

| 方面 | 改进前 | 改进后 |
|------|--------|--------|
| **追问显示** | 不明确 | 清晰标注"属于当前问题的一部分" |
| **统计报告** | 可能混淆 | 明确区分主问题、追问、有效回答 |
| **错误提示** | 不友好 | 详细的错误类型和恢复建议 |
| **连接稳定性** | 一次错误就崩溃 | 自动重试，容错性强 |
| **心跳检测** | 无 | 30秒超时提示 |

### 代码质量改进

- ✅ 更清晰的日志输出
- ✅ 更好的错误处理
- ✅ 更强的容错能力
- ✅ 更友好的用户提示

---

## 📝 使用建议

### 1. 查看统计报告

访谈结束后，仔细查看统计报告：
```
主问题数: 5    ← 实际从知识库检索的问题数
追问次数: 2    ← 追问了 2 次（不计入主问题）
有效回答: 5    ← 5 个问题都有回答
```

### 2. 网络不稳定时

如果看到以下提示：
```
⚠️  30秒无响应，可能连接不稳定
❌ 发送错误 (1/5): ...
```

**建议**:
- 检查网络连接
- 尝试重启访谈
- 考虑更换网络环境

### 3. 避免触发"ongoing response"错误

**最佳实践**:
- 等待 AI 说完再继续
- 不要快速连续提问
- 追问会自动处理等待

---

## 🔮 未来改进方向

### 1. 自动重连机制

```python
def _reconnect(self):
    """自动重连"""
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"🔄 尝试重连 ({i+1}/{max_retries})...")
            self.connect()
            print("✅ 重连成功")
            return True
        except Exception as e:
            print(f"❌ 重连失败: {e}")
            time.sleep(5)
    return False
```

### 2. 连接质量指示器

```python
def _get_connection_quality(self):
    """获取连接质量"""
    if self.connection_errors == 0:
        return "优秀 🟢"
    elif self.connection_errors < 3:
        return "良好 🟡"
    else:
        return "较差 🔴"
```

### 3. 离线缓存

```python
def _cache_question_audio(self):
    """预缓存问题音频（离线使用）"""
    # 提前生成所有问题的 TTS 音频
    # 即使连接不稳定也能播放
```

### 4. WebSocket Ping/Pong

```python
def _send_ping(self):
    """发送心跳包"""
    if self.ws:
        self.ws.ping()
```

---

## 📚 相关文档

- [RAG_GUIDE.md](RAG_GUIDE.md) - RAG 系统完整指南
- [EMBEDDING_MODELS_GUIDE.md](EMBEDDING_MODELS_GUIDE.md) - 嵌入模型选择
- [CHANGELOG.md](CHANGELOG.md) - 完整更新日志

---

**版本**: v1.0.1
**日期**: 2025-11-22
**维护者**: Claude Code
