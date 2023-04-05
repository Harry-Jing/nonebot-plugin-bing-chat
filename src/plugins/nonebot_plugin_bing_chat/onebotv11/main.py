from nonebot.log import logger
from nonebot.params import CommandArg, EventMessage
from nonebot.matcher import Matcher
from nonebot.adapters import Bot
from nonebot_plugin_guild_patch import GuildMessageEvent
from nonebot.adapters.onebot.v11.event import (
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11.message import Message

from .check import check_if_in_list, check_if_user_is_waiting_for_response
from .utils import (
    reply_out,
    history_out,
    default_get_user_data,
    get_display_message_list,
    get_display_message_forward,
    matcher_reply_to_continue_chat,
)
from ..common import (
    HELP_MESSAGE,
    plugin_data,
    command_chat,
    plugin_config,
    command_new_chat,
    command_history_chat,
)
from ..common.utils import get_chatbot, store_response, get_bing_response
from ..common.data_model import Sender, UserData, UserInfo
from ..common.exceptions import BaseBingChatException, BingChatResponseException


@command_chat.handle()
async def bingchat_command_chat(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
    user_data: UserData | None = None,
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

    # 获取当前用户数据
    current_user_data = user_data or default_get_user_data(
        event=event, user_data_dict=plugin_data.user_data_dict
    )

    # 检查用户是否有对话在进行中，如果有则终止
    try:
        check_if_user_is_waiting_for_response(user_data=current_user_data)
    except BaseBingChatException as exc:
        await matcher.finish(reply_out(event, str(exc)))

    # 创建一些常用变量
    user_input_text = arg.extract_plain_text()
    base_data = {
        'event': event,
        'matcher': matcher,
        'user_data': current_user_data,
        'reply_out': reply_out,
    }

    # 获取Chatbot，如果没有则创建一个
    chatbot = await get_chatbot(
        **base_data,
    )

    # 发送“正在请求的消息”，并存储message_id
    message_is_asking_data = None
    if plugin_config.bingchat_display_is_waiting:
        message_is_asking_data = await matcher.send(reply_out(event, '正在请求'))

    # 向Bing发送请求, 并获取响应值
    response = await get_bing_response(
        **base_data,
        chatbot=chatbot,
        user_question=user_input_text,
    )

    # 撤回“正在请求的消息”
    if message_is_asking_data and not isinstance(event, GuildMessageEvent):
        await bot.delete_msg(message_id=message_is_asking_data['message_id'])

    # 检查后保存响应值
    await store_response(
        **base_data,
        new_chat_handler=(
            bingchat_command_chat,
            {
                'bot': bot,
                'event': event,
                'matcher': matcher,
                'arg': arg,
                'user_data': current_user_data,
                'depth': depth,
            },
        ),
        response=response,
        user_question=user_input_text,
    )

    # 发送Bing的回答
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
        await bingchat_command_chat(
            bot=bot, event=event, matcher=matcher, arg=arg, depth=depth
        )


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
