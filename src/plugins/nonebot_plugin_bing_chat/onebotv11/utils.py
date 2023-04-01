from nonebot.rule import Rule
from nonebot.params import EventToMe
from nonebot.adapters import Bot
from nonebot.plugin.on import on_message
from nonebot_plugin_guild_patch import GuildMessageEvent
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

from ..common import plugin_data, plugin_config
from ..common.utils import get_display_data, is_conflict_with_other_matcher
from ..common.data_model import Sender, UserData, UserInfo, T_DisplayContentType

if any(i == 'image' for i, _ in plugin_config.bingchat_display_content_types):
    from nonebot_plugin_htmlrender import md_to_pic


def default_get_user_data(
    event: MessageEvent, user_data_dict: dict[UserInfo, UserData]
) -> UserData:
    return user_data_dict.setdefault(
        UserInfo(platform='qq', user_id=event.user_id),
        UserData(
            sender=Sender(
                user_id=event.user_id,
                user_name=event.sender.nickname or '<未知的的用户名>',
            )
        ),
    )


def reply_out(event: MessageEvent, content: MessageSegment | Message | str) -> Message:
    """返回一个回复消息"""
    if isinstance(event, GuildMessageEvent):
        return Message(content)

    return MessageSegment.reply(event.message_id) + content


def history_out(bot: Bot, user_data: UserData) -> Message:
    """将历史记录输出到消息列表并返回"""
    msg = Message()
    for conversation in user_data.history:
        msg += MessageSegment.node_custom(
            user_id=user_data.sender.user_id,
            nickname=user_data.sender.user_name,
            content=conversation.ask,
        )
        msg += MessageSegment.node_custom(
            user_id=int(bot.self_id),
            nickname='Bing',
            content=conversation.response.content_answer,
        )

    return msg


async def get_display_message(
    user_data: UserData, display_content_type: T_DisplayContentType
) -> Message:
    """获取应该响应的信息片段"""
    display_type, content_type_list = display_content_type

    data = await get_display_data(user_data, display_content_type)

    match display_type:
        case 'text':
            return Message(MessageSegment.text(data))  # type: ignore
        case 'image':
            return Message(MessageSegment.image(data))


async def get_display_message_list(current_user_data: UserData) -> list[Message]:
    """获取应该响应的信息"""
    msg_list: list[Message] = []
    for display_content_type in plugin_config.bingchat_display_content_types:
        msg = await get_display_message(current_user_data, display_content_type)
        msg_list.append(msg)

    return msg_list


async def get_display_message_forward(current_user_data: UserData) -> Message:
    """获取应该响应的信息"""
    _msg = Message()
    for display_content_type in plugin_config.bingchat_display_content_types:
        msg = await get_display_message(current_user_data, display_content_type)
        _msg += MessageSegment.node_custom(
            user_id=current_user_data.sender.user_id,
            nickname=current_user_data.sender.user_name,
            content=msg,
        )
    return _msg


def _rule_continue_chat(event: MessageEvent, to_me: bool = EventToMe()) -> bool:
    return bool(
        to_me
        and event.reply
        and event.reply.message_id in plugin_data.reply_message_id_dict
        and not is_conflict_with_other_matcher(event.message.extract_plain_text())
    )


matcher_reply_to_continue_chat = on_message(
    rule=Rule(_rule_continue_chat),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)
