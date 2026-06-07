"""TestRunner 测试运行器模块测试"""

import os
import tempfile
import pytest


class TestTestRunner:
    """TestRunner 测试运行器测试套件"""

    @pytest.fixture
    def tmp_workspace(self):
        """创建包含测试文件的临时工作空间"""
        tmpdir = tempfile.mkdtemp()
        # 创建 tests 目录
        tests_dir = os.path.join(tmpdir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        # 创建 __init__.py
        with open(os.path.join(tests_dir, "__init__.py"), "w") as f:
            f.write("")
        # 创建 conftest.py 覆盖项目级配置，避免 pyproject.toml 干扰
        conftest = os.path.join(tmpdir, "conftest.py")
        with open(conftest, "w") as f:
            f.write("")
        yield tmpdir
        # 清理
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.unlink(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)

    def write_test_file(self, tests_dir, name, content):
        """辅助：写入测试文件"""
        filepath = os.path.join(tests_dir, name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def test_run_passing_tests(self, tmp_workspace):
        """测试运行通过的测试用例"""
        from ralph.test_runner import TestRunner

        tests_dir = os.path.join(tmp_workspace, "tests")
        self.write_test_file(
            tests_dir,
            "test_passing.py",
            "def test_always_pass():\n    assert True\n",
        )
        runner = TestRunner(
            command=["pytest", tests_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
        )
        passed, output = runner.run()
        assert passed is True
        assert "PASSED" in output or "passed" in output

    def test_run_failing_tests(self, tmp_workspace):
        """测试运行失败的测试用例"""
        from ralph.test_runner import TestRunner

        tests_dir = os.path.join(tmp_workspace, "tests")
        self.write_test_file(
            tests_dir,
            "test_failing.py",
            "def test_always_fail():\n    assert False, 'expected failure'\n",
        )
        runner = TestRunner(
            command=["pytest", tests_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
        )
        passed, output = runner.run()
        assert passed is False
        assert "FAILED" in output or "failed" in output

    def test_run_with_default_command(self):
        """测试使用默认命令"""
        from ralph.test_runner import TestRunner

        runner = TestRunner()
        assert runner.command == "pytest tests/ -v --tb=short"

    def test_output_contains_traceback_on_failure(self, tmp_workspace):
        """测试失败时输出包含 traceback 信息"""
        from ralph.test_runner import TestRunner

        tests_dir = os.path.join(tmp_workspace, "tests")
        self.write_test_file(
            tests_dir,
            "test_error.py",
            "def test_with_traceback():\n"
            "    x = 1 / 0\n"
            "    assert True\n",
        )
        runner = TestRunner(
            command=["pytest", tests_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
        )
        passed, output = runner.run()
        assert passed is False
        # 输出应包含错误信息
        assert "ZeroDivisionError" in output or "Error" in output or "error" in output.lower()

    def test_timeout_handling(self, tmp_workspace):
        """测试超时处理"""
        from ralph.test_runner import TestRunner

        tests_dir = os.path.join(tmp_workspace, "tests")
        self.write_test_file(
            tests_dir,
            "test_slow.py",
            "import time\n"
            "def test_slow():\n"
            "    time.sleep(10)\n"
            "    assert True\n",
        )
        runner = TestRunner(
            command=["pytest", tests_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
            timeout=2,
        )
        passed, output = runner.run()
        # 超时应返回失败
        assert passed is False

    def test_return_type_is_tuple(self, tmp_workspace):
        """测试返回值是 (bool, str) 元组"""
        from ralph.test_runner import TestRunner

        tests_dir = os.path.join(tmp_workspace, "tests")
        runner = TestRunner(
            command=["pytest", tests_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
        )
        result = runner.run()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_no_tests_found(self, tmp_workspace):
        """测试没有发现测试文件的情况"""
        from ralph.test_runner import TestRunner

        # 使用空目录（无测试文件）
        empty_dir = os.path.join(tmp_workspace, "empty_tests")
        os.makedirs(empty_dir, exist_ok=True)
        runner = TestRunner(
            command=["pytest", empty_dir, "-v", "--tb=short", "--rootdir", tmp_workspace],
        )
        passed, output = runner.run()
        # pytest 在没有测试时会返回非零退出码
        # 我们只需要确认返回了结果
        assert isinstance(passed, bool)
        assert isinstance(output, str)
