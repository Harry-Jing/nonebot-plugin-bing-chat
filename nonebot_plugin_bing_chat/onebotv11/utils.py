import time
from typing import Any, Optional

from EdgeGPT import Chatbot
from pydantic import BaseModel

from nonebot import Bot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.event import Sender

from ..common.dataModel import *
from ..common.utils import *


class UserData(BaseModel):
    sender: Sender
    
    first_ask_message_id: Optional[int] = None
    last_reply_message_id: int = 0

    chatbot: Optional[Chatbot] = None
    last_time: float = time.time()
    is_waiting: bool = False
    conversation_count: int = 0
    history: list[Conversation] = []

    class Config:
        arbitrary_types_allowed = True


def replyOut(message_id: int, message_segment: MessageSegment | str) -> Message:
    """返回一个回复消息"""
    return MessageSegment.reply(message_id) + message_segment


def historyOut(bot: Bot, user_data: UserData) -> list[MessageSegment]:
    """将历史记录输出到消息列表并返回"""
    nodes = []
    for conversation in user_data.history:
        nodes.append(
            MessageSegment.node_custom(
                user_id=user_data.sender.user_id,
                nickname=user_data.sender.nickname,
                content=conversation.ask,
            )
        )
        nodes.append(
            MessageSegment.node_custom(
                user_id=bot.self_id,
                nickname='Bing',
                content=conversation.reply.content_simple,
            )
        )
    return nodes
