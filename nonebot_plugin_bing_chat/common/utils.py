import re

from nonebot import get_driver
from nonebot.log import logger
from nonebot.plugin.on import on_command

from .dataModel import Config


plugin_config = Config.parse_obj(get_driver().config)

command_chat = on_command(
    cmd=plugin_config.bingchat_command_chat[0],
    aliases=set(plugin_config.bingchat_command_chat[1:]),
)
command_new_chat = on_command(
    cmd=plugin_config.bingchat_command_new_chat[0],
    aliases=set(plugin_config.bingchat_command_new_chat[1:]),
)
command_history_chat = on_command(
    cmd=plugin_config.bingchat_command_history_chat[0],
    aliases=set(plugin_config.bingchat_command_history_chat[1:]),
)


def helpMessage() -> str:
    return (
        f"""命令符号：{''.join(f'"{i}"' for i in plugin_config.command_start)}\n"""
        f"""开始对话：{{命令符号}}{'/'.join(i for i in plugin_config.bingchat_command_chat)} + {{你要询问的内容}}\n"""
        f"""重置一个对话：{{命令符号}}{'/'.join(i for i in plugin_config.bingchat_command_new_chat)}"""
    )



def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d+?\^\]', '', string)
