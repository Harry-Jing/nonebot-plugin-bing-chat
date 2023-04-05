from nonebot.rule import Rule
from nonebot.params import EventToMe
from nonebot.plugin.on import on_message
from nonebot_plugin_guild_patch import GuildMessageEvent
from nonebot.adapters.telegram.event import (
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)
from nonebot.adapters.telegram.message import Message, MessageSegment

from ..common import plugin_data, plugin_config
from ..common.utils import get_display_data, is_conflict_with_other_matcher
from ..common.data_model import Sender, UserData, UserInfo, T_DisplayContentType


def default_get_user_data(
    event: GroupMessageEvent | PrivateMessageEvent,
    user_data_dict: dict[UserInfo, UserData],
) -> UserData:
    return user_data_dict.setdefault(
        UserInfo(platform='telegram', user_id=event.from_.id),
        UserData(
            sender=Sender(
                user_id=event.from_.id,
                user_name=event.from_.username or '<未知的的用户名>',
            )
        ),
    )


def reply_out(event: MessageEvent, content: MessageSegment | Message | str) -> Message:
    """返回一个回复消息，Telegram 不知道如何实现"""
    # TODO: 实现回复
    return Message(content)


async def get_display_message(
    user_data: UserData, display_content_type: T_DisplayContentType
) -> Message:
    """获取应该响应的信息片段"""
    display_type, content_type_list = display_content_type

    data = await get_display_data(user_data, display_content_type)

    match display_type:
        case 'text':
            return Message(MessageSegment(data))  # type: ignore
        case 'image':
            raise NotImplementedError('Telegram 暂时不支持图片')


async def get_display_message_list(current_user_data: UserData) -> list[Message]:
    """获取应该响应的信息"""
    msg_list: list[Message] = []
    for display_content_type in plugin_config.bingchat_display_content_types:
        msg = await get_display_message(current_user_data, display_content_type)
        msg_list.append(msg)

    return msg_list
