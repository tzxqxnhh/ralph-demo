# Ralph — AI 驱动的轻量级任务编排工具

Ralph 让 AI 自主完成编码任务。核心机制是 **Ralph Loop**：四顶"帽子"（角色）协作 + 文件系统传递上下文 + 测试驱动的反馈闭环，使 AI 持续迭代直至任务完成。

## 快速开始

```bash
# 1. 进入项目目录
cd CASE1_Ralph实战

# 2. 安装依赖
pip install -e .

# 3. 看帮助
ralph --help

# 4. 查看当前状态
ralph status

# 5. 启动一个任务（需要先配置好 LLM 适配器）
ralph run "实现一个计算器类，支持加减乘除和单元测试"
```

## 核心理念

```
用户需求 → Planner → Builder → Critic → Finalizer → 完成
              ↑          │          │          │
              └──────────└──────────└──────────┘
                    便签本 (ralph_scratchpad.md)
```

| 阶段 | 角色 | 做什么 |
|------|------|--------|
| 1 | **Planner** | 把需求拆成原子任务，输出验收标准 |
| 2 | **Builder** | 按计划写代码，跑测试，失败就原地修 |
| 3 | **Critic** | 审查代码质量、逻辑、边界，给 PASSED/FAILED |
| 4 | **Finalizer** | 通读便签本，判断任务真完成了还是继续 |

每一步的输出都写入 `ralph_scratchpad.md`，AI 不靠记忆，靠文件传话。

## 项目结构

```
CASE1_Ralph实战/
├── ralph/                    # 核心代码
│   ├── cli.py                #   命令行入口
│   ├── orchestrator.py       #   主控制器（Ralph Loop）
│   ├── hats.py               #   四顶帽子（Planner/Builder/Critic/Finalizer）
│   ├── config.py             #   配置解析
│   ├── scratchpad.py         #   便签本管理
│   ├── file_manager.py       #   文件读写
│   └── test_runner.py        #   测试执行器
├── tests/                    # 测试套件（69 个测试）
├── prompts/                  # 帽子提示词模板（可自定义）
│   ├── planner.md
│   ├── builder.md
│   ├── critic.md
│   └── finalizer.md
├── ralph_config.yaml         # 配置文件
└── spec.md                   # 架构规格文档
```

## 命令一览

```bash
ralph run "需求描述"      # 启动新任务
ralph status              # 查看当前迭代状态
ralph resume              # 从便签本恢复中断的任务
ralph clean               # 清除便签本和生成文件
```

## 配置

编辑 `ralph_config.yaml`：

```yaml
max_iterations: 10              # 最大迭代轮数（安全阀）
project_root: "./workspace"     # 代码生成目录
test_command: "pytest tests/ -v --tb=short"
scratchpad_path: "ralph_scratchpad.md"

llm:                            # AI 模型配置
  provider: "deepseek"
  model: "deepseek-v4-flash"
  api_key_env: "sk-xxx"

prompts:                        # 自定义提示词路径
  planner: "prompts/planner.md"
  builder: "prompts/builder.md"
  critic: "prompts/critic.md"
  finalizer: "prompts/finalizer.md"
```

## 自定义提示词

直接编辑 `prompts/` 下的 `.md` 文件即可改变帽子的行为，无需改代码。

优先级：`prompts/xxx.md` 存在 → 用它；不存在 → 用内置默认值。

| 文件 | 调什么 |
|------|--------|
| `planner.md` | 任务拆分粒度、验收标准格式 |
| `builder.md` | 编码风格、修复策略 |
| `critic.md` | 审查维度、严重度分级 |
| `finalizer.md` | 完成判定门槛、报告格式 |

## 扩展

- **自定义帽子**：创建一个继承 `BaseHat` 的类，注册到 `HatRegistry`，插入 Ralph Loop
- **自定义 LLM**：实现 `chat(prompt)` 方法的适配器，注入帽子实例
- **自定义测试框架**：修改 `test_command` 配置，支持 jest、unittest 等

## 依赖

- Python >= 3.9
- click >= 8.0
- pyyaml >= 6.0
- pytest >= 7.0
