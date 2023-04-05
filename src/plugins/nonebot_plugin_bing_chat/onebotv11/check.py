from nonebot_plugin_guild_patch import GuildMessageEvent
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent

from .utils import UserData
from ..common import plugin_config
from ..common.exceptions import (
    BingChatPermissionDeniedException,
    BingchatIsWaitingForResponseException,
)


def check_if_in_list(event: MessageEvent) -> str:
    """检查用户和群组是否在名单中，如果没有则抛出异常"""
    if event.sub_type == 'group':
        raise BingChatPermissionDeniedException('您没有权限，无法再群临时对话聊进行')

    if event.user_id in plugin_config.superusers:
        return '跳过权限检查，发送用户为超级用户'

    if isinstance(event, GroupMessageEvent):
        match plugin_config.bingchat_group_filter_mode:
            case 'blacklist':
                if event.group_id in plugin_config.bingchat_group_filter_blacklist:
                    raise BingChatPermissionDeniedException('您没有权限，此群组在黑名单内')

            case 'whitelist':
                if event.group_id not in plugin_config.bingchat_group_filter_whitelist:
                    raise BingChatPermissionDeniedException('您没有权限，此群组不在白名单内')
    elif isinstance(event, GuildMessageEvent):
        match plugin_config.bingchat_group_filter_mode:
            case 'blacklist':
                if {
                    'guild_id': str(event.guild_id),
                    'group_id': str(event.channel_id),
                } in plugin_config.bingchat_guild_filter_blacklist:
                    raise BingChatPermissionDeniedException('您没有权限，此频道在黑名单内')

            case 'whitelist':
                if {
                    'guild_id': str(event.guild_id),
                    'group_id': str(event.channel_id),
                } not in plugin_config.bingchat_guild_filter_whitelist:
                    raise BingChatPermissionDeniedException('您没有权限，此频道不在白名单内')
    return '在名单中'
