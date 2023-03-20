import shutil
from datetime import datetime, timedelta

from nonebot import require

from .utils import plugin_config, plugin_directory

"""初始化"""
plugin_directory.mkdir(parents=True, exist_ok=True)
# 检查cookie文件是否存在且不为空
plugin_cookies_path = plugin_directory.joinpath('cookies.json')
plugin_cookies_path.touch(exist_ok=True)
if plugin_cookies_path.stat().st_size == 0:
    raise FileNotFoundError(
        'BingChat插件未配置cookie，请在./data/BingChat/cookies.json中填入你的cookie'
    )
# 创建log文件夹
plugin_log_directory = plugin_directory / 'log'
plugin_log_directory.mkdir(parents=True, exist_ok=True)


if plugin_config.bingchat_display_mode in ('image_simple', 'image_detail'):
    try:
        require("nonebot_plugin_htmlrender")
    except RuntimeError as exc:
        raise RuntimeError(
            "请使用 pip install nonebot-plugin-bing-chat[all] 来安装所有依赖"
        ) from exc
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


@scheduler.scheduled_job('cron', hour=2)
async def _del_log_file() -> None:
    print('del_log_file')
    current_time = datetime.now()
    plugin_log_directory = plugin_directory / 'log'
    for child_dir in plugin_log_directory.iterdir():
        if current_time - datetime.fromisoformat(child_dir.name) > timedelta(days=7):
            shutil.rmtree(child_dir)
