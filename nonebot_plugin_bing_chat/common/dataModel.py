import re
from enum import Enum
from typing import Optional, Literal
from pathlib import Path

from pydantic import BaseModel, Extra, validator

from nonebot.log import logger

from .exceptions import (
    BaseBingChatException,
    BingChatResponseException,
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
)


def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d+?\^\]', '', string)


class filterMode(str, Enum):
    whitelist = 'whitelist'
    blacklist = 'blacklist'


class Config(BaseModel, extra=Extra.ignore):
    superusers: set[int]

    bingchat_block: bool = False
    bingchat_to_me: bool = False
    bingchat_priority: int = 1
    bingchat_share_chat: bool = False
    bingchat_command_start: set[str]  # 默认值为command_start

    bingchat_command_chat: set[str] = {'chat'}
    bingchat_command_new_chat: set[str] = {'chat-new', '刷新对话'}
    bingchat_command_history_chat: set[str] = {'chat-history'}

    bingchat_log: bool = True
    bingchat_show_detail: bool = False
    bingchat_show_is_waiting: bool = True
    bingchat_plugin_directory: Path = Path('./data/BingChat')
    bingchat_conversation_style: Literal['creative', 'balanced', 'precise'] = 'balanced'
    bingchat_auto_refresh_conversation: bool = True

    bingchat_group_filter_mode: filterMode = filterMode.blacklist
    bingchat_group_filter_blacklist: set[Optional[int]] = set()
    bingchat_group_filter_whitelist: set[Optional[int]] = set()

    def __init__(self, **data) -> None:
        if not 'bingchat_command_start' in data:
            data['bingchat_command_start'] = data['command_start']
        super().__init__(**data)

    @validator('bingchat_command_chat', pre=True)
    def bingchat_command_chat_validator(cls, v) -> set:
        if not v:
            raise ValueError('bingchat_command_chat不能为空')
        return set(v)

    @validator('bingchat_command_new_chat', pre=True)
    def bingchat_command_new_chat_validator(cls, v) -> set:
        if not v:
            raise ValueError('bingchat_command_new_chat不能为空')
        return set(v)

    @validator('bingchat_command_history_chat', pre=True)
    def bingchat_command_history_chat_validator(cls, v) -> set:
        if not v:
            raise ValueError('bingchat_command_history_chat不能为空')
        return set(v)

    @validator('bingchat_plugin_directory', pre=True)
    def bingchat_plugin_directory_validator(cls, v) -> Path:
        return Path(v)


class BingChatResponse(BaseModel):
    raw: dict

    @validator('raw')
    def rawValidator(cls, v):
        match v:
            case {'item': {'result': {'value': 'Throttled'}}}:
                logger.error('<Bing账号到达今日请求上限>')
                raise BingChatAccountReachLimitException('<Bing账号到达今日请求上限>')

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'throttling': {
                        'numUserMessagesInConversation': num_conver,
                        'maxNumUserMessagesInConversation': max_conver,
                    },
                }
            } if num_conver > max_conver:
                raise BingChatConversationReachLimitException(
                    f'<达到对话上限>\n最大对话次数：{max_conver}\n你的话次数：{num_conver}'
                )

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'messages': [
                        _,
                        {'hiddenText': hiddenText},
                    ],
                }
            }:
                raise BingChatResponseException(f'<Bing检测到敏感问题，无法回答>\n{hiddenText}')

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'messages': [
                        _,
                        {'text': text},
                    ],
                }
            }:
                return v

            case _:
                logger.error('<未知的错误>')
                raise BingChatResponseException('<未知的错误, 请管理员查看控制台>')

    @property
    def content_simple(self) -> str:
        try:
            return removeQuoteStr(self.raw["item"]["messages"][1]["text"])
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值, 请管理员查看控制台>') from exc

    @property
    def content_with_reference(self) -> str:
        try:
            return removeQuoteStr(
                self.raw["item"]["messages"][1]["adaptiveCards"][0]['body'][0]['text']
            )
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值, 请管理员查看控制台>') from exc

    @property
    def content_detail(self) -> str:
        return ''

    @property
    def adaptive_cards(self) -> list:
        try:
            return self.raw["item"]["messages"][1]["adaptiveCards"][0]['body']
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值, 请管理员查看控制台>') from exc


class Conversation(BaseModel):
    ask: str
    reply: BingChatResponse
