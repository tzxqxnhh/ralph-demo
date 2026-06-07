"""Ralph 便签本模块 - 管理跨步骤持久化上下文"""

import os
import re
from datetime import datetime


class Scratchpad:
    """便签本 - 通过 Markdown 文件在帽子间传递上下文"""

    def __init__(self, path="ralph_scratchpad.md"):
        self.path = path
        if not os.path.isfile(self.path):
            self._create_empty()

    def _create_empty(self):
        """创建空便签本"""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("# Ralph Scratchpad\n\n")

    def read(self):
        """读取完整便签本内容"""
        if not os.path.isfile(self.path):
            return ""
        with open(self.path, "r", encoding="utf-8") as f:
            return f.read()

    def append_section(self, hat_name, content):
        """追加一个新章节，带时间戳和帽子名称"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        section = (
            f"\n## {hat_name} - {timestamp}\n\n{content}\n"
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(section)

    def set_requirements(self, requirements):
        """写入初始需求"""
        self.append_section("原始需求", requirements)

    def get_last_section(self):
        """获取最后一个章节的内容"""
        content = self.read()
        # 按 ## 分割章节
        sections = re.split(r'\n(?=## )', content)
        # 过滤掉标题行
        real_sections = [
            s for s in sections if s.startswith("## ")
        ]
        if not real_sections:
            return None
        return real_sections[-1].strip()

    def clear(self):
        """清空便签本内容"""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("")
