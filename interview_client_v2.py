"""
客户访谈客户端 V2 - 指令驱动版本
采用动态更新 instructions 的方式，实现精确的流程控制
"""

import base64
import json
import os
import threading
import queue
import time
from websocket import create_connection, WebSocketConnectionClosedException
import pyaudio
from typing import Optional, Dict, Any
from enum import Enum

from question_manager import QuestionManager, SessionRecorder, Question

# 配置信息
API_KEY = os.getenv("STEPFUN_API_KEY", "your-api-key-here")
WS_URL = "wss://api.stepfun.com/v1/realtime"

# 支持的模型
class ModelType(Enum):
    STEP_AUDIO_2 = "step-audio-2"
    STEP_AUDIO_2_MINI = "step-audio-2-mini"
    STEP_AUDIO_2_THINK = "step-audio-2-think"
    STEP_AUDIO_2_MINI_THINK = "step-audio-2-mini-think"

# 音频配置
SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 480
FORMAT = pyaudio.paInt16


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class AudioPlayer:
    """实时音频播放器"""
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.playing = False
        self.audio_queue = queue.Queue(maxsize=100)
        self.play_thread = None
        self._lock = threading.Lock()
        
    def start(self):
        with self._lock:
            if self.playing:
                return
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE
            )
            self.playing = True
            self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
            self.play_thread.start()
        
    def _play_loop(self):
        while self.playing:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                if audio_data is not None and self.playing:
                    self.stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                if self.playing:
                    print(f"❌ 播放错误: {e}")
                
    def add_audio(self, pcm_bytes: bytes):
        try:
            if self.audio_queue.full():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    pass
            self.audio_queue.put_nowait(pcm_bytes)
        except queue.Full:
            pass
        
    def clear(self):
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
    def stop(self):
        with self._lock:
            self.playing = False
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        self.audio.terminate()


class AudioRecorder:
    """实时音频录制器"""
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.record_thread = None
        self.audio_queue = queue.Queue()
        self._lock = threading.Lock()
        
    def start(self):
        with self._lock:
            if self.recording:
                return
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            self.recording = True
            self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.record_thread.start()
        
    def _record_loop(self):
        while self.recording:
            try:
                audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_queue.put(audio_data)
            except Exception as e:
                if self.recording:
                    print(f"❌ 录制错误: {e}")
                
    def get_audio(self) -> Optional[bytes]:
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
            
    def stop(self):
        with self._lock:
            self.recording = False
        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=1.0)
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        self.audio.terminate()


class InterviewClientV2:
    """客户访谈客户端 V2 - 指令驱动版本"""
    
    def __init__(
        self, 
        api_key: str,
        question_file: str = "questions.yaml",
        model: str = ModelType.STEP_AUDIO_2.value,
        temperature: float = 0.8,
        vad_threshold: float = 0.5,
        vad_silence_duration_ms: int = 700
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.vad_threshold = vad_threshold
        self.vad_silence_duration_ms = vad_silence_duration_ms
        
        # 问题管理器
        self.question_manager = QuestionManager(question_file)
        self.session_recorder: Optional[SessionRecorder] = None
        
        # 当前问题状态
        self.current_question: Optional[Question] = None
        self.waiting_for_answer = False
        self.current_transcript = ""
        
        # WebSocket 和音频
        self.ws = None
        self.running = False
        self.connection_state = ConnectionState.DISCONNECTED
        
        self.player = AudioPlayer()
        self.recorder = AudioRecorder()
        
        self.receive_thread = None
        self.send_thread = None
        
        self.is_ai_speaking = False
        self.user_speaking = False
        
        # 同步事件
        self.answer_received = threading.Event()
        self.ai_finished_speaking = threading.Event()
        
    def connect(self):
        """建立 WebSocket 连接"""
        url = f"{WS_URL}?model={self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        print(f"🔌 正在连接到 {url}...")
        self.connection_state = ConnectionState.CONNECTING
        
        try:
            self.ws = create_connection(url, header=headers, timeout=10)
            self.connection_state = ConnectionState.CONNECTED
            print("✅ WebSocket 连接成功！")
            
            # 初始配置（通用指令）
            self._configure_initial_session()
            
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            raise Exception(f"连接失败: {e}")
        
    def _configure_initial_session(self):
        """初始会话配置"""
        instructions = """你是一个专业、友好的访谈助手。
你会收到具体的指令告诉你要问什么问题，以及如何处理回答。
请严格按照指令执行，用自然、亲切的语气交流。"""
        
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": instructions,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self.vad_threshold,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": self.vad_silence_duration_ms
                },
                "temperature": self.temperature,
                "max_response_output_tokens": 4096
            }
        }
        self._send_event(config)
        print("⚙️  初始会话配置完成")
    
    def _update_instructions_for_question(self, question: Question):
        """为特定问题更新 instructions（方案A：指令驱动）"""
        
        # 根据问题类型定制指令
        if question.type == "yesno":
            answer_guide = "这是一个是非题，用户通常会回答'是'、'否'或类似的答案。"
        elif question.type == "choice":
            answer_guide = "这是一个选择题，用户会选择其中一个选项。"
        else:  # open
            answer_guide = "这是一个开放式问题，请耐心倾听用户的完整回答。"
        
        # 构建针对当前问题的精确指令
        instructions = f"""你是访谈助手，当前是第 {question.id} 个问题。

【步骤1：提问阶段】
- 收到 [执行问题{question.id}] 信号后，用自然、友好的语气向用户提问
- 必须完整地说出这个问题："{question.question}"
- {answer_guide}
- 提问后立即停止，等待用户回答

【步骤2：确认阶段】
- 收到 [用户已回答，请确认] 信号后，用简短的话确认
- 例如："好的，我记录下来了" 或 "明白了，谢谢您"
- 确认后立即停止

【严格禁止】
❌ 不要偏离问题内容
❌ 不要自己编造问题
❌ 不要追问或提出新问题
❌ 不要总结或评论用户的回答
❌ 不要在没收到信号时主动说话"""

        # 发送更新指令
        config = {
            "type": "session.update",
            "session": {
                "instructions": instructions
            }
        }
        self._send_event(config)
        print(f"🔄 已更新指令 [问题 {question.id}]")
        
    def _send_event(self, event: Dict[str, Any]):
        """发送事件"""
        if self.connection_state == ConnectionState.CONNECTED and self.ws:
            try:
                self.ws.send(json.dumps(event))
            except Exception as e:
                print(f"❌ 发送消息失败: {e}")
                
    def start_interview(self):
        """开始访谈"""
        print("\n" + "=" * 60)
        print("🎤 客户访谈系统 V2（指令驱动版）")
        print("=" * 60)
        
        # 加载问题
        if not self.question_manager.load_questions():
            print("❌ 加载问题失败，无法开始访谈")
            return
        
        # 创建会话记录器
        self.session_recorder = SessionRecorder()
        
        print(f"\n📊 访谈配置:")
        print(f"   模型: {self.model}")
        print(f"   问题总数: {len(self.question_manager.questions)}")
        print(f"   会话ID: {self.session_recorder.session_id}")
        print(f"   流程控制: 指令驱动（精确控制）")
        print("\n" + "=" * 60 + "\n")
        
        self.running = True
        
        # 启动音频播放和录制
        self.player.start()
        self.recorder.start()
        
        # 启动接收和发送线程
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        
        self.receive_thread.start()
        self.send_thread.start()
        
        # 等待连接稳定
        time.sleep(1)
        
        try:
            # 发送欢迎语
            self._say_welcome()
            
            # 逐个提问
            while self.running and self.question_manager.has_next_question():
                question = self.question_manager.get_next_question()
                if question:
                    success = self._ask_question_v2(question)
                    if not success:
                        print("⚠️  该问题未获得有效回答，继续下一题")
                    
            # 访谈完成
            if self.running:
                self._complete_interview()
                
        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断访谈")
        finally:
            self.stop()
    
    def _say_welcome(self):
        """播放欢迎语"""
        welcome_msg = self.question_manager.get_welcome_message()
        print(f"🤖 欢迎: {welcome_msg}\n")
        
        # 使用临时指令
        temp_instructions = f"""请用友好、亲切的语气说："{welcome_msg}"
说完后立即停止，等待下一步指令。"""
        
        self._send_event({
            "type": "session.update",
            "session": {"instructions": temp_instructions}
        })
        time.sleep(0.5)
        
        # 触发AI说话
        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "[开始欢迎]"}]
            }
        })
        self._send_event({"type": "response.create"})
        
        # 等待AI说完
        self.ai_finished_speaking.clear()
        self.ai_finished_speaking.wait(timeout=10)
        time.sleep(1)
    
    def _ask_question_v2(self, question: Question) -> bool:
        """
        提出一个问题并等待回答（V2版本：指令驱动）
        返回：是否成功获得回答
        """
        self.current_question = question
        self.waiting_for_answer = True
        self.current_transcript = ""
        self.answer_received.clear()
        self.ai_finished_speaking.clear()
        
        progress = self.question_manager.get_current_progress()
        print(f"\n{'='*60}")
        print(f"📝 进度: {progress}")
        print(f"💭 问题类型: {question.type}")
        print(f"🤖 提问: {question.question}")
        print(f"{'='*60}\n")
        
        # 步骤1：确保前一个响应已完成，等待AI停止说话
        if self.is_ai_speaking:
            print("⏳ 等待上一个响应完成...")
            self.ai_finished_speaking.wait(timeout=5)
            time.sleep(0.5)
        
        # 步骤2：更新指令为当前问题
        self._update_instructions_for_question(question)
        time.sleep(0.5)  # 给足够时间让指令更新生效
        
        # 步骤3：触发AI提问
        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": f"[执行问题{question.id}]"}]
            }
        })
        time.sleep(0.2)
        
        self._send_event({"type": "response.create"})
        
        # 步骤4：等待AI提问完成
        print("⏳ AI正在提问...")
        self.ai_finished_speaking.clear()
        self.ai_finished_speaking.wait(timeout=10)
        print("✅ AI提问完成，等待用户回答\n")
        time.sleep(0.3)
        
        # 步骤5：等待用户回答
        timeout = 90  # 90秒超时
        if self.answer_received.wait(timeout):
            # 保存回答
            if self.current_transcript:
                print(f"\n✅ 已记录回答")
                self.session_recorder.add_answer(
                    question_id=question.id,
                    question_text=question.question,
                    transcript=self.current_transcript
                )
                
                # 步骤6：触发AI确认（"好的，我记录下来了"）
                time.sleep(0.5)
                self.ai_finished_speaking.clear()
                self._send_event({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "[用户已回答，请确认]"}]
                    }
                })
                time.sleep(0.2)
                self._send_event({"type": "response.create"})
                
                # 等待AI确认完成
                self.ai_finished_speaking.wait(timeout=8)
                time.sleep(0.8)  # 额外等待，确保完全结束
                
                self.waiting_for_answer = False
                return True
            else:
                print(f"⚠️  未检测到有效回答")
                self.waiting_for_answer = False
                return False
        else:
            print(f"⏰ 回答超时")
            self.waiting_for_answer = False
            return False
    
    def _complete_interview(self):
        """完成访谈"""
        print("\n" + "=" * 60)
        print("✅ 访谈已完成！")
        print("=" * 60 + "\n")
        
        # 发送结束语
        completion_msg = self.question_manager.get_completion_message()
        print(f"🤖 结束语: {completion_msg}\n")
        
        self._send_event({
            "type": "session.update",
            "session": {"instructions": f"用友好的语气说：{completion_msg}"}
        })
        time.sleep(0.3)
        
        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "[结束访谈]"}]
            }
        })
        self._send_event({"type": "response.create"})
        time.sleep(3)
        
        # 保存会话记录
        if self.session_recorder:
            self.session_recorder.save_session({
                "version": "v2_instruction_driven",
                "total_questions": len(self.question_manager.questions),
                "answered": self.session_recorder.get_answer_count()
            })
    
    def _send_loop(self):
        """发送音频数据循环"""
        while self.running:
            try:
                audio_data = self.recorder.get_audio()
                if audio_data:
                    encoded = base64.b64encode(audio_data).decode('ascii')
                    event = {
                        "type": "input_audio_buffer.append",
                        "audio": encoded
                    }
                    self._send_event(event)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"❌ 发送错误: {e}")
                break
                
    def _receive_loop(self):
        """接收响应循环"""
        while self.running:
            try:
                message = self.ws.recv()
                if not message:
                    break
                    
                event = json.loads(message)
                event_type = event.get("type")
                
                # 处理事件
                if event_type == "session.created":
                    session_id = event.get('session', {}).get('id', '')
                    print(f"✅ 会话已创建 (ID: {session_id[:8]}...)")
                    
                elif event_type == "session.updated":
                    # 静默处理，避免过多输出
                    pass
                    
                elif event_type == "input_audio_buffer.speech_started":
                    self.user_speaking = True
                    if self.waiting_for_answer:
                        print("🎤 [用户开始回答...]", end="", flush=True)
                    
                elif event_type == "input_audio_buffer.speech_stopped":
                    self.user_speaking = False
                    print(" [语音结束]")
                    
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if transcript:
                        if self.waiting_for_answer:
                            # 这是对问题的回答
                            print(f"👤 客户: {transcript}")
                            self.current_transcript = transcript
                            self.answer_received.set()
                    
                elif event_type == "response.created":
                    self.is_ai_speaking = True
                    
                elif event_type == "response.audio.delta":
                    if self.is_ai_speaking and not self.user_speaking:
                        audio_delta = event.get("delta", "")
                        if audio_delta:
                            pcm_bytes = base64.b64decode(audio_delta)
                            self.player.add_audio(pcm_bytes)
                        
                elif event_type == "response.done":
                    self.is_ai_speaking = False
                    self.ai_finished_speaking.set()
                    
                elif event_type == "error":
                    error_data = event.get("error", {})
                    print(f"\n❌ 错误: {error_data}")
                    
            except WebSocketConnectionClosedException:
                print("\n❌ WebSocket 连接已关闭")
                self.running = False
                break
            except Exception as e:
                if self.running:
                    print(f"\n❌ 接收错误: {e}")
                self.running = False
                break
            
    def stop(self):
        """停止访谈"""
        print("\n🛑 正在停止...")
        self.running = False
        
        self.recorder.stop()
        self.player.stop()
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)
        if self.send_thread and self.send_thread.is_alive():
            self.send_thread.join(timeout=1.0)
            
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
                
        self.connection_state = ConnectionState.DISCONNECTED
        print("👋 访谈已结束")


def main():
    """主函数"""
    print("\n🚀 客户访谈系统 V2 - 指令驱动版")
    print("=" * 60)
    
    # 检查 API Key
    if API_KEY == "your-api-key-here":
        print("⚠️  请先设置环境变量 STEPFUN_API_KEY")
        print("export STEPFUN_API_KEY='your-actual-api-key'")
        return
        
    # 检查音频设备
    try:
        audio = pyaudio.PyAudio()
        print(f"🎵 音频设备初始化成功")
        print(f"   输入设备: {audio.get_default_input_device_info()['name']}")
        print(f"   输出设备: {audio.get_default_output_device_info()['name']}")
        audio.terminate()
    except Exception as e:
        print(f"❌ 音频设备初始化失败: {e}")
        return
    
    # 创建访谈客户端（V2版本）
    client = InterviewClientV2(
        API_KEY,
        question_file="questions.yaml",
        model=ModelType.STEP_AUDIO_2.value,
        temperature=0.7,  # 稍微降低，使回答更一致
        vad_threshold=0.5,
        vad_silence_duration_ms=700
    )
    
    try:
        client.connect()
        client.start_interview()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

