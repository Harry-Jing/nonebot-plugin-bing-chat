import time
from typing import Any, Optional

from EdgeGPT import Chatbot
from pydantic import BaseModel

from nonebot import Bot
from nonebot.log import logger
from nonebot.rule import Rule, to_me
from nonebot.params import EventToMe
from nonebot.plugin.on import on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent

from ..common.dataModel import (
    DisplayContentTypes,
    Conversation,
    UserData,
)
from ..common.utils import (
    plugin_config,
    reply_message_id_dict,
    isConfilctWithOtherMatcher,
)

if plugin_config.bingchat_display_mode in ('image_simple', 'image_detail'):
    from nonebot_plugin_htmlrender import md_to_pic


def replyOut(
    message_id: int, message_segment: MessageSegment | Message | str
) -> Message:
    """返回一个回复消息"""
    return MessageSegment.reply(message_id) + message_segment


def historyOut(bot: Bot, user_data: UserData) -> Message:
    """将历史记录输出到消息列表并返回"""
    msg = Message()
    for conversation in user_data.history:
        msg += MessageSegment.node_custom(
            user_id=user_data.sender.user_id,
            nickname=user_data.sender.nickname,
            content=conversation.ask,
        )
        msg += MessageSegment.node_custom(
            user_id=int(bot.self_id),
            nickname='Bing',
            content=conversation.reply.content_answer,
        )

    return msg


async def getDisplayContentSegment(
    current_user_data: UserData, content_type: DisplayContentTypes
) -> Message:
    """获取应该响应的信息片段"""
    msg = Message()
    
    match content_type.split('.'):
        case ['text', param]:
            text = current_user_data.history[-1].reply.get_content(
                
            )
            msg.append(MessageSegment.text(text))

        case ['image', param]:
            img = await md_to_pic(
                current_user_data.history[-1].reply.get_content(
                    
                )
            )
            msg.append(MessageSegment.image(img))
    
    return msg


async def getDisplayContent(current_user_data: UserData) -> list[Message]:
    """获取应该响应的信息"""
    message_segment_list:list[Message] = []
    for content_type in plugin_config.bingchat_display_content_types:
        match content_type:
            case 'text-simple' | 'text-detail':
                text = current_user_data.history[-1].reply.get_content(
                    type=plugin_config.bingchat_display_content_types
                )
                message_segment_list.append(MessageSegment.text(text))

            case 'image-simple' | 'image-detail':
                img = await md_to_pic(
                    current_user_data.history[-1].reply.get_content(
                        type=plugin_config.bingchat_display_content_types
                    )
                )
                message_segment_list.append(MessageSegment.image(img))

    return message_segment_list



def _rule_continue_chat(event: MessageEvent, to_me: bool = EventToMe()) -> bool:
    if (
        not to_me
        or not event.reply
        or event.reply.message_id not in reply_message_id_dict
        or isConfilctWithOtherMatcher(event.message.extract_plain_text())
    ):
        return False
    return True


matcher_reply_to_continue_chat = on_message(
    rule=Rule(_rule_continue_chat),
    priority=plugin_config.bingchat_priority,
    block=plugin_config.bingchat_block,
)
