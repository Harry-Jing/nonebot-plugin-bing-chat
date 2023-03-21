import re
from typing import Literal

from nonebot import Bot
from nonebot.log import logger
from nonebot.rule import Rule
from nonebot.params import EventToMe
from nonebot.plugin.on import on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent

from ..common.data_model import (
    DisplayType,
    ResponseContentType,
    DisplayContentType,
    UserData,
)
from ..common.utils import (
    plugin_config,
    reply_message_id_dict,
    is_confilct_with_other_matcher,
)

if any('image' in i for i in plugin_config.bingchat_display_content_types):
    from nonebot_plugin_htmlrender import md_to_pic


def reply_out(
    message_id: int, message_segment: MessageSegment | Message | str
) -> Message:
    """返回一个回复消息"""
    return MessageSegment.reply(message_id) + message_segment


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
    display_type: DisplayType
    content_type_list: list[ResponseContentType]
    display_type, *content_type_list = re.split(r'[\.&]', display_content_type)  # type: ignore

    message_plain_text_list: list[str] = []         
    match display_type:
        case 'text':
            for content_type in content_type_list:
                content = current_user_data.lastest_response.get_content(type=content_type)
                match content_type:
                    case 'answer':
                        message_plain_text_list.append(content)
                    case 'reference':
                        new_content = '参考链接：\n' + content
                        message_plain_text_list.append(new_content)
                    case 'suggested-question':
                        new_content = '猜你想问：\n' + content
                        message_plain_text_list.append(new_content)
                    case 'num-max-conversation':
                        new_content = '回复数：' + content
                        message_plain_text_list.append(new_content)
                    case _:
                        raise ValueError(f'无效的content_type：{content_type}')
            msg.append(MessageSegment.text('\n\n'.join(message_plain_text_list)))

        case 'image':
            for content_type in content_type_list:
                content = current_user_data.lastest_response.get_content(type=content_type)
                match content_type:
                    case 'answer':
                        message_plain_text_list.append(content)
                    case 'reference':
                        new_content = '参考链接：\n\n' + content
                        message_plain_text_list.append(new_content)
                    case 'suggested-question':
                        new_content = '猜你想问：\n\n' + content
                        message_plain_text_list.append(new_content)
                    case 'num-max-conversation':
                        new_content = '回复数：' + content
                        message_plain_text_list.append(new_content)
                    case _:
                        raise ValueError(f'无效的content_type：{content_type}')
            img = await md_to_pic('\n\n---\n\n'.join(message_plain_text_list))
            msg.append(MessageSegment.image(img))

    return msg


async def get_display_content(current_user_data: UserData) -> list[Message]:
    """获取应该响应的信息"""
    message_list: list[Message] = []

    for display_content_type in plugin_config.bingchat_display_content_types:
        msg = await get_display_message(current_user_data, display_content_type)
        message_list.append(msg)

    return message_list


def _rule_continue_chat(event: MessageEvent, to_me: bool = EventToMe()) -> bool:
    if (
        not to_me
        or not event.reply
        or event.reply.message_id not in reply_message_id_dict
        or is_confilct_with_other_matcher(event.message.extract_plain_text())
    ):
        return False
    return True


matcher_reply_to_continue_chat = on_message(
    rule=Rule(_rule_continue_chat),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)
