from .common import logger, plugin_config

if 'console' in plugin_config.bingchat_adapters:
    from .console.main import __name__
if 'kaiheila' in plugin_config.bingchat_adapters:
    from .kaiheila.main import __name__
if 'onebotv11' in plugin_config.bingchat_adapters:
    from .onebotv11.main import __name__
if 'onebotv12' in plugin_config.bingchat_adapters:
    from .onebotv12.main import __name__
if 'qqguild' in plugin_config.bingchat_adapters:
    from .qqguild.main import __name__
if 'telegram' in plugin_config.bingchat_adapters:
    from .telegram.main import __name__


logger.opt(colors=True).warning('<red>你使用的是开发版，可能会出现未知错误，请及时反馈</red>')
