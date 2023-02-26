import asyncio
from EdgeGPT import Chatbot

from nonebot import Bot, require
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin.on import on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .check import permissionsCheck
from .utils import *
from .exceptions import BaseBingChatException

user_data_dict: dict[int, UserData] = dict()


command_chat = on_command(
    cmd=plugin_config['bingchat_command_chat'][0],
    aliases=set(plugin_config['bingchat_command_chat'][1:]),
)
command_new_chat = on_command(
    cmd=plugin_config['bingchat_command_new_chat'][0],
    aliases=set(plugin_config['bingchat_command_new_chat'][1:]),
)
command_history_chat = on_command(
    cmd=plugin_config['bingchat_command_history_chat'][0],
    aliases=set(plugin_config['bingchat_command_history_chat'][1:]),
)


@command_chat.handle()
async def bing_chat_command_chat(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    # 输入为空，则返回帮助信息
    if not arg:
        await command_chat.finish(helpMessage())

    # 检查权限，如果没有权限则抛出异常
    try:
        permissionsCheck(event=event)
    except BaseBingChatException as exc:
        await command_chat.finish(str(exc))

    # 获取历史创建的user_data，并获取chatbot，如果没有则创建一个
    try:
        if event.sender.user_id in user_data_dict:
            current_user_data = user_data_dict[event.sender.user_id]
            permissionsCheck(event=event, user_data=current_user_data)
        else:
            permissionsCheck(event=event)
            current_user_data = UserData(
                sender=event.sender,
                chatbot=Chatbot(cookiePath='./data/BingChat/cookies.json'),
            )
            user_data_dict[event.sender.user_id] = current_user_data
    except BaseBingChatException as exc:
        await command_chat.finish(str(exc))
    except Exception as exc:
        await command_chat.send(f'<无法创建Chatbot>\n{exc}')
        raise exc
    else:
        chatbot = current_user_data.chatbot

    # 询问Bing
    try:
        message_is_asking = await command_chat.send(replyOut(event.message_id, '正在请求'))
        user_input_text = arg.extract_plain_text()
        response = await chatbot.ask(prompt=user_input_text)
        # user_input_text = 'python的asyncio库是干什么的'
        # from .example_data import response
    except Exception as exc:
        await command_chat.send(f'<无法询问>\n{exc}')
        raise exc
    else:
        current_user_data.history.append(
            Conversation(ask=user_input_text, reply=BingChatResponse(raw=response))
        )

    await bot.delete_msg(message_id=message_is_asking['message_id'])
    await command_chat.send(
        replyOut(event.message_id, current_user_data.history[-1].reply.content_simple)
    )
    await chatbot.close()


@command_new_chat.handle()
async def bing_chat_command_new_chat(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    if arg:  # arg不为空
        await command_new_chat.finish('此命令没有参数，不要在命令后加别的内容')

    if event.sender.user_id in user_data_dict:
        user_data_dict[event.sender.user_id].chatbot.close()
        del user_data_dict[event.sender.user_id]
        await command_new_chat.send('已刷新对话')
    else:
        await command_new_chat.send('没有找到正现在进行的对话')


@command_history_chat.handle()
async def bing_chat_command_history_chat(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    if arg:  # arg不为空
        await command_new_chat.finish('此命令没有参数，不要在命令后加别的内容')

    if not event.sender.user_id in user_data_dict:
        await command_new_chat.finish('您没有历史对话')

    current_user_data = user_data_dict[event.sender.user_id]
    msg = historyOut(bot, current_user_data)

    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=msg)
    if isinstance(event, PrivateMessageEvent):
        await bot.send_private_forward_msg(user_id=event.user_id, messages=msg)
