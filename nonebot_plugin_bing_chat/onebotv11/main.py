from typing import Optional

from EdgeGPT import Chatbot
from nonebot import Bot
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventMessage

from ..common.dataModel import (
    BingChatResponse,
    Conversation,
)
from ..common.exceptions import (
    BaseBingChatException,
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
    BingChatResponseException,
)
from ..common.utils import (
    command_chat,
    command_history_chat,
    command_new_chat,
    createLog,
    helpMessage,
    plugin_config,
)
from .check import CheckIfInList, CheckIfUserIsWaitingForResponse
from .utils import (
    UserData,
    historyOut,
    matcher_reply_to_continue_chat,
    reply_message_id_dict,
    replyOut,
    user_data_dict,
)


@command_chat.handle()
async def bingchat_command_chat(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
    user_data: Optional[UserData] = None,
) -> None:
    # 如果arg为空，则返回帮助信息
    if not arg:
        await matcher.finish(helpMessage())

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    if user_data:
        current_user_data = user_data
    else:
        current_user_data = user_data_dict.setdefault(
            event.sender.user_id, UserData(sender=event.sender)  # type: ignore
        )

    if not current_user_data.first_ask_message_id:
        current_user_data.first_ask_message_id = event.message_id

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
        if plugin_config.bingchat_show_is_waiting:
            message_is_asking = await matcher.send(replyOut(event.message_id, '正在请求'))
        current_user_data.is_waiting = True
        user_input_text = arg.extract_plain_text()
        response = await chatbot.ask(
            prompt=user_input_text,
            conversation_style=plugin_config.bingchat_conversation_style,
        )
        """ from ..example_data import get_example_response
        user_input_text = 'python的asyncio库是干什么的'
        response = get_example_response() """
    except Exception as exc:
        await matcher.send(replyOut(event.message_id, f'<无法询问，如果出现多次请试刷新>\n{exc}'))
        raise exc
    finally:
        current_user_data.is_waiting = False
        if plugin_config.bingchat_show_is_waiting:
            await bot.delete_msg(message_id=message_is_asking['message_id'])

    # 检查后保存响应值
    try:
        if plugin_config.bingchat_log:
            createLog(str(response))
        current_user_data.history.append(
            Conversation(ask=user_input_text, reply=BingChatResponse(raw=response))
        )
    except BingChatAccountReachLimitException as exc:
        await matcher.finish(replyOut(event.message_id, f'<请尝联系管理员>\n{exc}'))
    except BingChatConversationReachLimitException as exc:
        if plugin_config.bingchat_auto_refresh_conversation:
            await matcher.send(replyOut(event.message_id, '检测到达到对话上限，将自动刷新对话'))
            await bingchat_command_new_chat(
                bot=bot, event=event, matcher=matcher, arg=arg
            )
            await matcher.finish()
        await matcher.finish(replyOut(event.message_id, f'<请尝试刷新>\n{exc}'))
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, f'<处理响应值值时出错>\n{exc}'))

    # 发送响应值
    try:
        if plugin_config.bingchat_show_detail:
            data = await matcher.send(
                replyOut(
                    event.message_id,
                    current_user_data.history[-1].reply.content_with_reference,
                )
            )
        else:
            data = await matcher.send(
                replyOut(
                    event.message_id, current_user_data.history[-1].reply.content_simple
                )
            )
        reply_message_id_dict[data['message_id']] = current_user_data.sender.user_id  # type: ignore
    except BingChatResponseException as exc:
        await matcher.finish(
            replyOut(event.message_id, f'<调用content_simple时出错>\n{str(exc)}')
        )
    finally:
        await chatbot.close()


@command_new_chat.handle()
async def bingchat_command_new_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
) -> None:
    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    current_user_data = user_data_dict.setdefault(
        event.sender.user_id, UserData(sender=event.sender)  # type: ignore
    )

    current_user_data.sender = event.sender
    current_user_data.chatbot = None
    current_user_data.conversation_count = 0
    current_user_data.history = []

    await matcher.send(replyOut(event.message_id, '已刷新对话'))

    # 如果arg不为空
    if arg:
        await bingchat_command_chat(bot=bot, event=event, matcher=matcher, arg=arg)


@command_history_chat.handle()
async def bingchat_command_history_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
) -> None:
    # 如果arg不为空
    if arg:
        await matcher.finish(replyOut(event.message_id, '此命令没有参数，不要在命令后加别的内容'))

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        CheckIfInList(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(replyOut(event.message_id, str(exc)))

    current_user_data = user_data_dict.setdefault(
        event.sender.user_id, UserData(sender=event.sender)  # type: ignore
    )

    # 如果该用户没有历史记录则终止
    if not current_user_data.history:
        await matcher.finish(replyOut(event.message_id, '您没有历史对话'))

    nodes = historyOut(bot, current_user_data)

    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=nodes)
    if isinstance(event, PrivateMessageEvent):
        await bot.send_private_forward_msg(user_id=event.sender.user_id, messages=nodes)


@matcher_reply_to_continue_chat.handle()
async def bingchat_message_all(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = EventMessage()
) -> None:
    # 检查是否回复的是自己的对话
    logger.debug(reply_message_id_dict[event.reply.message_id])  # type: ignore
    if (
        not plugin_config.bingchat_share_chat
        and event.sender.user_id != reply_message_id_dict[event.reply.message_id]  # type: ignore
    ):
        logger.error(f'用户{event.sender.user_id}试图继续别人的对话')

    # 获取最开始发送的用户数据
    current_user_data = user_data_dict[reply_message_id_dict[event.reply.message_id]]  # type: ignore

    await bingchat_command_chat(
        bot=bot,
        event=event,
        matcher=matcher,
        arg=arg,
        user_data=current_user_data,
    )
