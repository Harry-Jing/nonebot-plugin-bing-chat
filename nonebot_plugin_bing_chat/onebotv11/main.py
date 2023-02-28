from EdgeGPT import Chatbot

from nonebot import Bot
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.plugin.on import on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from nonebot_plugin_apscheduler import scheduler

from ..exceptions import BaseBingChatException

from .check import CheckIfInList, CheckIfUserIsWaitingForResponse
from .utils import *


user_data_dict: dict[int, UserData] = dict()


command_chat = on_command(
    cmd=plugin_config['bingchat_command_chat'][0],
    aliases=set(plugin_config['bingchat_command_chat'][1:]),
)
command_new_chat = on_command(
    cmd=plugin_config['bingchat_command_new_chat'][0],
    aliases=set(plugin_config['bingchat_command_new_chat'][1:]),
)
command_history_chat = on_command(
    cmd=plugin_config['bingchat_command_history_chat'][0],
    aliases=set(plugin_config['bingchat_command_history_chat'][1:]),
)


@command_chat.handle()
async def bing_chat_command_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
):
    # 如果arg为空，则返回帮助信息
    if not arg:
        await matcher.finish(helpMessage())

    # 检查用户和群组是否在名单中，如果没有则抛出异常
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(str(exc))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    # 检查用户是否有对话在进行中，如果有则抛出异常
    try:
        CheckIfUserIsWaitingForResponse(event=event, user_data=current_user_data)
    except BaseBingChatException as exc:
        await matcher.finish(str(exc))

    # 创建Chatbot
    try:
        if not current_user_data.chatbot:
            current_user_data.chatbot = Chatbot(
                cookiePath='./data/BingChat/cookies.json'
            )
    except Exception as exc:
        await matcher.send(f'<无法创建Chatbot>\n{exc}')
        raise exc
    else:
        chatbot = current_user_data.chatbot

    # 询问Bing, 并获取响应值
    try:
        message_is_asking = await matcher.send(replyOut(event.message_id, '正在请求'))
        current_user_data.is_waiting = True
        user_input_text = arg.extract_plain_text()
        response = await chatbot.ask(prompt=user_input_text)
        # user_input_text = 'python的asyncio库是干什么的'
        # from ..example_data import response
    except Exception as exc:
        await matcher.send(f'<无法询问>\n{exc}')
        raise exc
    else:
        current_user_data.history.append(
            Conversation(ask=user_input_text, reply=BingChatResponse(raw=response))
        )
    finally:
        current_user_data.is_waiting = False
        await bot.delete_msg(message_id=message_is_asking['message_id'])

    # 发送响应值
    try:
        await matcher.send(
            replyOut(
                event.message_id, current_user_data.history[-1].reply.content_simple
            )
        )
    except BingChatResponseException as exc:
        await matcher.finish(str(exc))
    finally:
        await chatbot.close()


@command_new_chat.handle()
async def bing_chat_command_new_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
):
    # 检查权限，如果没有权限则抛出异常
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(str(exc))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    await current_user_data.chatbot.close()
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

    # 检查权限，如果没有权限则抛出异常
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(str(exc))

    current_user_data = getUserDataSafe(user_data_dict=user_data_dict, event=event)

    # 如果该用户没有历史记录 则停止返回历史记录
    if not current_user_data.history:
        await matcher.finish(replyOut(event.message_id, '您没有历史对话'))

    current_user_data = user_data_dict[event.sender.user_id]
    msg = historyOut(bot, current_user_data)

    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=msg)
    if isinstance(event, PrivateMessageEvent):
        await bot.send_private_forward_msg(user_id=event.user_id, messages=msg)
