import re

from typing import Any, Optional
from EdgeGPT import Chatbot
from pydantic import BaseModel

from nonebot import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.event import Sender

class BingChatResponse(BaseModel):
    raw: dict
    
    @property
    def ask(self) -> str:
        return str(self.raw)

    @property
    def reply(self) -> str:
        return self.raw["item"]["messages"][1]["text"]


class UserData(BaseModel):
    sender: Sender
    chatbot: Chatbot
    history: list[tuple[str,BingChatResponse]] = list()

    class Config:
        arbitrary_types_allowed = True


def helpMessage() -> MessageSegment:
    return '命令符号："#", "/", "."\n' \
    '开始对话：{{命令符号}} chat/Chat/聊天 + 内容\n' \
    '重置一个对话：{{命令符号}}refresh-chat/刷新对话'

def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d\^\]', '', string)


def replyContent(bot: Bot, user_data:UserData):

    message = [
        MessageSegment.node_custom(
            user_id = user_data.sender.user_id,
            nickname = user_data.sender.nickname,
            content = user_data.history[-1][0]
        ),
        MessageSegment.node_custom(
            user_id = bot.self_id,
            nickname = 'BingChat',
            content = user_data.history[-1][1].reply
        )]

    if len(user_data) >= 2:
        message.append(
            MessageSegment.node_custom(
                user_id = bot.self_id,
                nickname = '分割线',
                content = '--------下面是历史消息--------'
            ))
        for user_convr, bot_convr in user_data.history:
            message.append(
                MessageSegment.node_custom(
                    user_id = user_data.sender.user_id,
                    nickname = user_data.sender.nickname,
                    content = user_convr
                ))
            message.append(
                MessageSegment.node_custom(
                    user_id = bot.self_id,
                    nickname = 'ChatGPT',
                    content = bot_convr.reply
                ))
    return message