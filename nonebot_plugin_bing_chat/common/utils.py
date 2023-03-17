import re
import shutil
from datetime import datetime, timedelta

from nonebot import get_driver, require
from nonebot.plugin.on import on_message
from nonebot.rule import Rule, command, to_me

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .dataModel import Config

plugin_config = Config.parse_obj(get_driver().config)

plugin_directory = plugin_config.bingchat_plugin_directory

command_chat = on_message(
    rule=command(*plugin_config.bingchat_command_chat)
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)
command_new_chat = on_message(
    rule=command(*plugin_config.bingchat_command_new_chat)
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)
command_history_chat = on_message(
    rule=command(*plugin_config.bingchat_command_history_chat)
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)

matcher_reply_to_me = on_message(
    rule=to_me(),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)


_matcher_in_regex = '|'.join(
    (
        f"""(({'|'.join(plugin_config.bingchat_command_start)})({'|'.join(plugin_config.bingchat_command_chat)}).*)""",
        f"""(({'|'.join(plugin_config.bingchat_command_start)})({'|'.join(plugin_config.bingchat_command_new_chat)}).*)""",
        f"""(({'|'.join(plugin_config.bingchat_command_start)})({'|'.join(plugin_config.bingchat_command_history_chat)}).*)""",
    )
)


def isConfilctWithOtherMatcher(msg: str) -> bool:
    return True if re.match(_matcher_in_regex, msg) else False


def helpMessage() -> str:
    help_message = (
        f"""开始对话：{'/'.join(plugin_config.bingchat_command_chat)} + {{你要询问的内容}}"""
        f"""\n\n"""
        f"""新建一个对话：{'/'.join(plugin_config.bingchat_command_new_chat)}"""
        f"""\n\n"""
        f"""查看历史记录：{'/'.join(plugin_config.bingchat_command_history_chat)}"""
        f"""\n\n"""
        f"""如果有任何疑问请查看https://github.com/Harry-Jing/nonebot-plugin-bing-chat"""
    )

    if '' not in plugin_config.bingchat_command_start:
        help_message = (
            f"""以下所有的命令都要在开头加上命令符号！！！"""
            f"""\n\n"""
            f"""命令符号：{','.join(plugin_config.bingchat_command_start)}"""
            f"""\n\n"""
        ) + help_message

    return help_message


def initFile() -> None:
    plugin_directory.mkdir(parents=True, exist_ok=True)

    # 检查cookie文件是否存在且不为空
    file_path = plugin_directory.joinpath('cookies.json')
    file_path.touch(exist_ok=True)
    if file_path.stat().st_size == 0:
        raise FileNotFoundError(
            'BingChat插件未配置cookie，请在./data/BingChat/cookies.json中填入你的cookie'
        )

    # 创建log文件夹
    plugin_log_directory = plugin_directory / 'log'
    plugin_log_directory.mkdir(parents=True, exist_ok=True)


def createLog(data: str) -> None:
    current_log_directory = (
        plugin_directory / 'log' / datetime.now().strftime('%Y-%m-%d')
    )
    current_log_directory.mkdir(parents=True, exist_ok=True)
    current_log_file = (
        current_log_directory / f'{datetime.now().strftime("%H-%M-%S")}.log'
    )
    current_log_file.write_text(data=str(data), encoding='utf-8')


@scheduler.scheduled_job('cron', hour=2)  # type: ignore
async def _del_log_file() -> None:
    print('del_log_file')
    current_time = datetime.now()
    plugin_log_directory = plugin_directory / 'log'
    for child_dir in plugin_log_directory.iterdir():
        if current_time - datetime.fromisoformat(child_dir.name) > timedelta(days=7):
            shutil.rmtree(child_dir)
