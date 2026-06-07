"""Ralph 文件管理器模块 - 负责代码文件的读写操作"""

import os
import shutil
from datetime import datetime


class FileManager:
    """文件管理器 - 将 Builder 输出的代码写入实际文件"""

    def __init__(self, workspace="./workspace", backup=False):
        self.workspace = workspace
        self.backup = backup

    def _resolve_path(self, filepath):
        """将相对路径解析为工作空间下的绝对路径"""
        if os.path.isabs(filepath):
            return filepath
        return os.path.join(self.workspace, filepath)

    def write_file(self, filepath, content):
        """写入文件内容，自动创建父目录，可选备份"""
        full_path = self._resolve_path(filepath)
        # 确保父目录存在
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        # 如果启用备份且文件已存在，创建备份
        if self.backup and os.path.isfile(full_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{full_path}.bak.{timestamp}"
            shutil.copy2(full_path, backup_path)
        # 写入文件
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def read_file(self, filepath):
        """读取文件内容"""
        full_path = self._resolve_path(filepath)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self):
        """列出工作空间内所有文件（相对路径）"""
        files = []
        if not os.path.isdir(self.workspace):
            return files
        for root, dirs, filenames in os.walk(self.workspace):
            for name in filenames:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, self.workspace)
                # 统一使用正斜杠
                files.append(rel.replace("\\", "/"))
        return sorted(files)
