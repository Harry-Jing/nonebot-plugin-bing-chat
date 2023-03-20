import re
from datetime import datetime

from nonebot import get_driver
from nonebot.log import logger
from nonebot.rule import Rule, command, to_me
from nonebot.plugin.on import on_message

from .data_model import Config, UserInfo, UserData


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


# dict[user_id, UserData] user_id: UserData
user_data_dict: dict[UserInfo, UserData] = dict()

# dict[message_id, user_id] bot回答的问题的message_id: 对应的用户的user_id
reply_message_id_dict: dict[int, UserInfo] = dict()


_matcher_in_regex = '|'.join(
    (
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_new_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_history_chat)}).*)""",
    )
)

HELP_MESSAGE = (
    (
        f"""开始对话：{'/'.join(i for i in plugin_config.bingchat_command_chat)} + {{你要询问的内容}}"""
        f"""\n\n"""
        f"""新建一个对话：{'/'.join(i for i in plugin_config.bingchat_command_new_chat)}"""
        f"""\n\n"""
        f"""查看历史记录：{'/'.join(i for i in plugin_config.bingchat_command_history_chat)}"""
        f"""\n\n"""
        f"""如果有任何疑问请查看https://github.com/Harry-Jing/nonebot-plugin-bing-chat"""
    )
    if '' in plugin_config.command_start
    else (
        f"""以下所有的命令都要在开头加上命令符号！！！"""
        f"""\n\n"""
        f"""命令符号：{','.join(f'"{i}"' for i in plugin_config.command_start)}"""
        f"""\n\n"""
        f"""开始对话：{'/'.join(i for i in plugin_config.bingchat_command_chat)} + {{你要询问的内容}}"""
        f"""\n\n"""
        f"""新建一个对话：{'/'.join(i for i in plugin_config.bingchat_command_new_chat)}"""
        f"""\n\n"""
        f"""查看历史记录：{'/'.join(i for i in plugin_config.bingchat_command_history_chat)}"""
        f"""\n\n"""
        f"""如果有任何疑问请查看https://github.com/Harry-Jing/nonebot-plugin-bing-chat"""
    )
)


def is_confilct_with_other_matcher(msg: str) -> bool:
    return True if re.match(_matcher_in_regex, msg) else False


def create_log(data: str) -> None:
    current_log_directory = (
        plugin_directory / 'log' / datetime.now().strftime('%Y-%m-%d')
    )
    current_log_directory.mkdir(parents=True, exist_ok=True)
    current_log_file = (
        current_log_directory / f'{datetime.now().strftime("%H-%M-%S")}.log'
    )
    current_log_file.write_text(data=str(data), encoding='utf-8')
