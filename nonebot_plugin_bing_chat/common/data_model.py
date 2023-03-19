import re
import time
from enum import Enum
from typing import Optional, Literal, TypeAlias
from pathlib import Path

from EdgeGPT import Chatbot
from pydantic import BaseModel, Extra, validator

from nonebot.log import logger

from .exceptions import (
    BaseBingChatException,
    BingChatResponseException,
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
)


def remove_quote_str(string: str) -> str:
    return re.sub(r'\[\^\d+?\^\]', '', string)


FilterMode: TypeAlias = Literal['whitelist', 'blacklist']
ConversationStyle: TypeAlias = Literal['creative', 'balanced', 'precise']
ResponseContentType: TypeAlias = Literal['answer', 'reference', 'suggested-question']
DisplayContentTypes: TypeAlias = Literal[
    'text.answer',
    'text.reference',
    'text.suggested-question',
    'text.answer&reference',
    'text.answer&suggested-question',
    'text.reference&answer',
    'text.reference&suggested-question',
    'text.suggested-question&answer',
    'text.suggested-question&reference',
    'text.answer&reference&suggested-question',
    'text.answer&suggested-question&reference',
    'text.reference&answer&suggested-question',
    'text.reference&suggested-question&answer',
    'text.suggested-question&answer&reference',
    'text.suggested-question&reference&answer',
    'image.answer',
    'image.reference',
    'image.suggested-question',
    'image.answer&reference',
    'image.answer&suggested-question',
    'image.reference&answer',
    'image.reference&suggested-question',
    'image.suggested-question&answer',
    'image.suggested-question&reference',
    'image.answer&reference&suggested-question',
    'image.answer&suggested-question&reference',
    'image.reference&answer&suggested-question',
    'image.reference&suggested-question&answer',
    'image.suggested-question&answer&reference',
    'image.suggested-question&reference&answer',
]
# *('text-'+'&'.join(i) for i in itertools.chain.from_iterable(itertools.permutations(options, r) for r in range(1, len(options) + 1)))
# *('image-'+'&'.join(i) for i in itertools.chain.from_iterable(itertools.permutations(options, r) for r in range(1, len(options) + 1)))


class Config(BaseModel, extra=Extra.ignore):
    superusers: set[int]
    command_start: set[str]

    bingchat_block: bool = False
    bingchat_to_me: bool = False
    bingchat_priority: int = 1
    bingchat_share_chat: bool = False

    bingchat_command_chat: set[str] = {'chat'}
    bingchat_command_new_chat: set[str] = {'chat-new', '刷新对话'}
    bingchat_command_history_chat: set[str] = {'chat-history'}

    bingchat_display_is_waiting: bool = True
    bingchat_display_mode: Literal['direct', 'forward'] = 'direct'  # TODO
    bingchat_display_content_types: list[DisplayContentTypes] = ['text.answer']

    bingchat_log: bool = True
    bingchat_plugin_directory: Path = Path('./data/BingChat')
    bingchat_conversation_style: ConversationStyle = 'balanced'
    bingchat_auto_refresh_conversation: bool = True

    bingchat_group_filter_mode: FilterMode = 'blacklist'
    bingchat_group_filter_blacklist: set[Optional[int]] = set()
    bingchat_group_filter_whitelist: set[Optional[int]] = set()

    def __init__(self, **data) -> None:
        if 'bingchat_show_detail' in data:
            logger.warning('<bingchat_show_detail>将在0.8弃用，请使用<bingchat_display_modes>')
            data['bingchat_display_mode'] = (
                ['text-answer&reference']
                if data['bingchat_show_detail']
                else ['text-answer']
            )
        if 'bingchat_show_is_waiting' in data:
            logger.warning(
                '<bingchat_show_is_waiting>将在0.8弃用，请使用<bingchat_display_is_waiting>'
            )
            data['bingchat_display_is_waiting'] = data['bingchat_show_is_waiting']
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

    @validator('bingchat_display_mode', pre=True)
    def bingchat_display_mode_validator(cls, v) -> list:
        if not v:
            raise ValueError('bingchat_display_mode不能为空')
        return list(v)

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

    def get_content(self, type: ResponseContentType = 'answer') -> str:
        match type:
            case 'answer':
                return self.content_answer
            case 'reference':
                return self.content_reference
            case 'suggested-question':
                return self.content_suggested_question
            case _:
                return ''

    @property
    def content_answer(self) -> str:
        try:
            return remove_quote_str(self.raw["item"]["messages"][1]["text"])
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值>') from exc

    @property
    def content_reference(self) -> str:
        try:
            return remove_quote_str(self.adaptive_cards[0]['text'])
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值>') from exc

    @property
    def content_suggested_question(self) -> str:
        return '\n'.join(self.suggested_questions)

    @property
    def adaptive_cards(self) -> list:
        try:
            return self.raw["item"]["messages"][1]["adaptiveCards"][0]['body']
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值>') from exc

    @property
    def suggested_questions(self) -> list[str]:
        suggested_questions = []
        try:
            for i in self.raw["item"]["messages"][1]["suggestedResponses"]:
                suggested_questions.append(i['text'])
            return suggested_questions
        except (IndexError, KeyError) as exc:
            logger.error(self.raw)
            raise BingChatResponseException('<无效的响应值>') from exc


class UserInfo(BaseModel, frozen=True):  # type: ignore
    platorm: str
    user_id: int


class Sender(BaseModel, extra=Extra.ignore):
    user_id: int
    nickname: str


class Conversation(BaseModel):
    ask: str
    reply: BingChatResponse


class UserData(BaseModel, arbitrary_types_allowed=True):
    sender: Sender

    first_ask_message_id: Optional[int] = None
    last_reply_message_id: int = 0

    chatbot: Optional[Chatbot] = None
    last_time: float = time.time()
    is_waiting: bool = False
    conversation_count: int = 0
    history: list[Conversation] = []

    @validator('sender', pre=True)
    def sender_validator(cls, v) -> Sender:
        return Sender(**v)
