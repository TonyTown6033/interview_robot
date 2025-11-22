#!/usr/bin/env python3
"""
客户访谈系统 - 主入口
混合模式：TTS生成问题 + Realtime API接收回答
"""

import os
import sys
import pyaudio
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.clients.interview_client_hybrid import HybridInterviewClient, ModelType

# 配置信息
API_KEY = os.getenv("STEPFUN_API_KEY", "your-api-key-here")


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
        tts_voice="cixingnansheng",  # 音色选项见下方注释
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
