import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from nonebot.log import logger
from pydantic import BaseModel, Extra, validator

from .exceptions import (
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
    BingChatResponseException,
)

INVALID_RESPONSE_MESSAGE = '<无效的响应值, 请管理员查看控制台>'


def removeQuoteStr(string: str) -> str:
    return re.sub(r'\[\^\d+?\^]', '', string)


def deep_get(dictionary: Dict[str, Any], keys: str) -> Any:
    for key in keys.split("."):
        if list_search := re.search(r"(\S+)?\[(\d+)]", key):
            try:
                if list_search[1]:
                    dictionary = dictionary[list_search[1]]
                dictionary = dictionary[int(list_search[2])]  # type: ignore
            except (KeyError, IndexError):
                return None
        else:
            try:
                dictionary = dictionary[key]
            except (KeyError, TypeError):
                return None
    return dictionary


class filterMode(str, Enum):
    whitelist = 'whitelist'
    blacklist = 'blacklist'


class Config(BaseModel, extra=Extra.ignore):
    superusers: Set[int]

    bingchat_block: bool = False
    bingchat_to_me: bool = False
    bingchat_priority: int = 1
    bingchat_share_chat: bool = False
    bingchat_command_start: Set[str]  # 默认值为command_start

    bingchat_command_chat: Set[str] = {'chat'}
    bingchat_command_new_chat: Set[str] = {'chat-new', '刷新对话'}
    bingchat_command_history_chat: Set[str] = {'chat-history'}

    bingchat_log: bool = True
    bingchat_show_detail: bool = False
    bingchat_show_is_waiting: bool = True
    bingchat_plugin_directory: Path = Path('./data/BingChat')
    bingchat_conversation_style: Literal['creative', 'balanced', 'precise'] = 'balanced'
    bingchat_auto_refresh_conversation: bool = True

    bingchat_group_filter_mode: filterMode = filterMode.blacklist
    bingchat_group_filter_blacklist: Set[Optional[int]] = set()
    bingchat_group_filter_whitelist: Set[Optional[int]] = set()

    def __init__(self, **data: Any) -> None:
        if 'bingchat_command_start' not in data:
            data['bingchat_command_start'] = data['command_start']
        super().__init__(**data)

    @validator('bingchat_command_chat', pre=True)
    def bingchat_command_chat_validator(cls, v) -> set:  # type: ignore
        if not v:
            raise ValueError('bingchat_command_chat不能为空')
        return set(v)

    @validator('bingchat_command_new_chat', pre=True)
    def bingchat_command_new_chat_validator(cls, v) -> set:  # type: ignore
        if not v:
            raise ValueError('bingchat_command_new_chat不能为空')
        return set(v)

    @validator('bingchat_command_history_chat', pre=True)
    def bingchat_command_history_chat_validator(cls, v) -> set:  # type: ignore
        if not v:
            raise ValueError('bingchat_command_history_chat不能为空')
        return set(v)

    @validator('bingchat_plugin_directory', pre=True)
    def bingchat_plugin_directory_validator(cls, v) -> Path:  # type: ignore
        return Path(v)


class BingChatResponse(BaseModel):
    raw: Dict[str, Any]

    @validator('raw')
    def rawValidator(cls, v):  # type: ignore
        result_value = deep_get(v, 'item.result.value')

        if result_value == 'Throttled':
            logger.error('<Bing账号到达今日请求上限>')
            raise BingChatAccountReachLimitException('<Bing账号到达今日请求上限>')

        if result_value == 'Success':
            num_conver = deep_get(v, 'item.throttling.numUserMessagesInConversation')
            max_conver = deep_get(v, 'item.throttling.maxNumUserMessagesInConversation')

            if num_conver is not None and max_conver is not None and num_conver > max_conver:
                raise BingChatConversationReachLimitException(
                    f'<达到对话上限>\n最大对话次数：{max_conver}\n你的话次数：{num_conver}'
                )

            hidden_text = deep_get(v, 'item.messages[1].hiddenText')
            if hidden_text is not None:
                raise BingChatResponseException(f'<Bing检测到敏感问题，无法回答>\n{hidden_text}')

            text = deep_get(v, 'item.messages[1].text')
            if text is not None:
                return v

        logger.error('<未知的错误>')
        raise BingChatResponseException('<未知的错误, 请管理员查看控制台>')


    @property
    def content_simple(self) -> str:
        text = deep_get(self.raw, "item.messages[1].text")
        if text is not None:
            return removeQuoteStr(text)
        else:
            logger.error(self.raw)
            raise BingChatResponseException(INVALID_RESPONSE_MESSAGE)

    @property
    def content_with_reference(self) -> str:
        text = deep_get(self.raw, "item.messages[1].adaptiveCards[0].body[0].text")
        if text is not None:
            return removeQuoteStr(text)
        else:
            logger.error(self.raw)
            raise BingChatResponseException(INVALID_RESPONSE_MESSAGE)

    @property
    def content_detail(self) -> str:
        return ''

    @property
    def adaptive_cards(self) -> List[Any]:
        cards: Optional[List[Any]] = deep_get(self.raw, "item.messages[1].adaptiveCards[0].body")
        if cards is not None:
            return cards
        else:
            logger.error(self.raw)
            raise BingChatResponseException(INVALID_RESPONSE_MESSAGE)


class Conversation(BaseModel):
    ask: str
    reply: BingChatResponse
