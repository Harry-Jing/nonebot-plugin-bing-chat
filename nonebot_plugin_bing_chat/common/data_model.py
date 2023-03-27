import re
import time
from pathlib import Path
from typing import Any, Callable, Literal, Optional, TypeAlias, NoReturn

from EdgeGPT import Chatbot
from nonebot.log import logger
from pydantic import BaseModel, Extra, validator

from .exceptions import (
    BingChatAccountReachLimitException,
    BingChatConversationReachLimitException,
    BingChatResponseException,
)


def remove_quote_str(string: str) -> str:
    return re.sub(r'\[\^\d+?\^]', '', string)


def get_response_content_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    def inner(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (IndexError, KeyError) as exc:
            raise BingChatResponseException('<无效的响应值>') from exc

    return inner


FilterMode: TypeAlias = Literal['whitelist', 'blacklist']
ConversationStyle: TypeAlias = Literal['creative', 'balanced', 'precise']
DisplayType: TypeAlias = Literal['text', 'image']
ResponseContentType: TypeAlias = Literal[
    'answer', 'reference', 'suggested-question', 'num-max-conversation'
]
DisplayContentType: TypeAlias = tuple[DisplayType, list[ResponseContentType]]


class PluginConfig(BaseModel, extra=Extra.ignore):
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
    bingchat_display_in_forward: bool = False
    bingchat_display_content_types: list[DisplayContentType] = [('text', ['num-max-conversation', 'answer', 'suggested-question'])]

    bingchat_log: bool = True
    bingchat_proxy: Optional[str] = None
    bingchat_plugin_directory: Path = Path('./data/BingChat')
    bingchat_conversation_style: ConversationStyle = 'balanced'
    bingchat_auto_switch_cookies: bool = False
    bingchat_auto_refresh_conversation: bool = True

    bingchat_group_filter_mode: FilterMode = 'blacklist'
    bingchat_group_filter_blacklist: set[Optional[int]] = set()
    bingchat_group_filter_whitelist: set[Optional[int]] = set()

    def __init__(self, **data: Any) -> None:
        if 'bingchat_show_detail' in data:
            logger.error(
                '<bingchat_show_detail>已经弃用，请使用<bingchat_display_content_types>'
            )
        if 'bingchat_show_is_waiting' in data:
            logger.error(
                '<bingchat_show_is_waiting>已经弃用，请使用<bingchat_display_is_waiting>'
            )
        super().__init__(**data)

    @validator('bingchat_command_chat', pre=True)
    def bingchat_command_chat_validator(cls, v: Any) -> set[str]:
        if not v:
            raise ValueError('bingchat_command_chat不能为空')
        return set(v)

    @validator('bingchat_command_new_chat', pre=True)
    def bingchat_command_new_chat_validator(cls, v: Any) -> set[str]:
        if not v:
            raise ValueError('bingchat_command_new_chat不能为空')
        return set(v)

    @validator('bingchat_command_history_chat', pre=True)
    def bingchat_command_history_chat_validator(cls, v: Any) -> set[str]:
        if not v:
            raise ValueError('bingchat_command_history_chat不能为空')
        return set(v)

    @validator('bingchat_display_content_types', pre=True)
    def bingchat_display_content_types_validator(
        cls, v: Any
    ) -> list[DisplayContentType]:
        if not v:
            raise ValueError('bingchat_display_content_types不能为空')
        types = []
        for i in list(v):
            display_type, *content_type_list = re.split(r'[.&]', i)
            if display_type not in ['text', 'image']:
                raise ValueError(f'无效的显示类型: {display_type}')
            for content_type in content_type_list:
                if content_type not in [
                    'answer',
                    'reference',
                    'suggested-question',
                    'num-max-conversation',
                ]:
                    raise ValueError(f'无效的响应类型: {content_type}')
            types.append((display_type, content_type_list))
        return types

    @validator('bingchat_plugin_directory', pre=True)
    def bingchat_plugin_directory_validator(cls, v: Any) -> Path:
        return Path(v)


class BingChatResponse(BaseModel):
    raw: dict[Any, Any]

    @validator('raw')
    def raw_validator(cls, v: dict[Any, Any]) -> dict[Any, Any]:
        match v:
            case {'item': {'result': {'value': 'Throttled'}}}:
                logger.error('<Bing账号到达今日请求上限>')
                raise BingChatAccountReachLimitException('<Bing账号到达今日请求上限>')

            case {'item': {'result': {'value': 'InvalidSession'}}}:
                logger.error('<无效的会话>')
                raise BingChatResponseException('<无效的会话>')

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
                    f'<达到对话上限>\n对话数达到上限：{num_conver}/{max_conver}'
                )

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'messages': [
                        {'offense': 'Offensive'},
                        _,
                    ],
                }
            }:
                logger.error('<Bing检测到冒犯性文字，拒绝回答')
                raise BingChatResponseException('<Bing检测到冒犯性文字，拒绝回答>')

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'messages': [
                        _,
                        {'hiddenText': hidden_text},
                    ],
                }
            }:
                logger.error(f'<Bing检测到敏感问题，自动隐藏>\n{hidden_text}')
                raise BingChatResponseException(f'<Bing检测到敏感问题，自动隐藏>\n{hidden_text}')

            case {
                'item': {
                    'result': {'value': 'Success'},
                    'messages': [
                        _,
                        {'text': _},
                    ],
                }
            }:
                return v

            case _:
                logger.error('<未知的错误>')
                raise BingChatResponseException('<未知的错误, 请管理员查看控制台>')

    @property
    @get_response_content_handler
    def num_conversation(self) -> int:
        return int(self.raw['item']['throttling']['numUserMessagesInConversation'])

    @property
    @get_response_content_handler
    def max_conversation(self) -> int:
        return int(self.raw['item']['throttling']['maxNumUserMessagesInConversation'])

    @property
    @get_response_content_handler
    def content_answer(self) -> str:
        return remove_quote_str(self.raw['item']['messages'][1]['text'])

    @property
    @get_response_content_handler
    def content_reference(self) -> str:
        return '\n'.join(f'- {i}' for i in self.source_attributions_url_list)

    @property
    def content_suggested_question(self) -> str:
        return '\n'.join(f'- {i}' for i in self.suggested_question_list)

    @property
    @get_response_content_handler
    def adaptive_cards(self) -> list[str]:
        return list(self.raw['item']['messages'][1]['adaptiveCards'][0]['body'])

    @property
    @get_response_content_handler
    def source_attributions_url_list(self) -> list[str]:
        return [
            i['seeMoreUrl']
            for i in self.raw['item']['messages'][1]['sourceAttributions']
        ]

    @property
    @get_response_content_handler
    def suggested_question_list(self) -> list[str]:
        return [
            i['text'] for i in self.raw['item']['messages'][1]['suggestedResponses']
        ]

    def get_content(self, type: ResponseContentType = 'answer') -> str:
        match type:
            case 'answer':
                return self.content_answer
            case 'reference':
                return self.content_reference
            case 'suggested-question':
                return self.content_suggested_question
            case 'num-max-conversation':
                return f'{self.num_conversation}/{self.max_conversation}'
            case _:
                raise TypeError(f'<无效的类型：{type}>')


class UserInfo(BaseModel, frozen=True):
    platform: str
    user_id: int


class Sender(BaseModel, extra=Extra.ignore):
    user_id: int
    user_name: str


class Conversation(BaseModel):
    ask: str
    response: BingChatResponse


class UserData(BaseModel, arbitrary_types_allowed=True):
    sender: Sender

    first_ask_message_id: Optional[int] = None
    last_reply_message_id: int = 0

    chatbot: Optional[Chatbot] = None
    last_time: float = time.time()
    is_waiting: bool = False
    history: list[Conversation] = []

    @property
    def latest_conversation(self) -> Conversation:
        return self.history[-1]

    @property
    def latest_ask(self) -> str:
        return self.history[-1].ask

    @property
    def latest_response(self) -> BingChatResponse:
        return self.history[-1].response

    async def clear(self, sender: Sender) -> None:
        if self.chatbot is not None:
            await self.chatbot.close()

        self.sender = sender
        self.first_ask_message_id = None
        self.last_reply_message_id = 0
        self.chatbot = None
        self.history = []


class PluginData(BaseModel):
    cookies_file_path_list: list[Path] = []
    current_cookies_file_path: Path = Path()
    is_switching_cookies: bool = False

    # dict[user_id, UserData] user_id: UserData
    user_data_dict: dict[UserInfo, UserData] = {}

    # dict[message_id, user_id] bot回答的问题的message_id: 对应的用户的user_id
    reply_message_id_dict: dict[int, UserInfo] = {}
