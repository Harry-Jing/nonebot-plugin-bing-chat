from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent

from .config import filterMode
from .utils import plugin_config
from .exceptions import BingChatPermissionDeniedException

def permissionsCheck(event: MessageEvent) -> str:
    if event.sub_type == 'group':
        raise BingChatPermissionDeniedException('无法再群临时对话聊进行')

    if event.user_id in plugin_config['superusers']:
        return '发送用户为超级用户'

    if isinstance(event, GroupMessageEvent):
        match plugin_config['bingchat_group_filter_mode']:

            case filterMode.blacklist:
                if event.group_id in plugin_config['bingchat_group_filter_blacklist']:
                    raise BingChatPermissionDeniedException('此群组在黑名单')

            case filterMode.whitelist:
                if event.group_id not in plugin_config['bingchat_group_filter_whitelist']:
                    raise BingChatPermissionDeniedException('此群组不在白名单`')

    return '正常'