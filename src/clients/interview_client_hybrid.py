"""
客户访谈客户端 - 混合模式
方案 A：TTS 生成问题 + Realtime API 接收回答
- 问题：使用 TTS API 生成音频，100% 忠实原文
- 回答：使用 Realtime API 接收语音并转写
"""

import base64
import json
import os
import threading
import queue
import time
from websocket import create_connection, WebSocketConnectionClosedException
import pyaudio
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from src.core.question_manager import QuestionManager, SessionRecorder, Question
from src.analyzers.health_analyzer_client import HealthAnalyzerClient

# 配置信息
API_KEY = os.getenv("STEPFUN_API_KEY", "your-api-key-here")
WS_URL = "wss://api.stepfun.com/v1/realtime"
TTS_URL = "https://api.stepfun.com/v1/audio/speech"


# 支持的模型
class ModelType(Enum):
    STEP_AUDIO_2 = "step-audio-2"
    STEP_AUDIO_2_MINI = "step-audio-2-mini"


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


class TTSGenerator:
    """TTS 音频生成器 - 用于生成问题语音"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.tts_model = "step-tts-mini"  # 默认模型
        self.tts_voice = "cixingnansheng"  # 默认音色

    def generate_speech(self, text: str, question_id: int) -> Optional[Path]:
        """
        生成语音文件
        返回：音频文件路径
        """
        # 检查缓存
        cache_file = self.cache_dir / f"question_{question_id}.mp3"
        if cache_file.exists():
            print(f"✅ 使用缓存音频: {cache_file.name}")
            return cache_file

        print(f"🎙️  正在生成语音: {text[:30]}...")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # 阶跃星辰 TTS API 参数格式（参考官方文档）
            data = {"model": self.tts_model,
                    "input": text, "voice": self.tts_voice}

            response = requests.post(
                TTS_URL, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                # 保存音频文件
                with open(cache_file, "wb") as f:
                    f.write(response.content)
                print(f"✅ 语音生成成功: {cache_file.name}")
                return cache_file
            else:
                print(f"❌ TTS 错误: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ TTS 生成失败: {e}")
            return None

    def clear_cache(self):
        """清空缓存"""
        for file in self.cache_dir.glob("*.mp3"):
            file.unlink()
        print("🗑️  TTS 缓存已清空")


class AudioPlayer:
    """音频播放器 - 支持文件播放"""

    def __init__(self):
        self.audio = pyaudio.PyAudio()

    def play_file(self, file_path: Path):
        """播放音频文件"""
        try:
            import soundfile as sf

            # 读取音频文件
            data, samplerate = sf.read(str(file_path))

            # 转换为 PyAudio 可播放的格式
            if len(data.shape) > 1:  # 立体声转单声道
                data = data.mean(axis=1)

            # 重采样到 24kHz（如果需要）
            if samplerate != SAMPLE_RATE:
                from scipy import signal

                num_samples = int(len(data) * SAMPLE_RATE / samplerate)
                data = signal.resample(data, num_samples)

            # 转换为 int16
            data = (data * 32767).astype("int16")

            # 播放
            stream = self.audio.open(
                format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, output=True
            )

            stream.write(data.tobytes())
            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"❌ 播放错误: {e}")

    def terminate(self):
        """清理资源"""
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
        """启动录制"""
        with self._lock:
            if self.recording:
                return
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            self.recording = True
            self.record_thread = threading.Thread(
                target=self._record_loop, daemon=True)
            self.record_thread.start()

    def _record_loop(self):
        """录制循环"""
        while self.recording:
            try:
                audio_data = self.stream.read(
                    CHUNK_SIZE, exception_on_overflow=False)
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


class HybridInterviewClient:
    """混合模式访谈客户端"""

    def __init__(
        self,
        api_key: str,
        question_file: str = "questions.yaml",
        model: str = ModelType.STEP_AUDIO_2.value,
        vad_threshold: float = 0.5,
        vad_silence_duration_ms: int = 700,
        tts_voice: str = "cixingnansheng",  # 磁性男声
        tts_model: str = "step-tts-mini",  # step-tts-mini 或 step-tts-vivid
    ):
        self.api_key = api_key
        self.model = model
        self.vad_threshold = vad_threshold
        self.vad_silence_duration_ms = vad_silence_duration_ms
        self.tts_voice = tts_voice
        self.tts_model = tts_model

        # 问题管理器
        self.question_manager = QuestionManager(question_file)
        self.session_recorder: Optional[SessionRecorder] = None

        # TTS 生成器
        self.tts_generator = TTSGenerator(api_key)
        self.tts_generator.tts_model = tts_model
        self.tts_generator.tts_voice = tts_voice

        # 健康分析客户端
        self.health_analyzer = HealthAnalyzerClient(api_key)

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

        self.user_speaking = False

        # 同步事件
        self.answer_received = threading.Event()

    def connect(self):
        """建立 WebSocket 连接（仅用于接收用户语音）"""
        url = f"{WS_URL}?model={self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        print(f"🔌 正在连接到 Realtime API...")
        self.connection_state = ConnectionState.CONNECTING

        try:
            self.ws = create_connection(url, header=headers, timeout=10)
            self.connection_state = ConnectionState.CONNECTED
            print("✅ WebSocket 连接成功！")

            # 配置会话（仅用于语音识别）
            self._configure_session()

        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            raise Exception(f"连接失败: {e}")

    def _configure_session(self):
        """配置会话参数"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],  # 必须同时包含 text 和 audio
                "instructions": "你是语音识别助手，只负责识别用户语音，不需要生成任何回复。",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",  # 必需字段
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self.vad_threshold,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": self.vad_silence_duration_ms,
                },
                "temperature": 0.8,
                "max_response_output_tokens": "inf",  # 禁止生成回复
            },
        }
        self._send_event(config)
        print("⚙️  会话配置完成（语音识别模式）")
        print(f"   VAD 阈值: {self.vad_threshold}")
        print(f"   静音检测: {self.vad_silence_duration_ms}ms")

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
        print("🎤 客户访谈系统 - 混合模式（TTS + Realtime）")
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
        print(f"   问题语音: TTS 生成（100% 准确）")
        print(f"   回答识别: Realtime API")
        print("\n" + "=" * 60 + "\n")

        # 预生成所有问题的语音
        print("🎙️  正在预生成问题语音...")
        self._pregenerate_tts()
        print()

        self.running = True

        # 启动录制
        self.recorder.start()

        # 启动接收和发送线程
        self.receive_thread = threading.Thread(
            target=self._receive_loop, daemon=True)
        self.send_thread = threading.Thread(
            target=self._send_loop, daemon=True)

        self.receive_thread.start()
        self.send_thread.start()

        # 等待连接稳定
        time.sleep(1)

        try:
            # 播放欢迎语
            self._play_welcome()

            # 逐个提问
            while self.running and self.question_manager.has_next_question():
                question = self.question_manager.get_next_question()
                if question:
                    success = self._ask_question_hybrid(question)
                    if not success:
                        print("⚠️  该问题未获得有效回答，继续下一题")

            # 访谈完成
            if self.running:
                self._complete_interview()

        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断访谈")
        finally:
            self.stop()

    def _pregenerate_tts(self):
        """预生成所有问题的 TTS 音频"""
        # 欢迎语
        welcome_msg = self.question_manager.get_welcome_message()
        self.tts_generator.generate_speech(welcome_msg, 0)

        # 所有问题
        for question in self.question_manager.questions:
            self.tts_generator.generate_speech(question.question, question.id)

        # 结束语
        completion_msg = self.question_manager.get_completion_message()
        self.tts_generator.generate_speech(completion_msg, 9999)

        print("✅ 所有语音文件已准备就绪")

    def _play_welcome(self):
        """播放欢迎语"""
        welcome_msg = self.question_manager.get_welcome_message()
        print(f"🤖 欢迎: {welcome_msg}\n")

        audio_file = self.tts_generator.cache_dir / "question_0.mp3"
        if audio_file.exists():
            self.player.play_file(audio_file)
            time.sleep(1)

    def _ask_question_hybrid(self, question: Question) -> bool:
        """
        混合模式提问：TTS 播放问题，Realtime 接收回答
        返回：是否成功获得回答
        """
        self.current_question = question
        self.waiting_for_answer = True
        self.current_transcript = ""
        self.answer_received.clear()

        progress = self.question_manager.get_current_progress()
        print(f"\n{'=' * 60}")
        print(f"📝 进度: {progress}")
        print(f"💭 问题类型: {question.type}")
        print(f"🎯 问题: {question.question}")
        print(f"{'=' * 60}\n")

        # 步骤1：播放 TTS 生成的问题音频
        audio_file = self.tts_generator.cache_dir / \
            f"question_{question.id}.mp3"
        if audio_file.exists():
            print("🔊 播放问题...")
            self.player.play_file(audio_file)
            time.sleep(0.5)
            print("✅ 问题播放完成，等待用户回答\n")
        else:
            print("❌ 音频文件不存在，跳过该问题")
            return False

        # 步骤2：等待用户语音回答
        timeout = 90  # 90秒超时
        if self.answer_received.wait(timeout):
            if self.current_transcript:
                print(f"\n✅ 已记录回答: {self.current_transcript}")
                self.session_recorder.add_answer(
                    question_id=question.id,
                    question_text=question.question,
                    transcript=self.current_transcript,
                )

                time.sleep(1.0)
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

        # 播放结束语
        completion_msg = self.question_manager.get_completion_message()
        print(f"🤖 结束语: {completion_msg}\n")

        audio_file = self.tts_generator.cache_dir / "question_9999.mp3"
        if audio_file.exists():
            self.player.play_file(audio_file)
            time.sleep(2)

        # 保存会话记录
        if self.session_recorder:
            self.session_recorder.save_session(
                {
                    "version": "hybrid_tts_realtime",
                    "total_questions": len(self.question_manager.questions),
                    "answered": self.session_recorder.get_answer_count(),
                }
            )

            # 生成 AI 健康分析报告
            self._generate_health_analysis()

    def _generate_health_analysis(self):
        """生成健康分析报告"""
        if not self.session_recorder or self.session_recorder.get_answer_count() == 0:
            print("⚠️  没有回答记录，跳过健康分析")
            return

        print("\n" + "=" * 70)
        print("🤖 正在生成 AI 健康分析报告...")
        print("=" * 70)

        try:
            # 准备分析数据
            answers = self.session_recorder.get_answers_for_analysis()
            questions_count = len(self.question_manager.questions)

            # 调用 AI 分析
            analysis_result = self.health_analyzer.analyze_interview(
                answers, questions_count
            )

            if "error" in analysis_result:
                print(f"\n❌ AI 分析失败: {analysis_result.get('message', '未知错误')}")
                return

            # 格式化报告
            formatted_report = self.health_analyzer.format_report(
                analysis_result)

            # 显示报告
            print("\n" + formatted_report)

            # 保存报告
            self.session_recorder.save_analysis_report(
                analysis_result, formatted_report
            )

            print("\n✅ 健康分析报告生成完成！")

        except Exception as e:
            print(f"\n❌ 生成健康分析报告时出错: {e}")
            import traceback

            traceback.print_exc()

    def _send_loop(self):
        """发送音频数据循环"""
        while self.running:
            try:
                audio_data = self.recorder.get_audio()
                if audio_data:
                    encoded = base64.b64encode(audio_data).decode("ascii")
                    event = {"type": "input_audio_buffer.append",
                             "audio": encoded}
                    self._send_event(event)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"❌ 发送错误: {e}")
                break

    def _receive_loop(self):
        """接收响应循环（仅处理转写）"""
        while self.running:
            try:
                message = self.ws.recv()
                if not message:
                    break

                event = json.loads(message)
                event_type = event.get("type")

                # 只处理语音相关事件
                if event_type == "session.created":
                    session_id = event.get("session", {}).get("id", "")
                    print(f"✅ 会话已创建 (ID: {session_id[:8]}...)")

                elif event_type == "session.updated":
                    pass  # 静默

                elif event_type == "input_audio_buffer.speech_started":
                    self.user_speaking = True
                    if self.waiting_for_answer:
                        print("🎤 [用户开始回答...]", end="", flush=True)

                elif event_type == "input_audio_buffer.speech_stopped":
                    self.user_speaking = False
                    print(" [语音结束]")

                elif (
                    event_type
                    == "conversation.item.input_audio_transcription.completed"
                ):
                    transcript = event.get("transcript", "")
                    if transcript and self.waiting_for_answer:
                        print(f"👤 客户: {transcript}")
                        self.current_transcript = transcript
                        self.answer_received.set()

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
        self.player.terminate()

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
    print("\n🚀 客户访谈系统 - 混合模式")
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

    # 创建混合模式客户端
    # VAD 参数调优指南：
    # - vad_threshold (0.0-1.0): 值越高，越不容易触发（需要更大声音）
    #   * 0.3-0.4: 灵敏（小声也能检测）
    #   * 0.5: 标准（推荐）
    #   * 0.6-0.7: 不灵敏（需要较大声音）
    #   * 0.8-0.9: 很不灵敏（需要很大声音，避免误触发）
    # - vad_silence_duration_ms: 静音多久判断为说话结束
    #   * 300-500: 快速响应（可能会打断长句）
    #   * 700-800: 标准（推荐）
    #   * 1000+: 容忍长停顿
    client = HybridInterviewClient(
        API_KEY,
        question_file="questions.yaml",
        model=ModelType.STEP_AUDIO_2.value,
        vad_threshold=0.7,  # 降低灵敏度，避免误触发（你可以根据实际情况调整 0.6-0.8）
        vad_silence_duration_ms=800,  # 稍微增加静音容忍时间
        tts_voice="wenrounvsheng",  # 音色选项见下方注释
        tts_model="step-tts-mini",  # step-tts-mini 或 step-tts-vivid
    )

    # step-tts-mini 支持的音色（22种）:
    # 磁性男声: cixingnansheng, 温柔男声: wenrounansheng
    # 甜美女声: tianmeinvsheng, 温柔女声: wenrounvsheng
    # 更多音色见: https://platform.stepfun.com/docs/guide/tts

    # step-tts-vivid 支持的音色（4种，更生动）:
    # shuangkuainansheng, ganliannvsheng, qinhenvsheng, huolinvsheng

    try:
        client.connect()
        client.start_interview()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
