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
from nonebot.adapters.onebot.v11.event import Sender

from ..common.dataModel import Conversation
from ..common.utils import (
    plugin_config,
    isConfilctWithOtherMatcher,
)


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


def detailOut(bot: Bot, raw: dict) -> list[MessageSegment]:
    nodes = []
    return nodes


# dict[user_id, UserData] user_id: UserData
user_data_dict: dict[int, UserData] = dict()

# dict[message_id, user_id] bot回答的问题的message_id: 对应的用户的user_id
reply_message_id_dict: dict[int, int] = dict()


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
