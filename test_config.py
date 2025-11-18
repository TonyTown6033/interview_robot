#!/usr/bin/env python3
"""
配置测试脚本
用于验证环境配置是否正确
"""

import os
import sys
from pathlib import Path


def test_api_key():
    """测试 API Key"""
    print("1️⃣  测试 API Key...")
    api_key = os.getenv("STEPFUN_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("   ❌ 未设置 STEPFUN_API_KEY")
        print("   请运行: export STEPFUN_API_KEY='your-key'")
        return False
    else:
        print(f"   ✅ API Key 已设置: {api_key[:10]}...{api_key[-4:]}")
        return True


def test_dependencies():
    """测试依赖包"""
    print("\n2️⃣  测试依赖包...")
    required = [
        "websocket",
        "yaml",
        "pyaudio",
        "numpy",
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n   缺少依赖: {', '.join(missing)}")
        print("   请运行: uv sync")
        return False
    return True


def test_audio_device():
    """测试音频设备"""
    print("\n3️⃣  测试音频设备...")
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # 测试输入设备
        try:
            input_info = audio.get_default_input_device_info()
            print(f"   ✅ 输入设备: {input_info['name']}")
        except Exception as e:
            print(f"   ❌ 无法检测输入设备: {e}")
            return False
        
        # 测试输出设备
        try:
            output_info = audio.get_default_output_device_info()
            print(f"   ✅ 输出设备: {output_info['name']}")
        except Exception as e:
            print(f"   ❌ 无法检测输出设备: {e}")
            return False
        
        audio.terminate()
        return True
        
    except Exception as e:
        print(f"   ❌ PyAudio 错误: {e}")
        return False


def test_question_file():
    """测试问题配置文件"""
    print("\n4️⃣  测试问题配置文件...")
    
    question_file = Path("questions.yaml")
    if not question_file.exists():
        print(f"   ❌ 找不到 questions.yaml")
        return False
    
    try:
        import yaml
        with open(question_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        questions = config.get('questions', [])
        settings = config.get('settings', {})
        
        print(f"   ✅ 配置文件格式正确")
        print(f"   ✅ 问题数量: {len(questions)}")
        print(f"   ✅ 欢迎语: {settings.get('welcome_message', 'N/A')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ YAML 解析错误: {e}")
        return False


def test_modules():
    """测试项目模块"""
    print("\n5️⃣  测试项目模块...")
    
    try:
        from question_manager import QuestionManager, SessionRecorder
        print("   ✅ question_manager 模块")
        
        # 测试加载问题
        manager = QuestionManager("questions.yaml")
        if manager.load_questions():
            print(f"   ✅ 成功加载 {len(manager.questions)} 个问题")
        else:
            print("   ❌ 加载问题失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 模块导入错误: {e}")
        return False


def test_directories():
    """测试目录结构"""
    print("\n6️⃣  测试目录结构...")
    
    required_files = [
        "interview_client.py",
        "question_manager.py",
        "questions.yaml",
        "README.md",
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
            all_exist = False
    
    # 检查示例目录
    examples_dir = Path("examples")
    if examples_dir.exists() and examples_dir.is_dir():
        examples = list(examples_dir.glob("*.yaml"))
        print(f"   ✅ 示例模板: {len(examples)} 个")
    else:
        print("   ❌ examples 目录")
        all_exist = False
    
    return all_exist


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 QuestionAgent 配置测试")
    print("=" * 60)
    
    tests = [
        test_api_key,
        test_dependencies,
        test_audio_device,
        test_question_file,
        test_modules,
        test_directories,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ⚠️  测试异常: {e}")
            results.append(False)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("\n✅ 所有测试通过！可以开始使用了。")
        print("\n快速开始:")
        print("  uv run python interview_client.py")
        return 0
    else:
        print("\n❌ 部分测试失败，请先解决上述问题。")
        print("\n参考文档:")
        print("  - QUICKSTART.md")
        print("  - README.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())

