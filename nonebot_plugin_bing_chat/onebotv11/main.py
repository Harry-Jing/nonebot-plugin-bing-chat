from EdgeGPT import Chatbot

from nonebot import Bot
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from nonebot_plugin_apscheduler import scheduler

from ..common.exceptions import (
    BaseBingChatException,
    BingChatConversationReachLimitException,
)

from .check import CheckIfInList, CheckIfUserIsWaitingForResponse
from .utils import *


user_data_dict: dict[int, UserData] = dict()


@command_chat.handle()
async def bing_chat_command_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
):
    # 如果arg为空，则返回帮助信息
    if not arg:
        await matcher.finish(helpMessage())

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    # 检查用户是否有对话在进行中，如果有则终止
    try:
        CheckIfUserIsWaitingForResponse(event=event, user_data=current_user_data)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    # 获取Chatbot，如果没有则创建一个
    try:
        if not current_user_data.chatbot:
            current_user_data.chatbot = Chatbot(
                cookiePath='./data/BingChat/cookies.json'
            )
    except Exception as exc:
        await matcher.send(replyOut(event.message_id, f'<无法创建Chatbot>\n{exc}'))
        raise exc
    else:
        chatbot = current_user_data.chatbot

    # 向Bing发送请求, 并获取响应值
    try:
        message_is_asking = await matcher.send(replyOut(event.message_id, '正在请求'))
        current_user_data.is_waiting = True
        user_input_text = arg.extract_plain_text()
        response = await chatbot.ask(prompt=user_input_text)
        # from ..example_data import get_example_response
        # user_input_text = 'python的asyncio库是干什么的'
        # response = get_example_response()
    except Exception as exc:
        await matcher.send(replyOut(event.message_id, f'<无法询问，如果出现多次请试刷新>\n{exc}'))
        raise exc
    finally:
        current_user_data.is_waiting = False
        await bot.delete_msg(message_id=message_is_asking['message_id'])

    # 检查后保存响应值
    try:
        current_user_data.history.append(
            Conversation(ask=user_input_text, reply=BingChatResponse(raw=response))
        )
    except BingChatAccountReachLimitException as exc:
        await matcher.finish(replyOut(event.message_id, f'<请尝联系管理员>\n{exc}'))
    except BingChatConversationReachLimitException as exc:
        if plugin_config.bingchat_auto_refresh_conversation:
            await matcher.send(replyOut(event.message_id, f'检测到达到对话上限，将自动刷新对话'))
            await bing_chat_command_new_chat(bot=bot, event=event, matcher=matcher, arg=arg)
            await matcher.finish()
        await matcher.finish(replyOut(event.message_id, f'<请尝试刷新>\n{exc}'))
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, f'<处理响应值值时出错>\n{exc}'))

    # 发送响应值
    try:
        await matcher.send(
            replyOut(
                event.message_id, current_user_data.history[-1].reply.content_simple
            )
        )
    except BingChatResponseException as exc:
        logger.error(current_user_data.history[-1].reply.raw)
        await matcher.finish(
            replyOut(event.message_id, f'<调用content_simple时出错>\n{str(exc)}')
        )
    finally:
        await chatbot.close()


@command_new_chat.handle()
async def bing_chat_command_new_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
):
    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    current_user_data.sender = event.sender
    current_user_data.chatbot = None
    current_user_data.conversation_count = 0
    current_user_data.history = []

    await matcher.send(replyOut(event.message_id, '已刷新对话'))

    # 如果arg不为空
    if arg:
        await bing_chat_command_chat(bot=bot, event=event, matcher=matcher, arg=arg)


@command_history_chat.handle()
async def bing_chat_command_history_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
):
    # 如果arg不为空
    if arg:
        await matcher.finish(replyOut(event.message_id, '此命令没有参数，不要在命令后加别的内容'))

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    # 如果该用户没有历史记录则终止
    if not current_user_data.history:
        await matcher.finish(replyOut(event.message_id, '您没有历史对话'))

    current_user_data = user_data_dict[event.sender.user_id]
    msg = historyOut(bot, current_user_data)

    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=msg)
    if isinstance(event, PrivateMessageEvent):
        await bot.send_private_forward_msg(user_id=event.user_id, messages=msg)
