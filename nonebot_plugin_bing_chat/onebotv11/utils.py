import time
from typing import Any, Optional

from EdgeGPT import Chatbot
from pydantic import BaseModel

from nonebot import Bot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.event import Sender

from ..common.dataModel import *
from ..common.utils import *


class UserData(BaseModel):
    sender: Sender

    chatbot: Optional[Chatbot] = None
    last_time: float = time.time()
    is_waiting: bool = False
    conversation_count: int = 0
    history: list[Conversation] = []

    class Config:
        arbitrary_types_allowed = True


def getUserDataSafe(
    user_data_dict: dict[int, UserData], event: MessageEvent
) -> UserData:
    """获取该用户的user_data，如果没有则创建一个并返回"""
    if event.sender.user_id in user_data_dict:
        current_user_data = user_data_dict[event.sender.user_id]
    else:
        current_user_data = UserData(sender=event.sender)
        user_data_dict[event.sender.user_id] = current_user_data

    return current_user_data


def replyOut(message_id: int, message_segment: MessageSegment | str) -> MessageSegment:
    """返回一个回复消息"""
    return MessageSegment.reply(message_id) + message_segment


def historyOut(bot: Bot, user_data: UserData) -> list[MessageSegment]:
    """将历史记录输出到消息列表并返回"""
    messages = []
    for conversation in user_data.history:
        messages.append(
            MessageSegment.node_custom(
                user_id=user_data.sender.user_id,
                nickname=user_data.sender.nickname,
                content=conversation.ask,
            )
        )
        messages.append(
            MessageSegment.node_custom(
                user_id=bot.self_id,
                nickname='ChatGPT',
                content=conversation.reply.content_simple,
            )
        )
    return messages
