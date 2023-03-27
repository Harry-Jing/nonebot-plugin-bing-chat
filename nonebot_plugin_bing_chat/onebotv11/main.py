import json
from typing import Optional

from EdgeGPT import Chatbot
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventMessage
from nonebot_plugin_guild_patch import GuildMessageEvent

from ..common import (
    HELP_MESSAGE,
    command_chat,
    command_history_chat,
    command_new_chat,
    plugin_config,
    plugin_data,
)
from ..common.data_model import (
    BingChatResponse,
    Conversation,
    Sender,
    UserData,
    UserInfo,
)
from ..common.exceptions import (
    BaseBingChatException,
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
    BingChatInvalidSessionException,
    BingChatResponseException,
)
from ..common.utils import (
    create_log,
    switch_to_usable_cookies,
)
from .check import check_if_in_list, check_if_user_is_waiting_for_response
from .utils import (
    default_get_user_data,
    get_display_message_forward,
    get_display_message_list,
    history_out,
    matcher_reply_to_continue_chat,
    reply_out,
)


@command_chat.handle()
async def bingchat_command_chat(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
    user_data: Optional[UserData] = None,
    depth: int = 1,
) -> None:
    # 防止无线递归
    if depth >= 3:
        return
    else:
        depth += 1

    # 如果arg为空，则返回帮助信息
    if not arg:
        await matcher.finish(HELP_MESSAGE)

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        check_if_in_list(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, str(exc)))

    if plugin_data.is_switching_cookies:
        await matcher.finish(reply_out(event, '正在切换cookies，请稍后再试'))

    current_user_data = user_data or default_get_user_data(
        event=event, user_data_dict=plugin_data.user_data_dict
    )

    if not current_user_data.first_ask_message_id:
        current_user_data.first_ask_message_id = event.message_id

    # 检查用户是否有对话在进行中，如果有则终止
    try:
        check_if_user_is_waiting_for_response(event=event, user_data=current_user_data)
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, str(exc)))

    # 获取Chatbot，如果没有则创建一个
    try:
        if not current_user_data.chatbot:
            current_user_data.chatbot = Chatbot(
                cookiePath=plugin_data.current_cookies_file_path,  # type: ignore 应该支持Path的
                proxy=plugin_config.bingchat_proxy,
            )
    except Exception as exc:
        await matcher.send(reply_out(event, f'<无法创建Chatbot>\n{exc}'))
        raise exc
    else:
        chatbot = current_user_data.chatbot

    message_is_asking = None
    # 向Bing发送请求, 并获取响应值
    try:
        if plugin_config.bingchat_display_is_waiting:
            message_is_asking = await matcher.send(reply_out(event, '正在请求'))
        current_user_data.is_waiting = True
        user_input_text = arg.extract_plain_text()
        response = await chatbot.ask(
            prompt=user_input_text,
            conversation_style=plugin_config.bingchat_conversation_style,
        )
        """ from ..example_data import get_example_response
        user_input_text = 'python中asyncio有什么用，并举例代码'
        response = get_example_response() """
    except Exception as exc:
        await matcher.send(reply_out(event, f'<无法询问，如果出现多次请试刷新>\n{exc}'))
        raise exc
    finally:
        current_user_data.is_waiting = False
        if message_is_asking:
            await bot.delete_msg(message_id=message_is_asking['message_id'])

    # 检查后保存响应值
    try:
        if plugin_config.bingchat_log:
            create_log(json.dumps(response))
        current_user_data.history.append(
            Conversation(ask=user_input_text, response=BingChatResponse(raw=response))
        )
    except BingChatAccountReachLimitException as exc:
        if plugin_config.bingchat_auto_switch_cookies:
            await matcher.send(reply_out(event, '检测到达到账户上限，将自动刷新账户，所有对话将被清空'))
            if not await switch_to_usable_cookies():
                await matcher.finish('无可用cookies')
            for user_data in plugin_data.user_data_dict.values():
                await user_data.clear(
                    sender=Sender(
                        user_id=event.user_id,
                        user_name=(event.sender.nickname or '<未知的的用户名>'),
                    )
                )
            await matcher.finish('已切换cookies')
        await matcher.finish(reply_out(event, f'<请尝联系管理员>\n{exc}'))
    except (BingChatConversationReachLimitException,BingChatInvalidSessionException) as exc:
        if plugin_config.bingchat_auto_refresh_conversation:
            if isinstance(exc, BingChatConversationReachLimitException):
                await matcher.send(reply_out(event, '检测到达到对话上限，将自动刷新对话'))
            if isinstance(exc, BingChatConversationReachLimitException):
                await matcher.send(reply_out(event, '检测到达到对话过期，将自动刷新对话'))
            await bingchat_command_new_chat(
                bot=bot, event=event, matcher=matcher, arg=arg, depth=depth
            )
            await matcher.finish()
        await matcher.finish(reply_out(event, f'<请尝试刷新>\n{exc}'))
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, f'<处理响应值值时出错>\n{exc}'))

    # 发送响应值
    try:
        # 合并转发
        if plugin_config.bingchat_display_in_forward:
            msg = await get_display_message_forward(current_user_data=current_user_data)
            if isinstance(event, GroupMessageEvent):
                await bot.send_group_forward_msg(group_id=event.group_id, messages=msg)
            elif isinstance(event, PrivateMessageEvent):
                await bot.send_private_forward_msg(user_id=event.user_id, messages=msg)

        # 直接发送
        else:
            msg_list = await get_display_message_list(
                current_user_data=current_user_data
            )
            for i, msg in enumerate(msg_list):
                data = await matcher.send(
                    msg if i else reply_out(event=event, content=msg)
                )
                plugin_data.reply_message_id_dict[data['message_id']] = UserInfo(
                    platform='qq', user_id=event.user_id
                )
    except BingChatResponseException as exc:
        await matcher.finish(reply_out(event, f'<调用content_simple时出错>\n{str(exc)}'))
    finally:
        await chatbot.close()


@command_new_chat.handle()
async def bingchat_command_new_chat(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
    depth: int = 1,
) -> None:
    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        check_if_in_list(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, str(exc)))

    current_user_data = default_get_user_data(
        event=event, user_data_dict=plugin_data.user_data_dict
    )

    await current_user_data.clear(
        sender=Sender(
            user_id=event.user_id,
            user_name=event.sender.nickname or '<未知的的用户名>',
        )
    )

    await matcher.send(reply_out(event, '已刷新对话'))

    # 如果arg不为空
    if arg:
        await bingchat_command_chat(bot=bot, event=event, matcher=matcher, arg=arg, depth=depth)


@command_history_chat.handle()
async def bingchat_command_history_chat(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()
) -> None:
    if isinstance(event, GuildMessageEvent):
        await matcher.finish('频道不支持合并转发，无法使用该功能！')

    # 如果arg不为空
    if arg:
        await matcher.finish(reply_out(event, '此命令没有参数，不要在命令后加别的内容'))

    # 检查用户和群组是否在名单中，如果没有则终止
    try:
        check_if_in_list(event=event)
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, str(exc)))

    current_user_data = default_get_user_data(
        event=event, user_data_dict=plugin_data.user_data_dict
    )

    # 如果该用户没有历史记录则终止
    if not current_user_data.history:
        await matcher.finish(reply_out(event, '您没有历史对话'))

    msg = history_out(bot, current_user_data)

    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=msg)
    if isinstance(event, PrivateMessageEvent):
        await bot.send_private_forward_msg(user_id=event.user_id, messages=msg)


@matcher_reply_to_continue_chat.handle()
async def bingchat_message_all(
    bot: Bot, event: MessageEvent, matcher: Matcher, arg: Message = EventMessage()
) -> None:
    if not event.reply:
        raise Exception('这句话不应该出现')

    # 检查是否回复的是自己的对话
    if (
        not plugin_config.bingchat_share_chat
        and event.sender.user_id
        != plugin_data.reply_message_id_dict[event.reply.message_id]
    ):
        logger.error(f'用户{event.sender.user_id}试图继续别人的对话')

    # 获取最开始发送的用户数据
    current_user_data = plugin_data.user_data_dict[
        plugin_data.reply_message_id_dict[event.reply.message_id]
    ]

    await bingchat_command_chat(
        bot=bot,
        event=event,
        matcher=matcher,
        arg=arg,
        user_data=current_user_data,
    )
