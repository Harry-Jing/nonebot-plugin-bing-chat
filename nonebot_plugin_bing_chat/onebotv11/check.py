from nonebot.log import logger
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    PrivateMessageEvent,
    GroupMessageEvent,
)

from ..common.dataModel import filterMode
from ..common.exceptions import *

from .utils import plugin_config, UserData


def CheckIfInList(event: MessageEvent) -> str:
    """检查用户和群组是否在名单中，如果没有则抛出异常"""
    if event.sub_type == 'group':
        raise BingChatPermissionDeniedException('您没有权限，无法再群临时对话聊进行')

    if event.user_id in plugin_config.superusers:
        return '跳过权限检查，发送用户为超级用户'

    if isinstance(event, GroupMessageEvent):
        match plugin_config.bingchat_group_filter_mode:
            case filterMode.blacklist:
                if event.group_id in plugin_config.bingchat_group_filter_blacklist:
                    raise BingChatPermissionDeniedException('您没有权限，此群组在黑名单')

            case filterMode.whitelist:
                if event.group_id not in plugin_config.bingchat_group_filter_whitelist:
                    raise BingChatPermissionDeniedException('您没有权限，此群组不在白名单')

    return '在名单中'


def CheckIfUserIsWaitingForResponse(event: MessageEvent, user_data: UserData) -> str:
    """检查用户是否有对话在进行中，如果有则抛出异常"""
    if user_data.is_waiting:
        raise BingchatIsWaitingForResponseException('您有一个对话正在进行中，请先等待回应')

    return '用户没有对话在进行中'
