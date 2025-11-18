"""
问题管理模块
负责加载、管理和保存问题列表
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class Question:
    """问题数据类"""
    id: int
    question: str
    type: str  # open, yesno, choice
    
    def __str__(self):
        return f"问题 {self.id}: {self.question}"


@dataclass
class Answer:
    """回答数据类"""
    question_id: int
    question_text: str
    transcript: str  # 语音转写文本
    timestamp: str
    audio_file: Optional[str] = None  # 音频文件路径（如果保存）
    
    def to_dict(self):
        return asdict(self)


class QuestionManager:
    """问题管理器"""
    
    def __init__(self, config_file: str = "questions.yaml"):
        self.config_file = Path(config_file)
        self.questions: List[Question] = []
        self.settings: Dict[str, Any] = {}
        self.current_index = 0
        
    def load_questions(self) -> bool:
        """从 YAML 文件加载问题"""
        try:
            if not self.config_file.exists():
                print(f"❌ 配置文件不存在: {self.config_file}")
                return False
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 加载问题列表
            questions_data = config.get('questions', [])
            self.questions = [
                Question(
                    id=q['id'],
                    question=q['question'],
                    type=q.get('type', 'open')
                )
                for q in questions_data
            ]
            
            # 加载设置
            self.settings = config.get('settings', {})
            
            print(f"✅ 成功加载 {len(self.questions)} 个问题")
            return True
            
        except Exception as e:
            print(f"❌ 加载问题配置失败: {e}")
            return False
    
    def get_welcome_message(self) -> str:
        """获取欢迎语"""
        return self.settings.get(
            'welcome_message',
            "您好！欢迎参与访谈。"
        )
    
    def get_completion_message(self) -> str:
        """获取结束语"""
        return self.settings.get(
            'completion_message',
            "感谢您的参与！"
        )
    
    def has_next_question(self) -> bool:
        """是否还有下一个问题"""
        return self.current_index < len(self.questions)
    
    def get_next_question(self) -> Optional[Question]:
        """获取下一个问题"""
        if self.has_next_question():
            question = self.questions[self.current_index]
            self.current_index += 1
            return question
        return None
    
    def get_current_progress(self) -> str:
        """获取当前进度"""
        return f"{self.current_index}/{len(self.questions)}"
    
    def reset(self):
        """重置进度"""
        self.current_index = 0
    
    def should_save_audio(self) -> bool:
        """是否保存音频"""
        return self.settings.get('save_audio', False)
    
    def should_save_transcript(self) -> bool:
        """是否保存转写文本"""
        return self.settings.get('save_transcript', True)


class SessionRecorder:
    """会话记录器"""
    
    def __init__(self, session_id: Optional[str] = None):
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session_id = session_id
        self.answers: List[Answer] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        # 创建会话目录
        self.session_dir = Path("sessions") / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 会话目录: {self.session_dir}")
    
    def add_answer(
        self,
        question_id: int,
        question_text: str,
        transcript: str,
        audio_data: Optional[bytes] = None
    ) -> Answer:
        """添加一个回答"""
        timestamp = datetime.now().isoformat()
        audio_file = None
        
        # 保存音频文件（如果提供）
        if audio_data:
            audio_file = f"answer_{question_id}.wav"
            audio_path = self.session_dir / audio_file
            # 注意：这里需要实际的音频保存逻辑
            # 暂时先记录文件名
        
        answer = Answer(
            question_id=question_id,
            question_text=question_text,
            transcript=transcript,
            timestamp=timestamp,
            audio_file=audio_file
        )
        
        self.answers.append(answer)
        return answer
    
    def save_session(self, additional_info: Optional[Dict[str, Any]] = None):
        """保存会话记录到 JSON 文件"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        session_data = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration,
            "total_questions": len(self.answers),
            "answers": [answer.to_dict() for answer in self.answers]
        }
        
        if additional_info:
            session_data["additional_info"] = additional_info
        
        # 保存为 JSON
        json_file = self.session_dir / "session.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 会话记录已保存: {json_file}")
        
        # 同时保存为易读的文本格式
        self._save_text_summary()
    
    def _save_text_summary(self):
        """保存文本摘要"""
        text_file = self.session_dir / "summary.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"客户访谈记录\n")
            f.write(f"会话ID: {self.session_id}\n")
            f.write(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if self.end_time:
                f.write(f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                duration = (self.end_time - self.start_time).total_seconds()
                f.write(f"总时长: {duration:.0f} 秒\n")
            f.write("=" * 60 + "\n\n")
            
            for i, answer in enumerate(self.answers, 1):
                f.write(f"\n【问题 {i}】\n")
                f.write(f"{answer.question_text}\n\n")
                f.write(f"【回答】\n")
                f.write(f"{answer.transcript}\n")
                f.write(f"\n{'-' * 60}\n")
        
        print(f"📄 文本摘要已保存: {text_file}")
    
    def get_answer_count(self) -> int:
        """获取已回答的问题数"""
        return len(self.answers)


def main():
    """测试函数"""
    # 测试问题管理器
    manager = QuestionManager("questions.yaml")
    
    if manager.load_questions():
        print(f"\n欢迎语: {manager.get_welcome_message()}")
        print(f"问题总数: {len(manager.questions)}\n")
        
        # 显示所有问题
        for q in manager.questions:
            print(f"  {q}")
        
        print(f"\n结束语: {manager.get_completion_message()}")
        
        # 测试会话记录器
        print("\n" + "=" * 60)
        recorder = SessionRecorder()
        
        # 添加测试回答
        recorder.add_answer(1, "请问您贵姓？", "我姓张")
        recorder.add_answer(2, "使用多久了？", "大概三个月")
        
        # 保存会话
        recorder.save_session()


if __name__ == "__main__":
    main()

