#!/usr/bin/env python3
"""
将 print 语句转换为 logging 的脚本
"""

import re
from pathlib import Path


def convert_print_to_logger(file_path: str):
    """转换文件中的 print 语句为 logger"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定义不同级别的映射规则
    patterns = [
        # ERROR 级别 - 包含 ❌ 或 ERROR
        (r'print\(f?"(.*?❌.*?)"\)', r'logger.error("\1")'),
        (r'print\(f?"(.*?错误.*?)"\)', r'logger.error("\1")'),
        (r'print\(f?"(.*?失败.*?)"\)', r'logger.error("\1")'),

        # WARNING 级别 - 包含 ⚠️ 或 WARNING
        (r'print\(f?"(.*?⚠️.*?)"\)', r'logger.warning("\1")'),
        (r'print\(f?"(.*?警告.*?)"\)', r'logger.warning("\1")'),
        (r'print\(f?"(.*?超时.*?)"\)', r'logger.warning("\1")'),

        # DEBUG 级别 - 包含调试信息
        (r'print\(f?"(.*?调试.*?)"\)', r'logger.debug("\1")'),
        (r'print\(f?"(.*?DEBUG.*?)"\)', r'logger.debug("\1")'),
        (r'print\(f?"(.*?检测到.*?)"\)', r'logger.debug("\1")'),

        # INFO 级别 - 其他所有
        (r'print\(f?"', r'logger.info(f"'),
        (r"print\(f'", r"logger.info(f'"),
    ]

    # 应用转换
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    # 特殊处理：print() 空行
    content = re.sub(r'\bprint\(\)', 'logger.info("")', content)

    # 特殊处理：print(..., end="", flush=True)
    content = re.sub(
        r'print\((.*?), end="", flush=True\)',
        r'logger.info(\1)',
        content
    )
    content = re.sub(
        r'print\((.*?), end=""\)',
        r'logger.info(\1)',
        content
    )

    # 保存
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已转换: {file_path}")


def main():
    """主函数"""
    file_path = "src/clients/interview_client_rag.py"

    print(f"🔄 开始转换 {file_path}...")
    convert_print_to_logger(file_path)
    print("✅ 转换完成！")
    print("\n💡 提示:")
    print("   - ERROR: ❌ 错误 失败")
    print("   - WARNING: ⚠️ 警告 超时")
    print("   - INFO: 其他普通信息")
    print("   - DEBUG: 调试信息")


if __name__ == "__main__":
    main()
