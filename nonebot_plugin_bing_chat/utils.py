import re

from typing import Any, Optional
from EdgeGPT import Chatbot
from pydantic import BaseModel, validator

from nonebot import Bot, get_driver
from nonebot.log import logger
from nonebot.exception import FinishedException
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.event import Sender

from .config import Config

plugin_config = Config.parse_obj(get_driver().config).dict()


class BingChatResponse(BaseModel):
    raw: dict

    @property
    def content_simple(self) -> str:
        return removeQuoteStr(self.raw["item"]["messages"][1]["text"])


class Conversation(BaseModel):
    ask: str
    reply: BingChatResponse


class UserData(BaseModel):
    sender: Sender
    chatbot: Chatbot
    history: list[Conversation] = list()

    class Config:
        arbitrary_types_allowed = True


def helpMessage() -> MessageSegment:
    return (
        '命令符号："#", "/", "."\n'
        '开始对话：{{命令符号}} chat/Chat/聊天 + 内容\n'
        '重置一个对话：{{命令符号}}refresh-chat/刷新对话'
    )


def replyOut(message_id: int, message_segment: MessageSegment | str) -> MessageSegment:
    return MessageSegment.reply(message_id) + message_segment


def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d\^\]', '', string)


def historyOut(bot: Bot, user_data: UserData):
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
