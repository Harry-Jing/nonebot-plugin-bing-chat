import asyncio
from EdgeGPT import Chatbot

from nonebot import require
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from nonebot import Bot, get_driver
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin.on import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent

from .utils import *


user_data_dict: dict[int, UserData] = dict()


command_chat = on_command(cmd = plugin_config['bingchat_command_chat'][0], aliases=set(plugin_config['bingchat_command_chat'][1:]))
command_new_chat = on_command(cmd = plugin_config['bingchat_command_new_chat'][0], aliases=set(plugin_config['bingchat_command_new_chat'][1:]))

@command_chat.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if not arg: #arg为空
        logger.debug(helpMessage())
        await command_chat.finish(helpMessage())

    #检查权限
    if event.sub_type == 'group':
        logger.info('无法再群临时对话聊进行')
        await command_chat.finish()

    if plugin_config['bingchat_allow_group'] == False and isinstance(event, GroupMessageEvent):
        logger.info('无法再群聊进行')
        await command_chat.finish('无法再群聊进行')

    user_input_text = arg.extract_plain_text()

    if event.sender.user_id in user_data_dict:
        chatbot = user_data_dict[event.sender.user_id].chatbot
    else:
        try:
            chatbot = Chatbot(cookiePath='./data/BingChat/cookies.json')
            user_data_dict[event.sender.user_id] = UserData(sender=event.sender, chatbot=chatbot)
        except Exception as exc:
            await command_chat.send(f'<无法创建Chatbot>\n{exc}')
            raise exc

    try:
        response = await chatbot.ask(prompt=user_input_text)
    except Exception as exc:
        await command_chat.send(f'<无法询问>\n{exc}')
        raise exc

    logger.debug(response)
    text = response["item"]["messages"][1]["text"]
    await command_chat.send(removeQuoteStr(text))
    await chatbot.close()



@command_new_chat.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if not arg: #arg为空
        if event.sender.user_id in user_data_dict:
            user_data_dict[event.sender.user_id].chatbot.close()
            del user_data_dict[event.sender.user_id]
            await command_new_chat.send('已刷新对话')
        else:
            await command_new_chat.send('没有找到可以刷新的对话')
    else:
        await command_new_chat.send('不要再命令后加别的内容')
