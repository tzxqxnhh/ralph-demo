"""Ralph 四顶帽子模块 - Planner/Builder/Critic/Finalizer 角色实现

每个帽子代表 AI 在 Ralph Loop 中承担的一个明确角色。
帽子通过 LLM 适配器调用 AI 模型，实现各自职责。

提示词加载优先级：
1. prompts/ 目录下的 .md 文件（用户自定义）
2. 代码内置默认提示词（兜底）
"""

import os
import re


class BaseHat:
    """帽子基类 - 所有角色的抽象基类"""

    # 子类覆盖：对应 prompts/ 目录下的文件名
    prompt_file = None

    def __init__(self, llm_adapter=None):
        self.llm = llm_adapter

    def _ensure_llm(self):
        """确保 LLM 适配器已设置"""
        if self.llm is None:
            raise RuntimeError(
                f"{self.__class__.__name__} 需要 LLM 适配器才能运行"
            )

    def _load_prompt(self, default_factory):
        """加载提示词：优先读取外部文件，找不到则使用内置默认值

        Args:
            default_factory: 无参可调用对象，返回内置默认提示词

        Returns:
            str: 提示词内容
        """
        if self.prompt_file and os.path.isfile(self.prompt_file):
            try:
                with open(self.prompt_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    return content
            except (OSError, UnicodeDecodeError):
                pass  # 读取失败，回退到内置默认
        return default_factory()

    def run(self, context):
        """运行帽子逻辑 - 子类必须实现"""
        raise NotImplementedError


class Planner(BaseHat):
    """Planner 帽子 - 将自然语言需求拆解为原子任务和验收标准"""

    prompt_file = "prompts/planner.md"

    def run(self, requirements):
        """根据需求生成结构化的任务计划"""
        self._ensure_llm()

        def build_default():
            return (
                "你是一个技术规划专家。请根据以下用户需求，生成一个结构化的任务计划。\n"
                "计划应包含：\n"
                "1. 任务分解（原子级别）\n"
                "2. 需要创建/修改的文件清单\n"
                "3. 明确的验收标准\n\n"
                f"用户需求：\n{requirements}\n\n"
                "请用中文输出计划。"
            )

        system_prompt = self._load_prompt(build_default)
        full_prompt = system_prompt + f"\n\n用户需求：\n{requirements}"
        response = self.llm.chat(full_prompt)
        return response


class Builder(BaseHat):
    """Builder 帽子 - 根据计划编写代码文件，运行测试并原地修复"""

    prompt_file = "prompts/builder.md"

    def __init__(self, llm_adapter=None, file_manager=None):
        super().__init__(llm_adapter)
        self.file_manager = file_manager

    def run(self, plan):
        """根据计划生成代码并写入文件"""
        self._ensure_llm()

        def build_default():
            return (
                "你是一个代码实现专家。请根据以下任务计划，生成完整的代码实现。\n"
                "对于每个文件，请使用以下格式输出：\n"
                "文件: <文件路径>\n"
                "```python\n"
                "<代码内容>\n"
                "```\n\n"
                f"任务计划：\n{plan}\n\n"
                "请生成实际可运行的代码。"
            )

        system_prompt = self._load_prompt(build_default)
        full_prompt = system_prompt + f"\n\n任务计划：\n{plan}"
        response = self.llm.chat(full_prompt)
        # 从 LLM 响应中提取代码块并写入文件
        self._extract_and_write_files(response)
        return response

    def _extract_and_write_files(self, response):
        """从 LLM 响应中提取文件路径和代码块，写入文件系统"""
        # 匹配模式: "文件: <路径>" 后跟 ```python ... ```
        pattern = r'文件:\s*([^\n]+)\s*\n\s*```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)

        if self.file_manager:
            for filepath, code in matches:
                filepath = filepath.strip()
                code = code.strip()
                self.file_manager.write_file(filepath, code)


class Critic(BaseHat):
    """Critic 帽子 - 审查代码质量、逻辑正确性、边界情况"""

    prompt_file = "prompts/critic.md"

    def run(self, context):
        """审查代码并给出 PASSED/FAILED 判决"""
        self._ensure_llm()

        def build_default():
            return (
                "你是一个代码审查专家。请审查以下代码实现，关注：\n"
                "1. 代码质量和可读性\n"
                "2. 逻辑正确性\n"
                "3. 边界情况处理\n"
                "4. 错误处理\n\n"
                f"代码上下文：\n{context}\n\n"
                "请给出审查意见。如果通过，以'审查结果: PASSED'开头；"
                "如果不通过，以'审查结果: FAILED'开头，并列出问题和建议。"
            )

        system_prompt = self._load_prompt(build_default)
        full_prompt = system_prompt + f"\n\n代码上下文：\n{context}"
        response = self.llm.chat(full_prompt)
        return response


class Finalizer(BaseHat):
    """Finalizer 帽子 - 综合分析便签本，决定循环是否结束"""

    prompt_file = "prompts/finalizer.md"

    def run(self, context):
        """分析便签本，决定 LOOP_COMPLETE 或需要继续"""
        self._ensure_llm()

        def build_default():
            return (
                "你是一个项目终结判断专家。请分析以下便签本内容，判断任务是否真正完成。\n"
                "判断标准：\n"
                "1. 所有计划任务是否已执行？\n"
                "2. 所有测试是否通过？\n"
                "3. 审查是否通过（PASSED）？\n"
                "4. 是否有遗留问题？\n\n"
                f"便签本内容：\n{context}\n\n"
                "如果任务已完成，请输出 'LOOP_COMPLETE' 并总结。"
                "如果需要继续，请说明具体原因和建议的下一步行动。"
            )

        system_prompt = self._load_prompt(build_default)
        full_prompt = system_prompt + f"\n\n便签本内容：\n{context}"
        response = self.llm.chat(full_prompt)
        return response


class HatRegistry:
    """帽子注册表 - 管理可用帽子的注册和查找"""

    def __init__(self):
        self._hats = {}

    def register(self, name, hat_class):
        """注册一个帽子类"""
        self._hats[name] = hat_class

    def get(self, name):
        """通过名称获取帽子类，不存在返回 None"""
        return self._hats.get(name)

    def list_names(self):
        """列出所有已注册的帽子名称"""
        return list(self._hats.keys())
