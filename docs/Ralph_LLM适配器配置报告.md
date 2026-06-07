# Ralph LLM适配器配置报告

> 日期: 2026-06-07
> 环境: Windows 11, Python 3.12.9, 虚拟环境 `D:\myenvs\myenv_helloagent`

---

## 一、背景

Ralph 项目的 `ralph run` 命令原先只是一个骨架，缺少真正的 LLM 适配器实现。运行时会提示：

```
[RALPH] 提示: 需要配置 LLM 适配器才能运行完整 Ralph Loop
[RALPH] 请参考文档了解如何配置 DeepSeek/OpenAI 等适配器
```

本次工作完成了 LLM 适配器的创建和 CLI 接入，使 Ralph 能够真正调用 DeepSeek API 执行 AI 驱动的编码任务。

---

## 二、修改内容

### 2.1 新建 `ralph/llm_adapter.py` — LLM适配器模块

文件路径: `ralph/llm_adapter.py`

实现了适配器架构：

```
BaseLLMAdapter (抽象基类)
  └── chat(prompt) -> str      # 统一接口

DeepSeekAdapter (BaseLLMAdapter)
  └── 通过 OpenAI 兼容接口调用 DeepSeek API

create_adapter(llm_config)      # 工厂函数，根据配置选择适配器
```

**关键设计点：**

- `chat(prompt)` 方法是帽子角色调用 AI 的唯一入口，接收完整提示词字符串，返回 AI 原始响应文本
- `DeepSeekAdapter` 使用 `openai` SDK，通过 `base_url="https://api.deepseek.com"` 指向 DeepSeek 端点
- `create_adapter()` 工厂函数根据 `ralph_config.yaml` 中的 `llm.provider` 自动选择适配器
- 支持后续扩展：只需实现 `BaseLLMAdapter` 子类并注册到 `_PROVIDER_MAP` 即可接入新提供商

**适配器接口定义：**

```python
class BaseLLMAdapter:
    def chat(self, prompt: str) -> str:
        """发送提示词并获取 AI 响应"""
        raise NotImplementedError
```

### 2.2 修改 `ralph/cli.py` — 接入真实LLM

文件路径: `ralph/cli.py` (第 58-81 行)

原来 `run` 命令只打印提示信息，修改后完整流程：

1. 加载 `ralph_config.yaml` 配置
2. 调用 `create_adapter(cfg.llm)` 创建 LLM 适配器
3. 将适配器注入四顶帽子 (Planner/Builder/Critic/Finalizer)
4. 将文件管理器注入 Builder 帽子
5. 执行完整的 Ralph Loop 并输出执行摘要

```python
# 创建 LLM 适配器
llm_adapter = create_adapter(cfg.llm)

# 注册四顶帽子，注入 LLM 适配器和文件管理器
orch.register_hat("planner", Planner(llm_adapter=llm_adapter))
orch.register_hat("builder", Builder(llm_adapter=llm_adapter, file_manager=orch.file_manager))
orch.register_hat("critic", Critic(llm_adapter=llm_adapter))
orch.register_hat("finalizer", Finalizer(llm_adapter=llm_adapter))

# 执行 Ralph Loop
result = orch.run(task)
```

### 2.3 修改 `ralph/test_runner.py` — 修复Windows编码

文件路径: `ralph/test_runner.py` (第 24 行)

Windows 下 `subprocess.run()` 默认使用 GBK 编码，导致 pytest 输出的 UTF-8 中文出现乱码或子进程线程崩溃。

**修复:** 在 `subprocess.run()` 中添加 `encoding="utf-8"`

```python
# 修改前
result = subprocess.run(args, capture_output=True, text=True, timeout=..., cwd=...)

# 修改后
result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=..., cwd=...)
```

### 2.4 修改 `pyproject.toml` — 修复构建配置

文件路径: `pyproject.toml`

| 问题 | 修复 |
|------|------|
| `build-backend` 使用了已废弃的 `setuptools.backends._legacy:_Backend` | 改为 `setuptools.build_meta` |
| 新版 setuptools (81.0.0) 拒绝 flat-layout 多目录 | 添加 `[tool.setuptools.packages.find]` 配置，仅包含 `ralph*` |

---

## 三、配置说明

`ralph_config.yaml` 中 LLM 相关配置项：

```yaml
llm:
  provider: "deepseek"           # 提供商: deepseek / openai (可扩展)
  model: "deepseek-v4-flash"     # 模型名称
  api_key_env: "sk-xxx"          # API 密钥
```

当前支持的提供商映射：

| provider 值 | 适配器类 | API 端点 |
|------------|---------|---------|
| `deepseek` | `DeepSeekAdapter` | `https://api.deepseek.com` |

扩展其他提供商只需：
1. 在 `llm_adapter.py` 中创建继承 `BaseLLMAdapter` 的子类
2. 将 `provider名 -> 适配器类` 注册到 `_PROVIDER_MAP` 字典

---

## 四、验证结果

### 4.1 项目测试套件

```
69 passed in 10.64s
```

所有原有测试通过，修改未引入回归问题。

### 4.2 DeepSeek API 连通性

- 模型: `deepseek-v4-flash`
- 端点: `https://api.deepseek.com`
- 状态: 连通正常

### 4.3 实战验证

执行 `ralph run "实现一个计算器类，支持加减乘除和单元测试"`，Ralph Loop 自动完成：

| 阶段 | 帽子角色 | 产出 |
|------|---------|------|
| 1 | **Planner** | 任务计划 + 验收标准 |
| 2 | **Builder** | `workspace/calculator.py` + `workspace/test_calculator.py` |
| 3 | **Critic** | 审查通过 (PASSED) |
| 4 | **Finalizer** | 判断 LOOP_COMPLETE |

**生成的代码覆盖：**

- `Calculator` 类: `add`, `subtract`, `multiply`, `divide` 四个方法
- 除零异常处理 (`ValueError: Division by zero`)
- 浮点数运算支持

**生成的测试覆盖：**

- 19 个测试用例全部通过
- 覆盖: 正整数、负整数、正负混合、浮点精度、乘零、除零异常、零除以非零

```
tests/test_calculator.py::TestCalculator - 19 passed in 0.04s
```

---

## 五、日常使用命令

```bash
# 进入项目目录 (必须设置 UTF-8 编码)
export PYTHONIOENCODING=utf-8
cd CASE1_Ralph实战

# 查看帮助
ralph --help

# 查看当前状态
ralph status

# 启动新任务
ralph run "需求描述"

# 恢复中断的任务
ralph resume

# 清除便签本和生成文件
ralph clean

# 运行项目测试
pytest tests/ -v
```

---

## 六、文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `ralph/llm_adapter.py` | **新建** | DeepSeek 适配器 + 适配器工厂 |
| `ralph/cli.py` | 修改 | `run` 命令接入真实 LLM |
| `ralph/test_runner.py` | 修改 | 子进程编码修复 |
| `pyproject.toml` | 修改 | 构建后端 + 包发现配置 |
| `workspace/calculator.py` | 生成 | AI 生成的计算器代码 |
| `workspace/test_calculator.py` | 生成 | AI 生成的单元测试 |
| `docs/Ralph_LLM适配器配置报告.md` | **新建** | 本文档 |

---

## 七、架构总览

```
ralph_config.yaml (LLM配置)
       |
       v
create_adapter()  ──> DeepSeekAdapter ──> DeepSeek API
       |
       v
  Orchestrator
       |
   ┌───┼───┬───────┐
   v   v   v       v
Planner Builder Critic Finalizer   (四顶帽子, 注入 llm_adapter)
   │     │      │        │
   └─────┴──────┴────────┘
              │
              v
    ralph_scratchpad.md  (便签本, 上下文传递)
              │
              v
       workspace/  (生成代码目录)
```
