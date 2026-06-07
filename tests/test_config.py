"""Config 配置模块测试"""

import os
import tempfile
import pytest
import yaml


class TestConfig:
    """Config 配置类测试套件"""

    def test_load_from_yaml_file(self):
        """测试从 YAML 文件加载配置"""
        from ralph.config import Config

        config = Config.from_yaml("ralph_config.yaml")
        assert config.max_iterations == 10
        assert config.project_root == "./workspace"
        assert config.test_command == "pytest tests/ -v --tb=short"
        assert config.scratchpad_path == "ralph_scratchpad.md"

    def test_llm_config(self):
        """测试 LLM 配置段解析正确"""
        from ralph.config import Config

        config = Config.from_yaml("ralph_config.yaml")
        assert config.llm["provider"] == "deepseek"
        assert config.llm["model"] == "deepseek-v4-flash"
        assert "api_key_env" in config.llm

    def test_prompts_config(self):
        """测试提示词路径配置段"""
        from ralph.config import Config

        config = Config.from_yaml("ralph_config.yaml")
        assert config.prompts["planner"] == "prompts/planner.md"
        assert config.prompts["builder"] == "prompts/builder.md"
        assert config.prompts["critic"] == "prompts/critic.md"
        assert config.prompts["finalizer"] == "prompts/finalizer.md"

    def test_missing_file_raises_error(self):
        """测试配置文件不存在时抛出错误"""
        from ralph.config import Config

        with pytest.raises(FileNotFoundError):
            Config.from_yaml("nonexistent_config.yaml")

    def test_default_values(self):
        """测试未指定时的默认值"""
        from ralph.config import Config

        config = Config()
        assert config.max_iterations == 10
        assert config.project_root == "./workspace"
        assert config.scratchpad_path == "ralph_scratchpad.md"
        assert config.test_command == "pytest tests/ -v --tb=short"
        assert config.llm == {}

    def test_override_values(self):
        """测试可以覆盖默认值"""
        from ralph.config import Config

        config = Config(max_iterations=5, project_root="/tmp/test")
        assert config.max_iterations == 5
        assert config.project_root == "/tmp/test"

    def test_config_with_custom_yaml_content(self):
        """测试自定义 YAML 内容的配置解析"""
        from ralph.config import Config

        yaml_content = {
            "max_iterations": 3,
            "project_root": "./custom_workspace",
            "test_command": "python -m pytest custom_tests/",
            "scratchpad_path": "custom_scratchpad.md",
        }
        # 写入临时文件
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        yaml.dump(yaml_content, tmp)
        tmp.close()

        try:
            config = Config.from_yaml(tmp.name)
            assert config.max_iterations == 3
            assert config.project_root == "./custom_workspace"
            assert config.test_command == "python -m pytest custom_tests/"
            assert config.scratchpad_path == "custom_scratchpad.md"
        finally:
            os.unlink(tmp.name)
