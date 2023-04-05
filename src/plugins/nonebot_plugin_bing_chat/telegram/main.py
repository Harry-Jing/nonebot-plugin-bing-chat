from nonebot.log import logger
from nonebot.params import CommandArg, EventMessage
from nonebot.matcher import Matcher
from nonebot.adapters.telegram.bot import Bot
from nonebot.adapters.telegram.event import (
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)
from nonebot.adapters.telegram.message import Message

from .utils import reply_out, default_get_user_data, get_display_message_list
from ..common import (
    HELP_MESSAGE,
    plugin_data,
    command_chat,
    plugin_config,
    command_new_chat,
    command_history_chat,
)
from ..common.utils import (
    get_chatbot,
    store_response,
    get_bing_response,
    check_if_user_is_waiting_for_response,
)
from ..common.data_model import Sender, UserData, UserInfo
from ..common.exceptions import BaseBingChatException, BingChatResponseException


@command_chat.handle()
async def bingchat_command_chat(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
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
    # TODO: 撤回消息

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
            raise NotImplementedError('暂不支持合并转发')  # TODO: 合并转发

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
                    platform='telegram', user_id=event.from_.id
                )
    except BingChatResponseException as exc:
        await matcher.finish(reply_out(event, f'<调用content_simple时出错>\n{str(exc)}'))
    finally:
        await chatbot.close()


@command_new_chat.handle()
async def bingchat_command_new_chat(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
    depth: int = 1,
) -> None:
    current_user_data = default_get_user_data(
        event=event, user_data_dict=plugin_data.user_data_dict
    )

    await current_user_data.clear(
        sender=Sender(
            user_id=event.from_.id,
            user_name=event.from_.username or '<未知的的用户名>',
        )
    )

    await matcher.send(reply_out(event, '已刷新对话'))

    # 如果arg不为空
    if arg:
        await bingchat_command_chat(
            bot=bot, event=event, matcher=matcher, arg=arg, depth=depth
        )
