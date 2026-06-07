"""Scratchpad 便签本模块测试"""

import os
import tempfile
import pytest
from datetime import datetime


class TestScratchpad:
    """Scratchpad 便签本测试套件"""

    @pytest.fixture
    def tmp_scratchpad_path(self):
        """创建临时便签本文件路径"""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        )
        tmp.close()
        yield tmp.name
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    def test_create_new_scratchpad(self, tmp_scratchpad_path):
        """测试创建新的便签本文件"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        assert os.path.isfile(tmp_scratchpad_path)

    def test_append_section(self, tmp_scratchpad_path):
        """测试追加一个新章节到便签本"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.append_section("Planner", "任务计划：实现计算器类，支持加减乘除")
        content = sp.read()
        assert "Planner" in content
        assert "任务计划：实现计算器类，支持加减乘除" in content

    def test_read_empty_scratchpad(self, tmp_scratchpad_path):
        """测试读取空的便签本不会报错"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        content = sp.read()
        assert isinstance(content, str)

    def test_multiple_sections_maintain_order(self, tmp_scratchpad_path):
        """测试多个章节按时间顺序追加"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.append_section("Planner", "计划内容")
        sp.append_section("Builder", "构建输出")
        sp.append_section("Critic", "审查意见")
        content = sp.read()
        planner_pos = content.find("Planner")
        builder_pos = content.find("Builder")
        critic_pos = content.find("Critic")
        assert planner_pos < builder_pos < critic_pos

    def test_clear_scratchpad(self, tmp_scratchpad_path):
        """测试清空便签本"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.append_section("Planner", "一些内容")
        sp.clear()
        content = sp.read()
        # 清空后应该为空字符串
        assert content.strip() == ""

    def test_get_last_section(self, tmp_scratchpad_path):
        """测试获取最后一个章节"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.append_section("Planner", "第一个章节")
        sp.append_section("Critic", "最后一个章节")
        last = sp.get_last_section()
        assert last is not None
        assert "Critic" in last
        assert "最后一个章节" in last

    def test_get_last_section_empty(self, tmp_scratchpad_path):
        """测试空便签本获取最后章节返回 None"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        last = sp.get_last_section()
        assert last is None

    def test_section_contains_timestamp(self, tmp_scratchpad_path):
        """测试每个章节都包含时间戳"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.append_section("Planner", "内容")
        content = sp.read()
        # 应该包含类似时间戳格式的内容
        import re
        # 检查是否有时间格式 YYYY-MM-DD HH:MM 或类似
        assert re.search(r'\d{4}-\d{2}-\d{2}', content) is not None

    def test_write_initial_requirements(self, tmp_scratchpad_path):
        """测试写入初始需求"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad(tmp_scratchpad_path)
        sp.set_requirements("实现一个计算器类，支持加减乘除")
        content = sp.read()
        assert "原始需求" in content
        assert "实现一个计算器类，支持加减乘除" in content

    def test_scratchpad_path_default(self):
        """测试默认路径"""
        from ralph.scratchpad import Scratchpad

        sp = Scratchpad()
        assert sp.path == "ralph_scratchpad.md"
