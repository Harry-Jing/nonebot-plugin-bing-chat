import re
from pathlib import Path

from nonebot import get_driver
from nonebot.log import logger
from nonebot.rule import Rule, command, to_me
from nonebot.plugin.on import on_message

from .dataModel import Config


plugin_config = Config.parse_obj(get_driver().config)

plugin_directory = Path('./data/BingChat')

command_chat = on_message(
    rule=command(*set(plugin_config.bingchat_command_chat))
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
)
command_new_chat = on_message(
    rule=command(*set(plugin_config.bingchat_command_new_chat))
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
)
command_history_chat = on_message(
    rule=command(*set(plugin_config.bingchat_command_history_chat))
    & (to_me() if plugin_config.bingchat_to_me else Rule()),
)


def helpMessage() -> str:
    help_message = (
        f"""开始对话：{'/'.join(i for i in plugin_config.bingchat_command_chat)} + {{你要询问的内容}}"""
        f"""\n\n"""
        f"""新建一个对话：{'/'.join(i for i in plugin_config.bingchat_command_new_chat)}"""
        f"""\n\n"""
        f"""查看历史记录：{'/'.join(i for i in plugin_config.bingchat_command_new_chat)}"""
        f"""\n\n"""
        f"""如果有任何疑问请查看https://github.com/Harry-Jing/nonebot-plugin-bing-chat"""
    )

    if '' not in plugin_config.command_start:
        help_message = (
            f"""以下所有的命令都要在开头加上命令符号！！！"""
            f"""\n\n"""
            f"""命令符号：{','.join(f'"{i}"' for i in plugin_config.command_start)}"""
            f"""\n\n"""
        ) + help_message

    return help_message


def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d+?\^\]', '', string)


def initCookie():
    if not plugin_directory.exists():
        plugin_directory.mkdir(parents=True)

    file_path = plugin_directory.joinpath('cookies.json')

    if not file_path.exists():
        file_path.touch()

    if file_path.stat().st_size == 0:
        raise FileNotFoundError(
            'BingChat插件未配置cookie，请在./data/BingChat/cookies.json中填入你的cookie'
        )
