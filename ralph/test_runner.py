"""Ralph 测试运行器模块 - 执行自动化测试并返回结果"""

import subprocess
import shlex


class TestRunner:
    """测试运行器 - 运行 pytest/unittest 等测试框架并返回结果"""

    def __init__(self, command="pytest tests/ -v --tb=short", timeout=60,
                 cwd=None):
        self.command = command
        self.timeout = timeout
        self.cwd = cwd

    def run(self):
        """运行测试并返回 (passed: bool, output: str) 元组"""
        try:
            # 支持字符串命令和列表命令两种形式
            if isinstance(self.command, list):
                args = self.command
            else:
                args = shlex.split(self.command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                cwd=self.cwd,
            )
            output = result.stdout + result.stderr
            passed = result.returncode == 0
            return (passed, output)
        except subprocess.TimeoutExpired:
            return (False, "测试超时：执行时间超过限制")
        except FileNotFoundError as e:
            return (False, f"测试命令未找到: {e}")
        except Exception as e:
            return (False, f"测试执行异常: {e}")
