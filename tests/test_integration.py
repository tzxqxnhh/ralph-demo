"""Ralph 集成测试 - 端到端验证 Ralph Loop 完整流程"""

import os
import tempfile
import pytest


class MockLLMAdapter:
    """模拟 LLM 适配器，返回预设响应序列"""
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_history = []
        self._idx = 0

    def chat(self, prompt):
        self.call_history.append(prompt)
        if self._idx < len(self.responses):
            resp = self.responses[self._idx]
            self._idx += 1
            return resp
        return "默认响应"


class MockTestRunner:
    """模拟测试运行器"""
    def __init__(self, always_pass=True):
        self.always_pass = always_pass
        self.run_count = 0

    def run(self):
        self.run_count += 1
        if self.always_pass:
            return (True, "所有测试通过")
        return (False, "测试失败: assertion error")


class TestRalphIntegration:
    """Ralph 集成测试套件"""

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

    def _create_config(self, tmp_workspace, max_iterations=5):
        """创建测试配置"""
        from ralph.config import Config
        return Config(
            max_iterations=max_iterations,
            project_root=tmp_workspace,
            scratchpad_path=os.path.join(tmp_workspace, "ralph_scratchpad.md"),
            test_command="pytest tests/ -v --tb=short",
        )

    def test_full_loop_single_iteration_success(self, tmp_workspace):
        """测试完整 Ralph Loop 单轮成功场景

        场景: 用户要求实现一个简单的加法函数
        流程: Planner -> Builder -> 测试通过 -> Critic PASSED -> Finalizer LOOP_COMPLETE
        """
        from ralph.orchestrator import Orchestrator
        from ralph.hats import Planner, Builder, Critic, Finalizer

        config = self._create_config(tmp_workspace)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        # 预设 LLM 响应序列
        mock_llm = MockLLMAdapter(responses=[
            # Planner: 生成任务计划
            "任务计划：\n"
            "1. 创建 src/calculator.py，实现 Calculator 类\n"
            "2. 实现 add(a, b) 方法\n"
            "3. 编写单元测试\n"
            "验收标准：\n"
            "- 所有单元测试通过\n"
            "- add(1, 2) 返回 3\n"
            "- add(-1, 1) 返回 0",

            # Builder: 生成代码
            "文件: src/calculator.py\n"
            "```python\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n"
            "```",

            # Critic: 审查通过
            "审查结果: PASSED\n"
            "代码质量良好：\n"
            "1. 类结构清晰\n"
            "2. add 方法实现正确\n"
            "3. 代码简洁易读",

            # Finalizer: 任务完成
            "LOOP_COMPLETE\n"
            "所有任务已完成：\n"
            "- 计划已执行\n"
            "- 代码已生成\n"
            "- 测试已通过\n"
            "- 审查已通过",
        ])

        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        result = orch.run("实现一个 Calculator 类，支持加法运算")

        # 验证结果
        assert result["iterations"] == 1
        assert not result["max_iterations_reached"]

        # 验证便签本记录了所有阶段
        scratchpad_content = result["scratchpad"]
        assert "Planner" in scratchpad_content
        assert "Builder" in scratchpad_content
        assert "Critic" in scratchpad_content
        assert "Finalizer" in scratchpad_content
        assert "LOOP_COMPLETE" in scratchpad_content

        # 验证文件已创建
        assert os.path.isfile(os.path.join(tmp_workspace, "src", "calculator.py"))

        orch.close()

    def test_full_loop_critic_failed_then_retry(self, tmp_workspace):
        """测试 Critic 失败后重新规划的完整场景

        场景: 第一次 Critic 发现问题，第二轮改进后通过
        """
        from ralph.orchestrator import Orchestrator
        from ralph.hats import Planner, Builder, Critic, Finalizer

        config = self._create_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        mock_llm = MockLLMAdapter(responses=[
            # 第1轮 Planner
            "计划: 创建 math_utils.py，实现 divide 函数",
            # 第1轮 Builder
            "文件: math_utils.py\n```python\ndef divide(a, b):\n    return a / b\n```",
            # 第1轮 Critic: FAILED - 发现除零问题
            "审查结果: FAILED\n"
            "问题：\n"
            "1. 未处理除零异常\n"
            "建议：添加 ZeroDivisionError 处理",
            # 第1轮 Finalizer: 需要继续
            "需要继续：Critic 审查未通过，需要修复除零问题。",
            # 第2轮 Planner: 根据 Critic 反馈重新规划
            "修复计划: 在 math_utils.py 中添加除零异常处理",
            # 第2轮 Builder: 修复代码
            "文件: math_utils.py\n```python\n"
            "def divide(a, b):\n"
            "    if b == 0:\n"
            "        raise ValueError('除数不能为零')\n"
            "    return a / b\n"
            "```",
            # 第2轮 Critic: PASSED
            "审查结果: PASSED\n修复后代码正确处理了除零情况。",
            # 第2轮 Finalizer: LOOP_COMPLETE
            "LOOP_COMPLETE\n所有问题已修复。",
        ])

        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        result = orch.run("实现一个安全的除法函数")

        assert result["iterations"] == 2
        assert "FAILED" in result["scratchpad"]
        assert "LOOP_COMPLETE" in result["scratchpad"]

        orch.close()

    def test_scenario_calculator_with_four_operations(self, tmp_workspace):
        """测试计算器四则运算完整场景"""
        from ralph.orchestrator import Orchestrator
        from ralph.hats import Planner, Builder, Critic, Finalizer

        config = self._create_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        mock_llm = MockLLMAdapter(responses=[
            # Planner
            "任务计划：\n"
            "1. 创建 calc.py，实现 Calc 类\n"
            "2. 实现 add(sub(mul(div 四个方法\n"
            "3. 编写测试\n"
            "验收标准：四则运算正确，测试通过",

            # Builder
            "文件: calc.py\n"
            "```python\n"
            "class Calc:\n"
            "    def add(self, a, b): return a + b\n"
            "    def sub(self, a, b): return a - b\n"
            "    def mul(self, a, b): return a * b\n"
            "    def div(self, a, b):\n"
            "        if b == 0: raise ValueError('除零')\n"
            "        return a / b\n"
            "```",

            # Critic
            "审查结果: PASSED\n所有方法实现正确，边界处理完善。",

            # Finalizer
            "LOOP_COMPLETE\n计算器四则运算已完整实现。",
        ])

        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        result = orch.run("实现计算器类，支持加减乘除四则运算")

        assert result["iterations"] == 1
        assert os.path.isfile(os.path.join(tmp_workspace, "calc.py"))

        # 验证生成的文件内容包含四个方法
        with open(os.path.join(tmp_workspace, "calc.py"), "r", encoding="utf-8") as f:
            code = f.read()
        assert "add" in code
        assert "sub" in code
        assert "mul" in code
        assert "div" in code

        orch.close()

    def test_max_iterations_safety_valve(self, tmp_workspace):
        """测试 max_iterations 安全阀终止无限循环"""
        from ralph.orchestrator import Orchestrator
        from ralph.hats import Planner, Builder, Critic, Finalizer

        config = self._create_config(tmp_workspace, max_iterations=3)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        # 生成大量响应确保不会耗尽
        responses = []
        for i in range(10):
            responses.extend([
                f"计划第{i+1}轮",
                f"文件: file_{i+1}.py\n```python\nx={i+1}\n```",
                "审查结果: PASSED",
                "需要继续：还有更多功能要实现。",
            ])

        mock_llm = MockLLMAdapter(responses=responses)

        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        result = orch.run("实现无限功能列表")
        # 不应超过 max_iterations
        assert result["iterations"] <= 3
        assert result["max_iterations_reached"]

        orch.close()
