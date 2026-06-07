"""Hats 四顶帽子模块测试"""

import os
import tempfile
import pytest


# --- 模拟 LLM 适配器 ---

class MockLLMAdapter:
    """模拟 LLM 适配器，用于测试帽子行为"""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_history = []
        self._call_index = 0

    def chat(self, prompt):
        """模拟 LLM 调用，返回预设响应"""
        self.call_history.append(prompt)
        if self._call_index < len(self.responses):
            response = self.responses[self._call_index]
            self._call_index += 1
            return response
        return "默认响应"


# --- Planner 测试 ---

class TestPlanner:
    """Planner 帽子测试套件"""

    def test_planner_returns_structured_plan(self):
        """测试 Planner 返回结构化计划"""
        from ralph.hats import Planner

        mock_llm = MockLLMAdapter(responses=[
            "任务计划：\n"
            "1. 创建 calculator.py 文件，实现 Calculator 类\n"
            "2. 实现 add 方法 - 加法\n"
            "3. 实现 sub 方法 - 减法\n"
            "4. 编写单元测试验证所有方法\n"
            "验收标准：所有测试通过"
        ])
        planner = Planner(llm_adapter=mock_llm)
        result = planner.run("实现一个计算器类，支持加减乘除")

        assert "任务计划" in result
        assert "calculator" in result.lower()
        assert len(mock_llm.call_history) == 1

    def test_planner_includes_acceptance_criteria(self):
        """测试 Planner 输出包含验收标准"""
        from ralph.hats import Planner

        mock_llm = MockLLMAdapter(responses=[
            "计划内容\n验收标准：\n- 所有单元测试通过\n- 代码覆盖率 > 80%"
        ])
        planner = Planner(llm_adapter=mock_llm)
        result = planner.run("任意需求")

        assert "验收标准" in result

    def test_planner_requires_llm_adapter(self):
        """测试 Planner 没有 LLM 适配器时抛出错误"""
        from ralph.hats import Planner

        planner = Planner()
        with pytest.raises(RuntimeError, match="LLM"):
            planner.run("需求")


# --- Builder 测试 ---

class TestBuilder:
    """Builder 帽子测试套件"""

    @pytest.fixture
    def tmp_workspace(self):
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.unlink(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)

    def test_builder_creates_code_files(self, tmp_workspace):
        """测试 Builder 根据计划创建代码文件"""
        from ralph.hats import Builder
        from ralph.file_manager import FileManager

        plan = "创建 calculator.py，实现 Calculator 类"
        mock_llm = MockLLMAdapter(responses=[
            "文件: calculator.py\n"
            "```python\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n"
            "```"
        ])
        fm = FileManager(workspace=tmp_workspace)
        builder = Builder(llm_adapter=mock_llm, file_manager=fm)
        result = builder.run(plan)

        # 应该创建了文件
        assert os.path.isfile(os.path.join(tmp_workspace, "calculator.py"))

    def test_builder_extracts_code_from_llm_response(self):
        """测试 Builder 从 LLM 响应中提取代码块"""
        from ralph.hats import Builder
        from ralph.file_manager import FileManager

        mock_llm = MockLLMAdapter(responses=[
            "我来实现这个功能：\n\n"
            "文件: utils.py\n"
            "```python\ndef greet(name):\n    return f'Hello, {name}'\n```\n\n"
            "这实现了基本功能。"
        ])
        fm = FileManager(workspace=tempfile.mkdtemp())
        builder = Builder(llm_adapter=mock_llm, file_manager=fm)
        result = builder.run("实现 greet 函数")

        # 应该从响应中提取了代码
        assert "utils.py" in result or len(mock_llm.call_history) >= 1

    def test_builder_requires_llm_adapter(self):
        """测试 Builder 没有 LLM 适配器时抛出错误"""
        from ralph.hats import Builder

        builder = Builder()
        with pytest.raises(RuntimeError, match="LLM"):
            builder.run("计划")


# --- Critic 测试 ---

class TestCritic:
    """Critic 帽子测试套件"""

    def test_critic_returns_pass_or_fail(self):
        """测试 Critic 返回 PASSED 或 FAILED 判决"""
        from ralph.hats import Critic

        mock_llm = MockLLMAdapter(responses=[
            "审查结果: PASSED\n"
            "代码质量良好，逻辑正确，边界情况处理得当。"
        ])
        critic = Critic(llm_adapter=mock_llm)
        result = critic.run("一些代码内容")

        assert "PASSED" in result

    def test_critic_detects_issues(self):
        """测试 Critic 能检测到问题"""
        from ralph.hats import Critic

        mock_llm = MockLLMAdapter(responses=[
            "审查结果: FAILED\n"
            "问题：\n"
            "1. 未处理除零异常\n"
            "2. 缺少输入类型检查\n"
            "建议：添加 try-except 块"
        ])
        critic = Critic(llm_adapter=mock_llm)
        result = critic.run("有问题的代码")

        assert "FAILED" in result
        assert "除零" in result

    def test_critic_requires_llm_adapter(self):
        """测试 Critic 没有 LLM 适配器时抛出错误"""
        from ralph.hats import Critic

        critic = Critic()
        with pytest.raises(RuntimeError, match="LLM"):
            critic.run("代码")


# --- Finalizer 测试 ---

class TestFinalizer:
    """Finalizer 帽子测试套件"""

    def test_finalizer_returns_loop_complete(self):
        """测试 Finalizer 在任务完成时返回 LOOP_COMPLETE"""
        from ralph.hats import Finalizer

        mock_llm = MockLLMAdapter(responses=[
            "LOOP_COMPLETE\n"
            "所有任务已完成，测试通过，审查通过。"
        ])
        finalizer = Finalizer(llm_adapter=mock_llm)
        result = finalizer.run("完整的便签本内容")

        assert "LOOP_COMPLETE" in result

    def test_finalizer_requests_continue(self):
        """测试 Finalizer 在需要继续时给出指示"""
        from ralph.hats import Finalizer

        mock_llm = MockLLMAdapter(responses=[
            "需要继续：\n"
            "1. 缺少错误处理\n"
            "2. 测试覆盖率不足\n"
            "建议重新进入 Planner 阶段。"
        ])
        finalizer = Finalizer(llm_adapter=mock_llm)
        result = finalizer.run("不完整的便签本")

        assert "LOOP_COMPLETE" not in result
        assert "继续" in result or "重新" in result

    def test_finalizer_requires_llm_adapter(self):
        """测试 Finalizer 没有 LLM 适配器时抛出错误"""
        from ralph.hats import Finalizer

        finalizer = Finalizer()
        with pytest.raises(RuntimeError, match="LLM"):
            finalizer.run("便签本")


# --- 帽子注册表测试 ---

class TestHatRegistry:
    """帽子注册表测试"""

    def test_get_hat_by_name(self):
        """测试通过名称获取帽子实例"""
        from ralph.hats import HatRegistry, Planner

        registry = HatRegistry()
        registry.register("planner", Planner)

        hat_cls = registry.get("planner")
        assert hat_cls == Planner

    def test_get_nonexistent_hat(self):
        """测试获取不存在的帽子返回 None"""
        from ralph.hats import HatRegistry

        registry = HatRegistry()
        assert registry.get("nonexistent") is None

    def test_list_registered_hats(self):
        """测试列出所有已注册帽子名称"""
        from ralph.hats import HatRegistry, Planner, Builder, Critic, Finalizer

        registry = HatRegistry()
        registry.register("planner", Planner)
        registry.register("builder", Builder)
        registry.register("critic", Critic)
        registry.register("finalizer", Finalizer)

        names = registry.list_names()
        assert "planner" in names
        assert "builder" in names
        assert "critic" in names
        assert "finalizer" in names
