import time
from typing import Any, Dict, List, Optional, Union

from EdgeGPT import Chatbot
from nonebot import Bot
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.params import EventToMe
from nonebot.plugin.on import on_message
from nonebot.rule import Rule
from pydantic import BaseModel

from ..common.dataModel import Conversation
from ..common.utils import (
    isConfilctWithOtherMatcher,
    plugin_config,
)


class UserData(BaseModel):
    sender: Sender

    first_ask_message_id: Optional[int] = None
    last_reply_message_id: int = 0

    chatbot: Optional[Chatbot] = None
    last_time: float = time.time()
    is_waiting: bool = False
    conversation_count: int = 0
    history: List[Conversation] = []

    class Config:
        arbitrary_types_allowed = True


def replyOut(message_id: int, message_segment: Union[MessageSegment, str]) -> Message:
    """返回一个回复消息"""
    return MessageSegment.reply(message_id) + message_segment


def historyOut(bot: Bot, user_data: UserData) -> List[MessageSegment]:
    """将历史记录输出到消息列表并返回"""
    nodes = []
    for conversation in user_data.history:
        nodes.append(
            MessageSegment.node_custom(
                user_id=user_data.sender.user_id,  # type: ignore
                nickname=user_data.sender.nickname,  # type: ignore
                content=conversation.ask,
            )
        )
        nodes.append(
            MessageSegment.node_custom(
                user_id=int(bot.self_id),
                nickname='Bing',
                content=conversation.reply.content_simple,
            )
        )
    return nodes


# TODO: ?
def detailOut(bot: Bot, raw: Dict[str, Any]) -> List[MessageSegment]:
    nodes: List[MessageSegment] = []
    return nodes


# dict[user_id, UserData] user_id: UserData
user_data_dict: Dict[int, UserData] = dict()

# dict[message_id, user_id] bot回答的问题的message_id: 对应的用户的user_id
reply_message_id_dict: Dict[int, int] = dict()


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
