"""CLI 命令行接口模块测试"""

import os
import tempfile
import pytest
from click.testing import CliRunner


class TestCLI:
    """CLI 命令行接口测试套件"""

    @pytest.fixture
    def runner(self):
        """Click CLI 测试运行器"""
        return CliRunner()

    @pytest.fixture
    def tmp_workspace(self):
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                try:
                    os.unlink(os.path.join(root, name))
                except (PermissionError, OSError):
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    def test_cli_main_entry_point(self, runner):
        """测试 CLI 主入口点存在"""
        from ralph.cli import main
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "ralph" in result.output.lower()

    def test_run_command_accepts_argument(self, runner):
        """测试 run 命令接收参数"""
        from ralph.cli import main
        result = runner.invoke(
            main, ["run", "--help"]
        )
        assert result.exit_code == 0
        # run 命令应该接受任务描述参数
        assert "task" in result.output.lower() or "TASK" in result.output

    def test_status_command(self, runner, tmp_workspace):
        """测试 status 命令显示状态"""
        from ralph.cli import main

        # 先创建一个便签本以便有状态可显示
        scratchpad_path = os.path.join(tmp_workspace, "ralph_scratchpad.md")
        with open(scratchpad_path, "w", encoding="utf-8") as f:
            f.write("# Ralph Scratchpad\n\n## Planner - 2024-01-01\n\n测试计划\n")

        result = runner.invoke(
            main, ["status", "--scratchpad", scratchpad_path]
        )
        assert result.exit_code == 0
        # 应该显示迭代信息
        assert "Planner" in result.output or "迭代" in result.output or "状态" in result.output

    def test_clean_command(self, runner, tmp_workspace):
        """测试 clean 命令清除便签本"""
        from ralph.cli import main

        scratchpad_path = os.path.join(tmp_workspace, "ralph_scratchpad.md")
        with open(scratchpad_path, "w", encoding="utf-8") as f:
            f.write("一些内容")

        result = runner.invoke(
            main, ["clean", "--scratchpad", scratchpad_path],
            input="y\n",
        )
        assert result.exit_code == 0
        # 便签本内容应该被清除
        with open(scratchpad_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.strip() == ""

    def test_clean_command_asks_confirmation(self, runner, tmp_workspace):
        """测试 clean 命令请求确认"""
        from ralph.cli import main

        scratchpad_path = os.path.join(tmp_workspace, "ralph_scratchpad.md")
        with open(scratchpad_path, "w", encoding="utf-8") as f:
            f.write("重要内容")

        # 拒绝确认
        result = runner.invoke(
            main,
            ["clean", "--scratchpad", scratchpad_path],
            input="n\n",
        )
        # 内容应该保留
        with open(scratchpad_path, "r", encoding="utf-8") as f:
            assert "重要内容" in f.read()

    def test_resume_command_needs_scratchpad(self, runner, tmp_workspace):
        """测试 resume 命令需要便签本存在"""
        from ralph.cli import main

        scratchpad_path = os.path.join(tmp_workspace, "nonexistent.md")
        result = runner.invoke(
            main, ["resume", "--scratchpad", scratchpad_path]
        )
        # 便签本不存在时应该报错
        assert result.exit_code != 0 or "不存在" in result.output or "未找到" in result.output

    def test_version_option(self, runner):
        """测试 --version 选项"""
        from ralph.cli import main
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
