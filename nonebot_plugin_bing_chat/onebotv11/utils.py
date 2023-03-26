
from nonebot import Bot
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import EventToMe
from nonebot.plugin.on import on_message
from nonebot.rule import Rule
from nonebot_plugin_guild_patch import GuildMessageEvent

from ..common import (
    plugin_config,
    plugin_data,
)
from ..common.data_model import (
    DisplayContentType,
    Sender,
    UserData,
    UserInfo,
)
from ..common.utils import (
    is_conflict_with_other_matcher,
)

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
    current_user_data: UserData, display_content_type: DisplayContentType
) -> Message:
    """获取应该响应的信息片段"""
    msg = Message()
    display_type, content_type_list = display_content_type

    message_plain_text_list: list[str] = []
    for content_type in content_type_list:
        content = current_user_data.latest_response.get_content(content_type)
        match content_type:
            case 'reference':
                new_content = '参考链接：\n'
            case 'suggested-question':
                new_content = '猜你想问：\n'
            case 'num-max-conversation':
                new_content = '回复数：'
            case _:
                new_content = ''
        message_plain_text_list.append(f'{new_content}{content}')
    if message_plain_text_list:
        msg_content = '\n\n'.join(message_plain_text_list)
        match display_type:
            case 'text':
                msg.append(MessageSegment.text(msg_content))
            case 'image':
                img = await md_to_pic('\n\n---\n\n'.join(message_plain_text_list))
                msg.append(MessageSegment.image(img))
    return msg


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
