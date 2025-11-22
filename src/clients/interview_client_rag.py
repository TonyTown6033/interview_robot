"""
客户访谈客户端 - RAG 增强版
基于 RAG 的智能问题检索 + AI 灵活对话
- 使用向量数据库根据上下文智能选择问题
- AI 可以灵活表述问题，添加过渡语，进行追问
- 保证问题内容来自知识库，但表达方式自然灵活
"""

import base64
import json
import os
import threading
import queue
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
from websocket import create_connection, WebSocketConnectionClosedException
import pyaudio
from typing import Optional, Dict, Any, List
from enum import Enum

from src.core.question_rag import QuestionRAG, Question, analyze_answer_completeness
from src.core.question_manager import SessionRecorder

# 配置信息
API_KEY = os.getenv("STEPFUN_API_KEY", "your-api-key-here")
WS_URL = "wss://api.stepfun.com/v1/realtime"


# ==================== 日志配置 ====================
def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO):
    """
    配置日志记录器

    Args:
        name: logger 名称
        log_file: 日志文件路径（可选）
        level: 控制台日志级别

    Returns:
        配置好的 logger
    """
    logger = logging.getLogger(name)
    # Logger本身设为DEBUG，让handler控制级别
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（如果指定）
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的日志
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 创建全局 logger
logger = setup_logger(
    'RAGInterview',
    log_file=f'logs/interview_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,  # 可以改为 DEBUG 查看更详细信息
)


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
                frames_per_buffer=CHUNK_SIZE,
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
                    logger.error(f"❌ 播放错误: {e}")

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
                frames_per_buffer=CHUNK_SIZE,
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
                    logger.error(f"❌ 录制错误: {e}")

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


class ConversationContext:
    """对话上下文管理器"""

    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.qa_history: List[Dict[str, str]] = []  # 问答历史
        self.current_topic = ""  # 当前话题

    def add_qa(self, question: str, answer: str):
        """添加问答记录"""
        self.qa_history.append({"question": question, "answer": answer})
        # 保持历史记录不超过上限
        if len(self.qa_history) > self.max_history:
            self.qa_history.pop(0)

    def get_context_summary(self) -> str:
        """获取上下文摘要（用于 RAG 检索）"""
        if not self.qa_history:
            return "开始健康咨询访谈"

        # 返回最近的对话内容
        recent_qa = self.qa_history[-2:]  # 最近2轮
        context_parts = []
        for qa in recent_qa:
            context_parts.append(f"问：{qa['question']}")
            context_parts.append(f"答：{qa['answer']}")

        return " ".join(context_parts)

    def get_last_answer(self) -> Optional[str]:
        """获取最后一次回答"""
        if self.qa_history:
            return self.qa_history[-1]["answer"]
        return None


class RAGInterviewClient:
    """RAG 增强访谈客户端"""

    def __init__(
        self,
        api_key: str,
        question_file: str = "questions.yaml",
        model: str = ModelType.STEP_AUDIO_2.value,
        temperature: float = 0.7,
        vad_threshold: float = 0.5,
        vad_silence_duration_ms: int = 700,
        max_questions: int = 10,  # 最多问几个问题
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.vad_threshold = vad_threshold
        self.vad_silence_duration_ms = vad_silence_duration_ms
        self.max_questions = max_questions

        # RAG 问题检索引擎
        self.question_rag = QuestionRAG(question_file)
        self.session_recorder: Optional[SessionRecorder] = None

        # 对话上下文
        self.context = ConversationContext()

        # 当前问题状态
        self.current_question: Optional[Question] = None
        self.waiting_for_answer = False
        self.current_transcript = ""
        self.questions_asked = 0

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

        # 连接质量监控
        self.connection_errors = 0
        self.last_message_time = time.time()

    def connect(self):
        """建立 WebSocket 连接"""
        url = f"{WS_URL}?model={self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        logger.info(f"🔌 正在连接到 {url}...")
        self.connection_state = ConnectionState.CONNECTING

        try:
            self.ws = create_connection(url, header=headers, timeout=10)
            self.connection_state = ConnectionState.CONNECTED
            logger.info(f"✅ WebSocket 连接成功！")

            # 初始配置
            self._configure_initial_session()

        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            raise Exception(f"连接失败: {e}")

    def _configure_initial_session(self):
        """初始会话配置"""
        instructions = """你是一个专业、友好的健康咨询助手。

你的任务：
1. 根据提供的参考问题，用自然、亲切的语气与用户交流
2. 可以适当调整问题表述，使对话更自然流畅
3. 在问题之间添加简短的过渡语（如"好的，明白了"、"接下来"等）
4. 如果用户回答不够详细，可以追问澄清
5. 保持专业但不失温度，让用户感到舒适

重要原则：
- 每次只问一个问题
- 问题内容必须基于提供的参考，但表述可以灵活
- 说话要简洁，不要啰嗦
- 认真倾听用户的回答，不要急于提下一个问题
"""

        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": instructions,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self.vad_threshold,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": self.vad_silence_duration_ms,
                },
                "temperature": self.temperature,
                "max_response_output_tokens": 4096,
            },
        }
        self._send_event(config)
        logger.info(f"⚙️  初始会话配置完成（RAG 灵活模式）")

    def _send_event(self, event: Dict[str, Any]):
        """发送事件"""
        if self.connection_state == ConnectionState.CONNECTED and self.ws:
            try:
                self.ws.send(json.dumps(event))
            except Exception as e:
                logger.error(f"❌ 发送消息失败: {e}")

    def start_interview(self):
        """开始访谈"""
        logger.info(f"\n" + "=" * 60)
        logger.info(f"🎤 客户访谈系统 - RAG 增强版（智能 + 灵活）")
        logger.info(f"=" * 60)

        # 加载和索引问题
        if not self.question_rag.load_and_index_questions():
            logger.error("❌ 加载问题失败，无法开始访谈")
            return

        # 创建会话记录器
        self.session_recorder = SessionRecorder()

        logger.info(f"\n📊 访谈配置:")
        logger.info(f"   模型: {self.model}")
        logger.info(f"   问题库大小: {len(self.question_rag.questions)}")
        logger.info(f"   最多提问数: {self.max_questions}")
        logger.info(f"   会话ID: {self.session_recorder.session_id}")
        logger.info(f"   问题选择: RAG 智能检索")
        logger.info(f"   对话模式: AI 灵活表述")
        logger.info(f"\n" + "=" * 60 + "\n")

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

            # 智能提问循环
            while self.running and self.questions_asked < self.max_questions:
                # 根据上下文检索下一个问题
                next_question = self._retrieve_next_question()

                if next_question:
                    success = self._ask_question_rag(next_question)
                    if success:
                        self.questions_asked += 1
                else:
                    logger.info(f"✅ 所有相关问题都已提问")
                    break

            # 访谈完成
            if self.running:
                self._complete_interview()

        except KeyboardInterrupt:
            logger.info(f"\n\n⏹️  用户中断访谈")
        finally:
            self.stop()

    def _retrieve_next_question(self) -> Optional[Question]:
        """根据上下文检索下一个问题"""
        context = self.context.get_context_summary()
        logger.info(f"\n🔍 检索上下文: {context[:80]}...")

        question = self.question_rag.retrieve_next_question(
            context=context, n_results=3, exclude_asked=True
        )

        if question:
            logger.info(f"✅ 检索到问题 #{question.id}: {question.question}")

        return question

    def _say_welcome(self):
        """播放欢迎语"""
        welcome_msg = "您好，欢迎参加健康状况咨询。接下来我会问您几个关于健康的问题，请如实回答。"
        logger.info(f"🤖 欢迎: {welcome_msg}\n")

        # 触发 AI 说欢迎语
        self._send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"请用友好的语气说：{welcome_msg}",
                        }
                    ],
                },
            }
        )
        self._send_event({"type": "response.create"})

        # 等待 AI 说完
        self.ai_finished_speaking.clear()
        self.ai_finished_speaking.wait(timeout=10)
        time.sleep(1)

    def _ask_question_rag(self, question: Question) -> bool:
        """
        RAG 模式提问：AI 灵活表述问题
        返回：是否成功获得回答
        """
        self.current_question = question
        self.waiting_for_answer = True
        self.current_transcript = ""
        self.answer_received.clear()
        self.ai_finished_speaking.clear()

        logger.debug(f"🔧 初始化问题状态: waiting_for_answer=True, current_transcript='', events cleared")

        logger.info(f"\n{'=' * 60}")
        logger.info(f"📝 进度: {self.questions_asked + 1}/{self.max_questions}")
        logger.info(f"💭 问题类型: {question.type}")
        logger.info(f"📋 参考问题: {question.question}")
        logger.info(f"{'=' * 60}")
        logger.info(f"🤖 AI 实际说: ")

        # 等待上一个响应完成
        if self.is_ai_speaking:
            logger.info(f"⏳ 等待上一个响应完成...")
            self.ai_finished_speaking.wait(timeout=5)
            time.sleep(0.5)

        # 构建提问指令（灵活版）
        last_answer = self.context.get_last_answer()

        if last_answer and self.questions_asked > 0:
            # 有上下文，添加过渡
            prompt = f"""[上一个问题的回答是: {last_answer}]

现在请基于以下参考问题，用自然的方式继续提问：
参考问题: {question.question}

要求：
1. 可以先简短地回应上一个回答（如"好的，明白了"）
2. 然后提出新问题，表述要自然流畅
3. 整体保持简洁，不要啰嗦
"""
        else:
            # 第一个问题，直接问
            prompt = f"""请基于以下参考问题，用自然、友好的方式提问：
参考问题: {question.question}

要求：
1. 保持问题核心内容不变
2. 表述要自然亲切
3. 简洁明了
"""

        # 发送提问请求
        self._send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            }
        )
        self._send_event({"type": "response.create"})

        # 等待 AI 提问完成
        self.ai_finished_speaking.clear()
        self.ai_finished_speaking.wait(timeout=15)
        logger.info(f"\n✅ AI提问完成，等待用户回答\n")
        time.sleep(0.3)

        # 等待用户回答
        timeout = 90
        logger.debug(f"⏳ 开始等待用户回答（超时：{timeout}秒）...")
        if self.answer_received.wait(timeout):
            logger.debug(f"📨 收到 answer_received 事件，当前转录: '{self.current_transcript}'")
            if self.current_transcript:
                logger.info(f"\n✅ 已记录回答: {self.current_transcript}")

                # 保存记录
                self.session_recorder.add_answer(
                    question_id=question.id,
                    question_text=question.question,
                    transcript=self.current_transcript,
                )

                # 更新上下文
                self.context.add_qa(question.question, self.current_transcript)

                # 标记问题已问过
                self.question_rag.mark_question_asked(question.id)

                # 检查是否需要追问
                self._check_and_followup(question, self.current_transcript)

                time.sleep(1.0)
                logger.debug(f"🔧 重置状态: waiting_for_answer=False")
                self.waiting_for_answer = False
                return True
            else:
                logger.warning(f"⚠️  未检测到有效回答 (current_transcript='{self.current_transcript}')")
                logger.debug(f"🔧 重置状态: waiting_for_answer=False")
                self.waiting_for_answer = False
                return False
        else:
            logger.warning(f"⏰ 回答超时（{timeout}秒内未收到回答）")
            logger.debug(f"🔧 重置状态: waiting_for_answer=False")
            self.waiting_for_answer = False
            return False

    def _check_and_followup(self, question: Question, answer: str):
        """检查回答并决定是否追问"""
        # 分析回答完整性
        completeness = analyze_answer_completeness(question.question, answer)

        if not completeness['is_complete'] and completeness['confidence'] > 0.6:
            logger.debug(f"\n🤔 检测到回答可能不完整: {completeness['reason']}")

            # 生成追问
            follow_ups = self.question_rag.get_follow_up_questions(
                question, answer, n_results=1
            )

            if follow_ups:
                logger.info(f"🔄 进行追问（不计入问题总数）...")
                self._do_followup(follow_ups[0])

    def _do_followup(self, followup_text: str):
        """执行追问（不计入问题总数）"""
        self.waiting_for_answer = True
        self.current_transcript = ""
        self.answer_received.clear()

        logger.info(f"\n{'─' * 60}")
        logger.info(f"💬 追问（属于当前问题的一部分）")
        logger.info(f"{'─' * 60}")
        logger.info(f"🤖 追问: {followup_text}\n")

        # 确保上一个响应已完成
        if self.is_ai_speaking:
            logger.info(f"⏳ 等待 AI 完成当前响应...")
            self.ai_finished_speaking.wait(timeout=5)
            time.sleep(0.5)

        # 发送追问
        self._send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"用简短、自然的方式追问: {followup_text}",
                        }
                    ],
                },
            }
        )
        self._send_event({"type": "response.create"})

        # 等待 AI 说完
        self.ai_finished_speaking.clear()
        self.ai_finished_speaking.wait(timeout=10)

        # 等待用户回答
        if self.answer_received.wait(60):
            if self.current_transcript:
                logger.info(f"\n✅ 追问回答: {self.current_transcript}")
                # 将追问回答追加到原问题的记录中
                if self.current_question and self.session_recorder:
                    # 更新最后一个回答（Answer 是对象，不是字典）
                    answers = self.session_recorder.answers
                    if answers:
                        answers[
                            -1
                        ].transcript += f" [追问回答: {self.current_transcript}]"

        self.waiting_for_answer = False

    def _complete_interview(self):
        """完成访谈"""
        logger.info(f"\n" + "=" * 60)
        logger.info(f"✅ 访谈已完成！")
        logger.info(f"=" * 60 + "\n")

        completion_msg = "感谢您的配合，健康咨询已完成。祝您身体健康！"
        logger.info(f"🤖 结束语: {completion_msg}\n")

        self._send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"用友好的语气说：{completion_msg}",
                        }
                    ],
                },
            }
        )
        self._send_event({"type": "response.create"})
        time.sleep(3)

        # 保存会话记录
        if self.session_recorder:
            self.session_recorder.save_session(
                {
                    "version": "rag_enhanced",
                    "total_questions_in_db": len(self.question_rag.questions),
                    "questions_asked": self.questions_asked,
                    "answered": self.session_recorder.get_answer_count(),
                }
            )

        logger.info(f"\n📊 访谈统计:")
        logger.info(f"   问题库大小: {len(self.question_rag.questions)}")
        logger.info(f"   主问题数: {self.questions_asked}")
        logger.info(f"   有效回答: {self.session_recorder.get_answer_count()}")

        # 统计追问次数
        followup_count = 0
        if self.session_recorder:
            for answer in self.session_recorder.answers:
                if "[追问回答:" in answer.transcript:
                    followup_count += 1

        if followup_count > 0:
            logger.info(f"   追问次数: {followup_count} (已自动合并到对应问题)")

        logger.info(f"\n💡 说明:")
        logger.info(f"   • 主问题: 从知识库检索的核心问题")
        logger.info(f"   • 追问: 当回答不完整时的补充提问（不单独计数）")

    def _send_loop(self):
        """发送音频数据循环（带重试机制）"""
        error_count = 0
        max_errors = 5

        while self.running:
            try:
                audio_data = self.recorder.get_audio()
                if audio_data:
                    encoded = base64.b64encode(audio_data).decode("ascii")
                    event = {"type": "input_audio_buffer.append", "audio": encoded}
                    self._send_event(event)
                    error_count = 0  # 成功发送，重置错误计数
                else:
                    time.sleep(0.01)
            except Exception as e:
                error_count += 1
                if self.running:
                    logger.error(f"❌ 发送错误 ({error_count}/{max_errors}): {e}")
                    if error_count >= max_errors:
                        logger.error("❌ 发送错误过多，停止发送循环")
                        break
                    time.sleep(0.5)  # 错误后等待一下再重试
                else:
                    break

    def _receive_loop(self):
        """接收响应循环（带重试机制）"""
        error_count = 0
        max_errors = 3
        last_activity = time.time()
        heartbeat_timeout = 30  # 30秒无活动视为超时

        while self.running:
            try:
                # 检查心跳超时
                if time.time() - last_activity > heartbeat_timeout:
                    logger.warning(f"\n⚠️  {heartbeat_timeout}秒无响应，可能连接不稳定")
                    last_activity = time.time()

                message = self.ws.recv()
                if not message:
                    logger.warning("\n⚠️  收到空消息")
                    time.sleep(0.1)
                    continue

                last_activity = time.time()  # 更新活动时间
                error_count = 0  # 成功接收，重置错误计数

                event = json.loads(message)
                event_type = event.get("type")

                if event_type == "session.created":
                    session_id = event.get("session", {}).get("id", "")
                    logger.info(f"✅ 会话已创建 (ID: {session_id[:8]}...)")

                elif event_type == "session.updated":
                    pass

                elif event_type == "input_audio_buffer.speech_started":
                    self.user_speaking = True
                    if self.waiting_for_answer:
                        logger.info(f"🎤 [用户开始回答...]")

                elif event_type == "input_audio_buffer.speech_stopped":
                    self.user_speaking = False
                    logger.info(f" [语音结束]")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "").strip()

                    # 调试信息：记录收到的转录文本
                    logger.debug(f"📝 收到转录: '{transcript}' (长度: {len(transcript)} 字符)")
                    logger.debug(f"   当前状态 - waiting_for_answer: {self.waiting_for_answer}, user_speaking: {self.user_speaking}")

                    # 验证转录文本有效性
                    if not transcript:
                        logger.warning("⚠️  收到空转录文本，忽略")
                        continue

                    # 检查是否太短（可能是误触发）
                    if len(transcript) < 2:
                        logger.warning(f"⚠️  转录文本过短 ({len(transcript)} 字符)，可能是误触发，忽略: '{transcript}'")
                        continue

                    if self.waiting_for_answer:
                        logger.info(f"👤 客户: {transcript}")
                        logger.debug(f"✅ 设置 answer_received 事件")
                        self.current_transcript = transcript
                        self.answer_received.set()
                    else:
                        logger.debug(f"⏭️  当前不在等待回答状态，忽略转录: '{transcript}'")

                elif event_type == "response.created":
                    self.is_ai_speaking = True

                elif event_type == "response.text.delta":
                    text_delta = event.get("delta", "")
                    if text_delta:
                        logger.info(text_delta)

                elif event_type == "response.text.done":
                    logger.info("")

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
                    error_msg = error_data.get("message", "Unknown error")
                    error_type = error_data.get("type", "")
                    logger.error(f"\n❌ API 错误 [{error_type}]: {error_msg}")

                    # 特殊处理某些错误
                    if "ongoing response" in error_msg:
                        logger.info(f"   → 提示: 上一个响应未完成，已自动处理")
                        # 等待一下让响应完成
                        time.sleep(1)

            except WebSocketConnectionClosedException:
                error_count += 1
                logger.error(f"\n❌ WebSocket 连接已关闭 ({error_count}/{max_errors})")
                if error_count >= max_errors or not self.running:
                    self.running = False
                    break
                else:
                    logger.info(f"   → 尝试恢复连接...")
                    time.sleep(2)

            except json.JSONDecodeError as e:
                logger.error(f"\n⚠️  JSON 解析错误: {e}")
                continue

            except Exception as e:
                error_count += 1
                if self.running:
                    logger.error(f"\n❌ 接收错误 ({error_count}/{max_errors}): {e}")
                    if error_count >= max_errors:
                        logger.error("   → 错误过多，停止接收")
                        self.running = False
                        break
                    time.sleep(1)
                else:
                    break

    def stop(self):
        """停止访谈"""
        logger.info(f"\n🛑 正在停止...")
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
        logger.info(f"👋 访谈已结束")


def main():
    """主函数"""
    logger.info(f"\n🚀 客户访谈系统 - RAG 增强版")
    logger.info(f"=" * 60)

    # 检查 API Key
    if API_KEY == "your-api-key-here":
        logger.warning("⚠️  请先设置环境变量 STEPFUN_API_KEY")
        logger.info(f"export STEPFUN_API_KEY='your-actual-api-key'")
        return

    # 检查音频设备
    try:
        audio = pyaudio.PyAudio()
        logger.info(f"🎵 音频设备初始化成功")
        logger.info(f"   输入设备: {audio.get_default_input_device_info()['name']}")
        logger.info(f"   输出设备: {audio.get_default_output_device_info()['name']}")
        audio.terminate()
    except Exception as e:
        logger.error(f"❌ 音频设备初始化失败: {e}")
        return

    # 创建 RAG 增强访谈客户端
    client = RAGInterviewClient(
        API_KEY,
        question_file="questions.yaml",
        model=ModelType.STEP_AUDIO_2.value,
        temperature=0.7,  # 适中的温度，保持灵活性和一致性的平衡
        vad_threshold=0.5,
        vad_silence_duration_ms=700,
        max_questions=10,  # 最多问10个问题
    )

    try:
        client.connect()
        client.start_interview()
    except Exception as e:
        logger.error(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
