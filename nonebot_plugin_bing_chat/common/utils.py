import re
import asyncio
from pathlib import Path
from datetime import datetime

from EdgeGPT import Chatbot

from nonebot import get_driver
from nonebot.log import logger
from nonebot.rule import Rule, command, to_me
from nonebot.plugin.on import on_message

from . import plugin_config, plugin_data
from .data_model import BingChatResponse
from .exceptions import BingChatAccountReachLimitException

_matcher_in_regex = '|'.join(
    (
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_new_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_history_chat)}).*)""",
    )
)


def is_confilct_with_other_matcher(msg: str) -> bool:
    return True if re.match(_matcher_in_regex, msg) else False


def create_log(data: str) -> None:
    current_log_directory = (
        plugin_config.bingchat_plugin_directory
        / 'log'
        / datetime.now().strftime('%Y-%m-%d')
    )
    current_log_directory.mkdir(parents=True, exist_ok=True)
    current_log_file = (
        current_log_directory / f'{datetime.now().strftime("%H-%M-%S")}.log'
    )
    current_log_file.write_text(data=str(data), encoding='utf-8')


async def check_cookies_useable(cookies: Path) -> bool:
    chatbot = Chatbot(
        cookiePath=cookies,
        proxy=plugin_config.bingchat_proxy,
    )
    try:
        response = BingChatResponse(raw=(await chatbot.ask('Hello')))
    except BingChatAccountReachLimitException:
        return False
    except Exception as exc:
        logger.error(f'在检查cookies：{cookies} 时出错')
        logger.error(exc)
        return False
    else:
        return True


async def switch_to_useable_cookies() -> bool:
    try:
        plugin_data.is_switching_cookies = True
        task_result = await asyncio.gather(
            check_cookies_useable(cookies)
            for cookies in plugin_data.cookies_file_path_list
        )
        for cookies, result in zip(plugin_data.cookies_file_path_list, task_result):
            if result:
                plugin_data.current_cookies_file_path = cookies
                break
        else:
            return False

    except Exception as exc:
        raise exc

    finally:
        plugin_data.is_switching_cookies = False
        return True
