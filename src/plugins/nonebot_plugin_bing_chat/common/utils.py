import asyncio
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable, ParamSpec

from EdgeGPT import Chatbot
from nonebot.adapters import Bot, Event, Message, MessageSegment
from nonebot.log import logger
from nonebot.matcher import Matcher

from nonebot.adapters.onebot.v11 import (
    MessageEvent as OB11MessageEvent,
    GroupMessageEvent as OB11GroupMessageEvent,
    PrivateMessageEvent as OB11PrivateMessageEvent,
)

from . import plugin_config, plugin_data
from .data_model import (
    DisplayContentType,
    BingChatResponse,
    UserData,
    Conversation,
    Sender,
)
from .exceptions import (
    BaseBingChatException,
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
    BingChatInvalidSessionException,
)

if any(i == 'image' for i, _ in plugin_config.bingchat_display_content_types):
    from nonebot_plugin_htmlrender import md_to_pic

_matcher_in_regex = '|'.join(
    (
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_new_chat)}).*)""",
        f"""(({'|'.join(plugin_config.command_start)})({'|'.join(plugin_config.bingchat_command_history_chat)}).*)""",
    )
)


def is_conflict_with_other_matcher(msg: str) -> bool:
    return bool(re.match(_matcher_in_regex, msg))


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
    current_log_file.write_text(data=data, encoding='utf-8')


async def check_cookies_usable(cookies: Path) -> bool:
    chatbot = Chatbot(
        cookiePath=str(cookies),
        proxy=plugin_config.bingchat_proxy,
    )
    try:
        BingChatResponse(raw=(await chatbot.ask('Hello')))
    except BingChatAccountReachLimitException:
        return False
    except Exception as exc:
        logger.error(f'在检查cookies：{cookies} 时出错')
        logger.error(exc)
        return False
    else:
        return True


async def switch_to_usable_cookies() -> bool:
    plugin_data.is_switching_cookies = True

    try:
        task_result = await asyncio.gather(
            check_cookies_usable(cookies)
            for cookies in plugin_data.cookies_file_path_list
        )
    except Exception:
        plugin_data.is_switching_cookies = False
        raise

    for cookies, result in zip(plugin_data.cookies_file_path_list, task_result):
        if result:
            plugin_data.current_cookies_file_path = cookies
            plugin_data.is_switching_cookies = False
            return True

    plugin_data.is_switching_cookies = False
    return False


async def get_display_data(
    user_data: UserData, display_content_type: DisplayContentType
) -> str | bytes:
    plain_text_list = []
    display_type, content_type_list = display_content_type
    for content_type in content_type_list:
        if not (content := user_data.latest_response.get_content(content_type)):
            continue
        match display_type:
            case 'text':
                match content_type:
                    case 'reference':
                        new_content = '参考链接：\n'
                    case 'suggested-question':
                        new_content = '猜你想问：\n'
                    case 'num-max-conversation':
                        new_content = '回复数：'
                    case _:
                        new_content = ''

            case 'image':
                match content_type:
                    case 'reference':
                        new_content = '参考链接：\n\n'
                    case 'suggested-question':
                        new_content = '猜你想问：\n\n'
                    case 'num-max-conversation':
                        new_content = '回复数：'
                    case _:
                        new_content = ''
        plain_text_list.append(f'{new_content}{content}')

    match display_type:
        case 'text':
            return '\n\n'.join(plain_text_list)
        case 'image':
            return await md_to_pic('\n\n---\n\n'.join(plain_text_list))


# 下面是主要逻辑的函数

async def get_chatbot(
    event: Event,
    matcher: Matcher,
    user_data: UserData,
    reply_out: Callable[[Event, str | Message | MessageSegment], Message],
) -> Chatbot:
    try:
        if not user_data.chatbot:
            user_data.chatbot = Chatbot(
                cookiePath=plugin_data.current_cookies_file_path,  # type: ignore 应该支持Path的
                proxy=plugin_config.bingchat_proxy,
            )
    except Exception as exc:
        await matcher.send(reply_out(event, f'<无法创建Chatbot>\n{exc}'))
        raise exc
    else:
        return user_data.chatbot

async def get_bing_response(
    event: Event,
    matcher: Matcher,
    user_data: UserData,
    reply_out: Callable[[Event, str | Message | MessageSegment], Message],
    chatbot: Chatbot,
    user_question: str,
) -> dict:
    message_is_asking_data = None
    # 向Bing发送请求, 并获取响应值
    try:
        user_data.is_waiting = True
        response = await chatbot.ask(  
            prompt=user_question,
            conversation_style=plugin_config.bingchat_conversation_style,
        )
        """ from ..example_data import get_example_response
        user_question = 'python中asyncio有什么用，并举例代码'
        response = get_example_response() """
    except Exception as exc:
        await matcher.send(reply_out(event, f'<无法询问，如果出现多次请试刷新>\n{exc}'))
        raise exc
    else:
        return response
    finally:
        user_data.is_waiting = False


async def store_response(
    event: Event,
    matcher: Matcher,
    user_data: UserData,
    reply_out: Callable[[Event, str | Message | MessageSegment], Message],
    new_chat_handler: tuple[Callable[..., Awaitable], dict],
    response: dict,
    user_question: str,
) -> None:
    try:
        if plugin_config.bingchat_log:
            create_log(json.dumps(response))
        user_data.history.append(
            Conversation(ask=user_question, response=BingChatResponse(raw=response))
        )
    except BingChatAccountReachLimitException as exc:
        if plugin_config.bingchat_auto_switch_cookies:
            await matcher.send(reply_out(event, '检测到达到账户上限，将自动刷新账户，所有对话将被清空'))
            if not await switch_to_usable_cookies():
                await matcher.finish('无可用cookies')
            for user_data in plugin_data.user_data_dict.values():
                if isinstance(event, OB11MessageEvent):
                    await user_data.clear(
                        sender=Sender(
                            user_id=event.user_id,
                            user_name=(event.sender.nickname or '<未知的的用户名>'),
                        )
                    )
            await matcher.finish('已切换cookies')
        await matcher.finish(reply_out(event, f'<请尝联系管理员>\n{exc}'))
    except (
        BingChatConversationReachLimitException,
        BingChatInvalidSessionException,
    ) as exc:
        if plugin_config.bingchat_auto_refresh_conversation:
            if isinstance(exc, BingChatConversationReachLimitException):
                await matcher.send(reply_out(event, '检测到达到对话上限，将自动刷新对话'))
            if isinstance(exc, BingChatConversationReachLimitException):
                await matcher.send(reply_out(event, '检测到达到对话过期，将自动刷新对话'))
            logger.debug(f'{new_chat_handler=}')
            await new_chat_handler[0](**new_chat_handler[1])
            await matcher.finish()
        await matcher.finish(reply_out(event, f'<请尝试刷新>\n{exc}'))
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, f'<处理响应值值时出错>\n{exc}'))
