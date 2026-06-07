"""Ralph 配置模块 - 负责读取和管理 ralph_config.yaml 配置"""

import os
import yaml


class Config:
    """Ralph 配置管理类"""

    def __init__(self, **kwargs):
        # 默认值
        self.max_iterations = kwargs.get("max_iterations", 10)
        self.project_root = kwargs.get("project_root", "./workspace")
        self.scratchpad_path = kwargs.get(
            "scratchpad_path", "ralph_scratchpad.md"
        )
        self.test_command = kwargs.get(
            "test_command", "pytest tests/ -v --tb=short"
        )
        self.llm = kwargs.get("llm", {})
        self.prompts = kwargs.get("prompts", {})

    @classmethod
    def from_yaml(cls, path):
        """从 YAML 文件加载配置"""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)
