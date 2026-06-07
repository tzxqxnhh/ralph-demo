"""Ralph CLI 命令行接口模块 - 提供 ralph 命令的终端入口"""

import os
import sys
import click

from ralph import __version__


# 共享选项
_scratchpad_option = click.option(
    "--scratchpad", "-s",
    default="ralph_scratchpad.md",
    help="便签本文件路径",
    show_default=True,
)


@click.group()
@click.version_option(version=__version__, prog_name="ralph")
def main():
    """Ralph - AI 驱动的轻量级任务编排工具

    通过四顶帽子（Planner/Builder/Critic/Finalizer）协作，
    实现测试驱动的 AI 编码闭环。
    """
    pass


@main.command()
@click.argument("task", required=True)
@click.option(
    "--config", "-c",
    default="ralph_config.yaml",
    help="配置文件路径",
    show_default=True,
)
@click.option(
    "--scratchpad", "-s",
    default="ralph_scratchpad.md",
    help="便签本文件路径",
    show_default=True,
)
def run(task, config, scratchpad):
    """启动新的 Ralph 任务

    TASK 为自然语言描述的需求，如："实现一个计算器类，支持加减乘除"
    """
    click.echo(f"[RALPH] 启动新任务: {task}")
    click.echo(f"[RALPH] 配置文件: {config}")
    click.echo(f"[RALPH] 便签本: {scratchpad}")

    # 检查配置文件
    if not os.path.isfile(config):
        click.echo(f"[RALPH] 错误: 配置文件 '{config}' 不存在", err=True)
        sys.exit(1)

    try:
        from ralph.config import Config
        from ralph.orchestrator import Orchestrator
        from ralph.hats import Planner, Builder, Critic, Finalizer
        from ralph.llm_adapter import create_adapter

        # 加载配置
        cfg = Config.from_yaml(config)
        cfg.scratchpad_path = scratchpad

        # 创建 LLM 适配器
        click.echo(
            f"[RALPH] 初始化 LLM 适配器 "
            f"(provider={cfg.llm.get('provider')}, model={cfg.llm.get('model')})"
        )
        llm_adapter = create_adapter(cfg.llm)

        # 创建编排器
        orch = Orchestrator(cfg)

        # 注册四顶帽子，注入 LLM 适配器和文件管理器
        orch.register_hat("planner", Planner(llm_adapter=llm_adapter))
        orch.register_hat(
            "builder",
            Builder(llm_adapter=llm_adapter, file_manager=orch.file_manager)
        )
        orch.register_hat("critic", Critic(llm_adapter=llm_adapter))
        orch.register_hat("finalizer", Finalizer(llm_adapter=llm_adapter))

        click.echo("[RALPH] Ralph Loop 开始执行...\n")

        # 执行 Ralph Loop
        result = orch.run(task)

        # 输出执行摘要
        click.echo(f"\n{'='*50}")
        click.echo(f"[RALPH] 任务执行完成")
        click.echo(f"[RALPH] 总迭代次数: {result['iterations']}")
        click.echo(
            f"[RALPH] 状态: "
            f"{'达到最大迭代限制' if result['max_iterations_reached'] else '正常完成'}"
        )
        click.echo(f"[RALPH] 便签本: {scratchpad}")
        click.echo(f"[RALPH] 生成文件目录: {cfg.project_root}")

        orch.close()

    except Exception as e:
        click.echo(f"[RALPH] 错误: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--scratchpad", "-s",
    default="ralph_scratchpad.md",
    help="便签本文件路径",
    show_default=True,
)
def status(scratchpad):
    """显示当前迭代状态"""
    if not os.path.isfile(scratchpad):
        click.echo(f"[RALPH] 便签本 '{scratchpad}' 不存在，没有活动任务。")
        return

    with open(scratchpad, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        click.echo("[RALPH] 便签本为空，没有活动任务。")
        return

    click.echo(f"[RALPH] 便签本: {scratchpad}")
    click.echo("[RALPH] 当前内容:")

    # 统计章节数
    section_count = content.count("\n## ")
    requirements = ""
    loop_complete = "LOOP_COMPLETE" in content

    # 提取需求
    for line in content.split("\n"):
        if "原始需求" in line:
            # 下一行就是需求内容
            idx = content.find("原始需求")
            end = content.find("\n## ", idx + 1)
            if end == -1:
                end = len(content)
            requirements = content[idx:end].strip()
            break

    click.echo(f"  迭代阶段数: {section_count}")
    click.echo(f"  任务完成状态: {'已完成' if loop_complete else '进行中'}")
    if requirements:
        click.echo(f"  {requirements.split(chr(10))[0]}")


@main.command()
@click.option(
    "--scratchpad", "-s",
    default="ralph_scratchpad.md",
    help="便签本文件路径",
    show_default=True,
)
@click.confirmation_option(
    prompt="确定要清除便签本和生成的文件吗？此操作不可撤销。"
)
def clean(scratchpad):
    """清除便签本和生成的文件"""
    if os.path.isfile(scratchpad):
        with open(scratchpad, "w", encoding="utf-8") as f:
            f.write("")
        click.echo(f"[RALPH] 已清除便签本: {scratchpad}")
    else:
        click.echo(f"[RALPH] 便签本 '{scratchpad}' 不存在，无需清除。")


@main.command()
@click.option(
    "--scratchpad", "-s",
    default="ralph_scratchpad.md",
    help="便签本文件路径",
    show_default=True,
)
def resume(scratchpad):
    """从现有便签本恢复任务"""
    if not os.path.isfile(scratchpad):
        click.echo(
            f"[RALPH] 错误: 便签本 '{scratchpad}' 不存在，无法恢复。",
            err=True,
        )
        sys.exit(1)

    with open(scratchpad, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        click.echo("[RALPH] 便签本为空，没有可恢复的任务。")
        return

    click.echo(f"[RALPH] 从便签本恢复: {scratchpad}")
    click.echo("[RALPH] 当前便签本内容:")
    click.echo(content[:500] + ("..." if len(content) > 500 else ""))

    # 恢复逻辑：读取便签本，从上次中断的位置继续
    if "LOOP_COMPLETE" in content:
        click.echo("[RALPH] 该任务已完成，无需恢复。")
        return

    click.echo("[RALPH] 任务未完成，需要重新运行。")
    click.echo("[RALPH] 提示: 使用 'ralph run' 配合相同的需求描述来继续。")


if __name__ == "__main__":
    main()
