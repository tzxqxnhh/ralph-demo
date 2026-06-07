"""Ralph LLM适配器模块 - 连接不同AI模型提供商

每个适配器实现统一的 chat(prompt) 接口，供帽子角色调用。
"""

import logging
from openai import OpenAI


class BaseLLMAdapter:
    """LLM适配器基类 - 所有适配器的抽象基类"""

    def chat(self, prompt: str) -> str:
        """发送提示词并获取 AI 响应

        Args:
            prompt: 完整的提示词文本（系统提示 + 用户需求）

        Returns:
            str: AI 模型的原始文本响应
        """
        raise NotImplementedError


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek API适配器 - 通过 OpenAI 兼容接口调用 DeepSeek 模型"""

    # DeepSeek API 默认端点
    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key=None, model="deepseek-chat",
                 base_url=None):
        """
        Args:
            api_key: DeepSeek API 密钥
            model: 模型名称，如 deepseek-chat, deepseek-v4-flash
            base_url: API 端点地址，默认 https://api.deepseek.com
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
        self.logger = logging.getLogger("ralph.llm")

    def chat(self, prompt: str) -> str:
        """调用 DeepSeek API 发送提示词并获取响应"""
        self.logger.info(
            f"调用 DeepSeek API (模型: {self.model}, "
            f"提示词长度: {len(prompt)} 字符)"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            self.logger.info(
                f"API 响应成功 (长度: {len(content)} 字符)"
            )
            return content
        except Exception as e:
            self.logger.error(f"DeepSeek API 调用失败: {e}")
            raise RuntimeError(f"LLM调用失败: {e}")


# 适配器工厂 - 根据配置创建对应的适配器实例
_PROVIDER_MAP = {
    "deepseek": DeepSeekAdapter,
}


def create_adapter(llm_config: dict) -> BaseLLMAdapter:
    """根据配置字典创建对应的 LLM 适配器实例

    Args:
        llm_config: 配置字典，包含 provider, model, api_key_env 等字段

    Returns:
        BaseLLMAdapter: 适配器实例

    Raises:
        ValueError: 遇到不支持的提供商时
    """
    provider = llm_config.get("provider", "").lower()
    model = llm_config.get("model", "deepseek-chat")
    api_key = llm_config.get("api_key_env", "")

    adapter_cls = _PROVIDER_MAP.get(provider)
    if adapter_cls is None:
        raise ValueError(
            f"不支持的 LLM 提供商: '{provider}'。"
            f"当前支持: {list(_PROVIDER_MAP.keys())}"
        )

    return adapter_cls(api_key=api_key, model=model)
