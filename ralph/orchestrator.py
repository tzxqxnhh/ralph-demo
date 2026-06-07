"""Ralph 主控制器模块 - Ralph Loop 的核心编排逻辑

负责循环控制、迭代计数、异常处理，按顺序调用四顶帽子，
在每次帽子调用前后读写便签本，形成完整的测试驱动反馈闭环。
"""

import os
import logging
from datetime import datetime

from ralph.scratchpad import Scratchpad
from ralph.file_manager import FileManager
from ralph.test_runner import TestRunner


class Orchestrator:
    """主控制器 - 编排 Ralph Loop 完整工作流"""

    def __init__(self, config, max_hat_retries=3, log_path="ralph.log",
                 test_runner=None):
        self.config = config
        self.iteration = 0
        self.max_hat_retries = max_hat_retries
        self._hats = {}

        # 初始化便签本
        self.scratchpad = Scratchpad(path=config.scratchpad_path)

        # 初始化文件管理器
        self.file_manager = FileManager(workspace=config.project_root)

        # 初始化测试运行器（支持注入用于测试）
        if test_runner is not None:
            self.test_runner = test_runner
        else:
            self.test_runner = TestRunner(command=config.test_command)

        # 日志设置
        self.log_path = log_path
        self._setup_logging()

    def _setup_logging(self):
        """配置日志记录"""
        self.logger = logging.getLogger("ralph")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        # 文件处理器
        fh = logging.FileHandler(self.log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def register_hat(self, name, hat_instance):
        """注册一个帽子实例"""
        self._hats[name] = hat_instance

    def get_hat(self, name):
        """获取已注册的帽子实例"""
        return self._hats.get(name)

    def _run_hat_with_retry(self, name, context):
        """带重试机制运行帽子"""
        hat = self._hats.get(name)
        if hat is None:
            raise RuntimeError(f"帽子 '{name}' 未注册")

        last_error = None
        for attempt in range(1, self.max_hat_retries + 1):
            try:
                self._log(f"[{name}] 第 {attempt} 次尝试...")
                result = hat.run(context)
                self._log(f"[{name}] 执行成功")
                return result
            except Exception as e:
                last_error = e
                self._log(f"[{name}] 第 {attempt} 次失败: {e}")
                if attempt < self.max_hat_retries:
                    continue
        # 所有重试都失败
        error_msg = (
            f"帽子 '{name}' 在 {self.max_hat_retries} 次重试后仍然失败。"
            f"最后错误: {last_error}"
        )
        self._log(f"[ERROR] {error_msg}")
        self.scratchpad.append_section(name, f"错误: {error_msg}")
        raise RuntimeError(error_msg)

    def _log(self, message):
        """记录日志到文件和控制台"""
        self.logger.info(message)
        print(f"[RALPH] {message}")

    def close(self):
        """关闭日志处理器，释放文件句柄"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    def run(self, user_request):
        """执行 Ralph Loop 主循环

        Args:
            user_request: 用户的自然语言需求描述

        Returns:
            dict: 执行结果摘要
        """
        self._log(f"Ralph Loop 启动，最大迭代次数: {self.config.max_iterations}")
        self.scratchpad.set_requirements(user_request)

        for i in range(1, self.config.max_iterations + 1):
            self.iteration = i
            self._log(f"=== 迭代 {i}/{self.config.max_iterations} ===")

            # 阶段1: Planner - 生成计划
            if i == 1:
                self._log("阶段: Planner - 生成任务计划")
                plan = self._run_hat_with_retry("planner", user_request)
                self.scratchpad.append_section("Planner", plan)
            else:
                # 后续迭代：Critic 的反馈作为 Planner 的新输入
                scratchpad_content = self.scratchpad.read()
                self._log("阶段: Planner - 根据反馈重新规划")
                plan = self._run_hat_with_retry("planner", scratchpad_content)
                self.scratchpad.append_section("Planner", plan)

            # 阶段2: Builder - 写代码 + 测试内循环
            self._log("阶段: Builder - 编写代码并运行测试")
            builder_context = self.scratchpad.read()
            build_result = self._run_hat_with_retry("builder", builder_context)
            self.scratchpad.append_section("Builder", build_result)

            # Builder 内循环: 运行测试直到通过或达到最大重试
            build_retries = 0
            max_build_retries = 5
            while build_retries < max_build_retries:
                passed, test_output = self.test_runner.run()
                if passed:
                    self._log("Builder: 测试全部通过")
                    self.scratchpad.append_section(
                        "Builder-Test", f"测试通过\n{test_output}"
                    )
                    break
                else:
                    build_retries += 1
                    self._log(f"Builder: 测试失败 (第{build_retries}次修复尝试)")
                    self.scratchpad.append_section(
                        "Builder-Test",
                        f"测试失败 (尝试 {build_retries}):\n{test_output}",
                    )
                    if build_retries < max_build_retries:
                        # 让 Builder 根据错误信息修复
                        fix_context = self.scratchpad.read()
                        fix_result = self._run_hat_with_retry(
                            "builder", fix_context
                        )
                        self.scratchpad.append_section(
                            "Builder-Fix", fix_result
                        )
                    else:
                        self._log("Builder: 达到最大修复尝试次数")

            # 阶段3: Critic - 审查代码
            self._log("阶段: Critic - 代码审查")
            critic_context = self.scratchpad.read()
            critic_result = self._run_hat_with_retry("critic", critic_context)
            self.scratchpad.append_section("Critic", critic_result)

            if "FAILED" in critic_result:
                self._log("Critic: 审查未通过，反馈给下一轮迭代")
                # 不立即跳出，让 Finalizer 决定
            else:
                self._log("Critic: 审查通过")

            # 阶段4: Finalizer - 终结判断
            self._log("阶段: Finalizer - 终结判断")
            finalizer_context = self.scratchpad.read()
            finalizer_result = self._run_hat_with_retry(
                "finalizer", finalizer_context
            )
            self.scratchpad.append_section("Finalizer", finalizer_result)

            if "LOOP_COMPLETE" in finalizer_result:
                self._log(f"Finalizer: LOOP_COMPLETE - 任务在第 {i} 轮完成")
                break
            else:
                self._log("Finalizer: 任务未完成，继续下一轮迭代")

        # 达到最大迭代次数
        if self.iteration >= self.config.max_iterations:
            self._log(
                f"达到最大迭代次数 ({self.config.max_iterations})，循环终止"
            )

        self._log("Ralph Loop 结束")
        return {
            "iterations": self.iteration,
            "scratchpad": self.scratchpad.read(),
            "max_iterations_reached": (
                self.iteration >= self.config.max_iterations
            ),
        }
