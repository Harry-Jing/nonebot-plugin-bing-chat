import json
import shutil
import importlib
from datetime import datetime, timedelta

from nonebot import require, get_driver
from nonebot.rule import Rule, to_me, command
from nonebot.plugin.on import on_message

from .data_model import PluginData, PluginConfig

plugin_config = PluginConfig.parse_obj(get_driver().config)

plugin_data = PluginData()


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

COMMON_HELP_MESSAGE = (
    f"开始对话：{'/'.join(plugin_config.bingchat_command_chat)} + {{你要询问的内容}}\n\n"
    f"新建一个对话：{'/'.join(plugin_config.bingchat_command_new_chat)}\n\n"
    f"查看历史记录：{'/'.join(plugin_config.bingchat_command_history_chat)}\n\n"
    '如果有任何疑问请查看https://github.com/Harry-Jing/nonebot-plugin-bing-chat'
)
if '' in plugin_config.command_start:
    HELP_MESSAGE = COMMON_HELP_MESSAGE
else:
    command_symbols = ','.join(f'"{i}"' for i in plugin_config.command_start)
    HELP_MESSAGE = (
        f'以下所有的命令都要在开头加上命令符号！！！\n\n'
        f'命令符号：{command_symbols}\n\n'
        f'{COMMON_HELP_MESSAGE}'
    )


def init() -> None:
    plugin_directory = plugin_config.bingchat_plugin_directory
    plugin_directory.mkdir(parents=True, exist_ok=True)

    # 检查cookie文件是否存在且不为空, 并放入配置文件中
    plugin_cookies_path = plugin_directory / 'cookies'
    plugin_cookies_path.mkdir(parents=True, exist_ok=True)
    plugin_cookies_file_path_list = list(plugin_cookies_path.glob('*.json'))

    if not plugin_cookies_file_path_list:
        (plugin_cookies_path / 'cookies.json').touch(exist_ok=True)
        raise RuntimeError(
            'BingChat插件未配置cookie，请在./data/BingChat/cookies/cookies.json中填入你的cookie'
        )
    for cookies_file_path in plugin_cookies_file_path_list:
        if cookies_file_path.stat().st_size == 0:
            raise RuntimeError(f'BingChat插件未配置cookie，请在{cookies_file_path}中填入你的cookie')
        try:
            with open(cookies_file_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except Exception as exc:
            raise RuntimeError(
                f'BingChat插件配置的cookie不是一个合法的json，请检查{cookies_file_path}'
            ) from exc

    plugin_data.cookies_file_path_list = plugin_cookies_file_path_list
    plugin_data.current_cookies_file_path = plugin_data.cookies_file_path_list[0]

    # 创建log文件夹
    plugin_log_directory = plugin_directory / 'log'
    plugin_log_directory.mkdir(parents=True, exist_ok=True)

    # 检查依赖
    if any(i == 'image' for i, _ in plugin_config.bingchat_display_content_types):
        require('nonebot_plugin_apscheduler')
        try:
            importlib.import_module('nonebot_plugin_htmlrender')
        except Exception as exc:
            raise RuntimeError(
                '请使用 pip install nonebot-plugin-bing-chat[image] markdown渲染插件'
            ) from exc


init()


from nonebot_plugin_apscheduler import scheduler


@scheduler.scheduled_job('cron', hour=2)  # type: ignore
async def _del_log_file() -> None:
    print('del_log_file')
    current_time = datetime.now()
    plugin_log_directory = plugin_config.bingchat_plugin_directory / 'log'
    for child_dir in plugin_log_directory.iterdir():
        if current_time - datetime.fromisoformat(child_dir.name) > timedelta(days=7):
            shutil.rmtree(child_dir)
