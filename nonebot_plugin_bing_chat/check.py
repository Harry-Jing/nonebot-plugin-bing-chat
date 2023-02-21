from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent, GroupMessageEvent

from .config import filterMode
from .utils import plugin_config


def permissionsCheck(event: MessageEvent) -> tuple[bool, str | None]:
    if event.sub_type == 'group':
        return False, '无法再群临时对话聊进行'

    if event.user_id == plugin_config['superusers']:
        logger.info('发送用户为超级用户')
        return True, None

    if isinstance(event, GroupMessageEvent):
        match plugin_config['bingchat_group_filter_mode']:
            case filterMode.blacklist:
                return event.group_id in plugin_config['bingchat_group_filter_blacklist'], '此群组在黑名单'

            case filterMode.whitelist:
                return event.group_id not in plugin_config['bingchat_group_filter_whitelist'], '此群组不在白名单'
