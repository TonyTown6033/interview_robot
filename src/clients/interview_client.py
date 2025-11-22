"""
客户访谈客户端
基于 askagent 的实时语音对话，实现问答式采集
"""

import base64
import json
import os
import threading
import queue
import time
from websocket import create_connection, WebSocketConnectionClosedException
import pyaudio
import numpy as np
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

from question_manager import QuestionManager, SessionRecorder

# 配置信息
API_KEY = os.getenv("STEPFUN_API_KEY", "your-api-key-here")
WS_URL = "wss://api.stepfun.com/v1/realtime"

# 支持的模型
class ModelType(Enum):
    STEP_AUDIO_2 = "step-audio-2"
    STEP_AUDIO_2_MINI = "step-audio-2-mini"
    STEP_AUDIO_2_THINK = "step-audio-2-think"
    STEP_AUDIO_2_MINI_THINK = "step-audio-2-mini-think"
    STEP_1O_AUDIO = "step-1o-audio"

# 音频配置
SAMPLE_RATE = 24000  # 24kHz
CHANNELS = 1  # 单声道
CHUNK_SIZE = 480  # 20ms @ 24kHz
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
        """启动音频播放流"""
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
        """播放循环"""
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
        """添加音频数据到播放队列"""
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
        """清空播放队列"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
    def stop(self):
        """停止播放"""
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
        """启动音频录制流"""
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
        """录制循环"""
        while self.recording:
            try:
                audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_queue.put(audio_data)
            except Exception as e:
                if self.recording:
                    print(f"❌ 录制错误: {e}")
                
    def get_audio(self) -> Optional[bytes]:
        """获取录制的音频数据"""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
            
    def stop(self):
        """停止录制"""
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


class InterviewClient:
    """客户访谈客户端 - 问答式采集"""
    
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
        self.current_question = None
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
        
        # 消息队列
        self.message_queue = []
        self._message_lock = threading.Lock()
        
        # 同步事件
        self.answer_received = threading.Event()
        
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
            
            # 配置会话
            self._configure_session()
            
            # 发送队列中的消息
            self._flush_message_queue()
            
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            raise Exception(f"连接失败: {e}")
        
    def _configure_session(self):
        """配置会话参数"""
        instructions = """你是一个专业的客户访谈助手。你的任务是：
1. 按照预设的问题顺序向客户提问
2. 耐心倾听客户的回答
3. 用友好、专业的语气交流
4. 不要偏离预设的问题，但可以适当追问细节
5. 每次只问一个问题，等待客户回答完成后再继续"""
        
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
        print("⚙️  会话配置完成")
        
    def _send_event(self, event: Dict[str, Any]):
        """发送事件"""
        if self.connection_state == ConnectionState.CONNECTED and self.ws:
            try:
                self.ws.send(json.dumps(event))
            except Exception as e:
                print(f"❌ 发送消息失败: {e}")
        else:
            with self._message_lock:
                self.message_queue.append(event)
                
    def _flush_message_queue(self):
        """发送队列中的消息"""
        with self._message_lock:
            if self.message_queue:
                for event in self.message_queue:
                    try:
                        self.ws.send(json.dumps(event))
                    except Exception as e:
                        print(f"❌ 发送缓存消息失败: {e}")
                self.message_queue.clear()
                
    def start_interview(self):
        """开始访谈"""
        print("\n" + "=" * 60)
        print("🎤 客户访谈系统已启动！")
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
        print("\n使用说明：")
        print("  📢 AI会向您提问，请对着麦克风回答")
        print("  ⏸️  按 Ctrl+C 提前结束访谈")
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
            self._send_text_message(self.question_manager.get_welcome_message())
            time.sleep(3)  # 等待欢迎语播放完成
            
            # 逐个提问
            while self.running and self.question_manager.has_next_question():
                question = self.question_manager.get_next_question()
                if question:
                    self._ask_question(question)
                    
            # 访谈完成
            if self.running:
                self._complete_interview()
                
        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断访谈")
        finally:
            self.stop()
            
    def _send_text_message(self, text: str):
        """发送文本消息（让AI说话）"""
        # 创建对话项
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"请用友好的语气说：{text}"
                    }
                ]
            }
        }
        self._send_event(event)
        
        # 触发响应
        response_event = {
            "type": "response.create"
        }
        self._send_event(response_event)
    
    def _ask_question(self, question):
        """提出一个问题并等待回答"""
        self.current_question = question
        self.waiting_for_answer = True
        self.current_transcript = ""
        self.answer_received.clear()
        
        progress = self.question_manager.get_current_progress()
        print(f"\n{'='*60}")
        print(f"📝 进度: {progress}")
        print(f"🤖 提问: {question.question}")
        print(f"{'='*60}\n")
        
        # 发送问题
        self._send_text_message(question.question)
        
        # 等待用户回答（带超时）
        timeout = 120  # 2分钟超时
        if self.answer_received.wait(timeout):
            # 保存回答
            if self.current_transcript:
                print(f"✅ 已记录回答\n")
                self.session_recorder.add_answer(
                    question_id=question.id,
                    question_text=question.question,
                    transcript=self.current_transcript
                )
            else:
                print(f"⚠️  未检测到有效回答\n")
        else:
            print(f"⏰ 回答超时\n")
            
        self.waiting_for_answer = False
        time.sleep(1)  # 问题间隔
        
    def _complete_interview(self):
        """完成访谈"""
        print("\n" + "=" * 60)
        print("✅ 访谈已完成！")
        print("=" * 60 + "\n")
        
        # 发送结束语
        completion_msg = self.question_manager.get_completion_message()
        self._send_text_message(completion_msg)
        time.sleep(3)
        
        # 保存会话记录
        if self.session_recorder:
            self.session_recorder.save_session({
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
        text_buffer = ""
        
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
                    print("✅ 会话配置已更新")
                    
                elif event_type == "input_audio_buffer.speech_started":
                    self.user_speaking = True
                    if self.waiting_for_answer:
                        print("🎤 [正在回答...]", end="", flush=True)
                    
                elif event_type == "input_audio_buffer.speech_stopped":
                    self.user_speaking = False
                    print(" [语音结束]")
                    
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if transcript and self.waiting_for_answer:
                        print(f"👤 客户回答: {transcript}")
                        self.current_transcript = transcript
                        self.answer_received.set()  # 通知已收到回答
                    
                elif event_type == "response.created":
                    self.is_ai_speaking = True
                    text_buffer = ""
                    
                elif event_type == "response.text.delta":
                    if self.is_ai_speaking:
                        text_delta = event.get("delta", "")
                        text_buffer += text_delta
                    
                elif event_type == "response.audio.delta":
                    if self.is_ai_speaking and not self.user_speaking:
                        audio_delta = event.get("delta", "")
                        if audio_delta:
                            pcm_bytes = base64.b64decode(audio_delta)
                            self.player.add_audio(pcm_bytes)
                        
                elif event_type == "response.done":
                    self.is_ai_speaking = False
                    
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
    print("\n🚀 客户访谈系统")
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
    
    # 创建访谈客户端
    client = InterviewClient(
        API_KEY,
        question_file="questions.yaml",
        model=ModelType.STEP_AUDIO_2.value,
        temperature=0.8,
        vad_threshold=0.5,
        vad_silence_duration_ms=700  # 稍长一点，让客户有时间思考
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

