"""Orchestrator 主控制器模块测试"""

import os
import tempfile
import pytest


class MockLLMAdapter:
    """模拟 LLM 适配器"""
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
    """模拟测试运行器，始终返回通过"""
    def __init__(self, always_pass=True):
        self.always_pass = always_pass
        self.run_count = 0

    def run(self):
        self.run_count += 1
        if self.always_pass:
            return (True, "所有测试通过")
        return (False, "测试失败: assertion error")


class TestOrchestrator:
    """Orchestrator 主控制器测试套件"""

    @pytest.fixture
    def tmp_workspace(self):
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                try:
                    os.unlink(os.path.join(root, name))
                except PermissionError:
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

    def _make_config(self, workspace, max_iterations=5):
        """辅助：创建测试用配置"""
        from ralph.config import Config
        return Config(
            max_iterations=max_iterations,
            project_root=workspace,
            scratchpad_path=os.path.join(workspace, "ralph_scratchpad.md"),
            test_command="pytest tests/ -v --tb=short",
        )

    def test_orchestrator_initialization(self, tmp_workspace):
        """测试 Orchestrator 初始化"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace)
        orch = Orchestrator(config)
        assert orch.config == config
        assert orch.iteration == 0

    def test_orchestrator_has_max_iterations_safety_valve(self, tmp_workspace):
        """测试 max_iterations 作为安全阀"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=3)
        orch = Orchestrator(config)
        assert orch.config.max_iterations == 3

    def test_run_with_mocked_hats_completes(self, tmp_workspace):
        """测试使用模拟帽子完成完整循环"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        # 创建模拟 LLM 响应序列
        mock_llm = MockLLMAdapter(responses=[
            # Planner
            "任务计划：\n1. 创建 calc.py\n2. 实现 add/sub/mul/div\n验收标准：测试通过",
            # Builder
            "文件: calc.py\n```python\nclass Calc:\n    def add(self,a,b):return a+b\n```",
            # Critic
            "审查结果: PASSED\n代码简洁正确。",
            # Finalizer
            "LOOP_COMPLETE\n任务已完成。",
        ])

        from ralph.hats import Planner, Builder, Critic, Finalizer
        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm,
            file_manager=orch.file_manager,
        ))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        result = orch.run("实现计算器")
        assert result is not None
        assert result["iterations"] == 1

    def test_run_creates_scratchpad(self, tmp_workspace):
        """测试运行后创建了便签本文件"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        mock_llm = MockLLMAdapter(responses=[
            "计划: 创建 hello.py\n验收标准: 运行成功",
            "文件: hello.py\n```python\nprint('hello')\n```",
            "审查结果: PASSED",
            "LOOP_COMPLETE",
        ])

        from ralph.hats import Planner, Builder, Critic, Finalizer
        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        orch.run("创建 hello 程序")

        assert os.path.isfile(config.scratchpad_path)

    def test_run_records_iterations(self, tmp_workspace):
        """测试运行后迭代计数正确"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=10)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        mock_llm = MockLLMAdapter(responses=[
            "计划内容",
            "文件: a.py\n```python\nx=1\n```",
            "审查结果: PASSED",
            "LOOP_COMPLETE",
        ])

        from ralph.hats import Planner, Builder, Critic, Finalizer
        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        orch.run("任务")

        assert orch.iteration >= 1

    def test_max_iterations_prevents_infinite_loop(self, tmp_workspace):
        """测试 max_iterations 防止无限循环"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=2)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, test_runner=mock_runner)

        # Finalizer 始终要求继续，永不给出 LOOP_COMPLETE
        mock_llm = MockLLMAdapter(responses=[
            "计划A", "文件: a.py\n```python\nx=1\n```", "审查结果: PASSED",
            "需要继续：还有任务未完成。",
            "计划B", "文件: b.py\n```python\ny=2\n```", "审查结果: PASSED",
            "需要继续：还有任务未完成。",
        ])

        from ralph.hats import Planner, Builder, Critic, Finalizer
        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        orch.run("任务")
        assert orch.iteration <= config.max_iterations

    def test_hat_retry_on_failure(self, tmp_workspace):
        """测试帽子调用失败时的重试机制"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, max_hat_retries=3, test_runner=mock_runner)

        # 前两次 Planner 失败，第三次成功
        call_count = [0]

        class FailingThenSuccessPlanner:
            """先失败几次然后成功的 Planner"""
            def __init__(self):
                self.llm = None
            def run(self, context):
                call_count[0] += 1
                if call_count[0] < 3:
                    raise RuntimeError("临时错误")
                return "恢复后的计划"

        orch.register_hat("planner", FailingThenSuccessPlanner())

        mock_llm = MockLLMAdapter(responses=[
            "文件: x.py\n```python\nx=1\n```",
            "审查结果: PASSED",
            "LOOP_COMPLETE",
        ])
        from ralph.hats import Builder, Critic, Finalizer
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        orch.run("任务")
        assert call_count[0] >= 2

    def test_orchestrator_logs_activity(self, tmp_workspace):
        """测试 Orchestrator 记录活动日志"""
        from ralph.orchestrator import Orchestrator

        log_path = os.path.join(tmp_workspace, "test_ralph.log")
        config = self._make_config(tmp_workspace, max_iterations=4)
        mock_runner = MockTestRunner(always_pass=True)
        orch = Orchestrator(config, log_path=log_path, test_runner=mock_runner)

        mock_llm = MockLLMAdapter(responses=[
            "计划", "文件: a.py\n```python\nx=1\n```", "审查结果: PASSED",
            "LOOP_COMPLETE",
        ])

        from ralph.hats import Planner, Builder, Critic, Finalizer
        orch.register_hat("planner", Planner(llm_adapter=mock_llm))
        orch.register_hat("builder", Builder(
            llm_adapter=mock_llm, file_manager=orch.file_manager))
        orch.register_hat("critic", Critic(llm_adapter=mock_llm))
        orch.register_hat("finalizer", Finalizer(llm_adapter=mock_llm))

        orch.run("任务")
        assert os.path.isfile(log_path)
        orch.close()
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        assert len(log_content) > 0

    def test_register_and_get_hat(self, tmp_workspace):
        """测试注册和获取帽子实例"""
        from ralph.orchestrator import Orchestrator

        config = self._make_config(tmp_workspace)
        orch = Orchestrator(config)

        mock_llm = MockLLMAdapter()
        from ralph.hats import Planner
        planner = Planner(llm_adapter=mock_llm)

        orch.register_hat("planner", planner)
        assert orch.get_hat("planner") == planner
        assert orch.get_hat("nonexistent") is None
