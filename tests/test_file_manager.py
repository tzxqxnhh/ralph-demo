"""FileManager 文件管理器模块测试"""

import os
import tempfile
import pytest


class TestFileManager:
    """FileManager 文件管理器测试套件"""

    @pytest.fixture
    def tmp_workspace(self):
        """创建临时工作空间"""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        # 清理
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.unlink(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)

    def test_write_file_creates_file(self, tmp_workspace):
        """测试写入文件会创建文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        filepath = os.path.join(tmp_workspace, "test_module.py")
        fm.write_file(filepath, "def hello():\n    return 'world'\n")
        assert os.path.isfile(filepath)

    def test_write_file_content_is_correct(self, tmp_workspace):
        """测试写入的文件内容正确"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        filepath = os.path.join(tmp_workspace, "test_module.py")
        content = "def add(a, b):\n    return a + b\n"
        fm.write_file(filepath, content)
        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_write_file_with_relative_path(self, tmp_workspace):
        """测试使用相对路径写入文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        fm.write_file("src/utils.py", "def util():\n    pass\n")
        expected_path = os.path.join(tmp_workspace, "src", "utils.py")
        assert os.path.isfile(expected_path)

    def test_overwrite_existing_file(self, tmp_workspace):
        """测试覆盖已存在的文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        filepath = os.path.join(tmp_workspace, "module.py")
        fm.write_file(filepath, "version = 1\n")
        fm.write_file(filepath, "version = 2\n")
        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == "version = 2\n"

    def test_backup_before_overwrite(self, tmp_workspace):
        """测试覆盖前创建备份文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace, backup=True)
        filepath = os.path.join(tmp_workspace, "module.py")
        fm.write_file(filepath, "original content\n")
        fm.write_file(filepath, "new content\n")
        # 应该存在备份文件
        backup_files = [
            f for f in os.listdir(tmp_workspace)
            if f.startswith("module.py.bak")
        ]
        assert len(backup_files) == 1

    def test_no_backup_by_default(self, tmp_workspace):
        """测试默认不创建备份"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        filepath = os.path.join(tmp_workspace, "module.py")
        fm.write_file(filepath, "original\n")
        fm.write_file(filepath, "new\n")
        backup_files = [
            f for f in os.listdir(tmp_workspace)
            if ".bak" in f
        ]
        assert len(backup_files) == 0

    def test_read_file(self, tmp_workspace):
        """测试读取文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        filepath = os.path.join(tmp_workspace, "readme.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("hello ralph")
        content = fm.read_file(filepath)
        assert content == "hello ralph"

    def test_list_files_in_workspace(self, tmp_workspace):
        """测试列出工作空间文件"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        fm.write_file("a.py", "pass\n")
        fm.write_file("b.py", "pass\n")
        fm.write_file("sub/c.py", "pass\n")
        files = fm.list_files()
        assert "a.py" in files
        assert "b.py" in files
        assert "sub/c.py" in files

    def test_ensure_directory_created(self, tmp_workspace):
        """测试自动创建父目录"""
        from ralph.file_manager import FileManager

        fm = FileManager(workspace=tmp_workspace)
        nested_path = "deep/nested/dir/file.py"
        fm.write_file(nested_path, "# code\n")
        full_path = os.path.join(tmp_workspace, nested_path)
        assert os.path.isfile(full_path)

    def test_default_workspace(self):
        """测试默认工作空间"""
        from ralph.file_manager import FileManager

        fm = FileManager()
        assert fm.workspace == "./workspace"
