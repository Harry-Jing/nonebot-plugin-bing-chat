<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://raw.githubusercontent.com/Harry-Jing/nonebot-plugin-bing-chat/main/resources/NoneBot_Plugin_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://raw.githubusercontent.com/Harry-Jing/nonebot-plugin-bing-chat/main/resources/NoneBot_Plugin_text.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-bing-chat

_✨ 一个可以使用新版Bing进行聊天的插件 ✨_


<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/Harry-Jing/nonebot-plugin-bing-chat.svg" alt="license" />
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-bing-chat">
  <img src="https://img.shields.io/pypi/v/nonebot-plugin-bing-chat.svg" alt="pypi" />
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-bing-chat">
  <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/nonebot-plugin-bing-chat">
</a>

<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python" />

</div>


> - <b> 在v0.3.3支持更好的错误处理 </b>
> - <b> 在v0.3.4支持自动刷新已到达上限的对话，需要手动配置开启 </b>


## 📖 介绍

一个可以使用新版Bing进行聊天的插件

QQ群：366731501

能否给孩子一个star🌟吗

> 仅支持onebot v11
>
> 如果你有更多需求，请发布[issue](https://github.com/Harry-Jing/nonebot-plugin-bing-chat/issues/new)让我知道

## 💿 安装与更新

<details>
<summary> <b> 使用 nb-cli 安装与更新 </b> </summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-bing-chat --upgrade

</details>

<details>
<summary> <b> 使用包管理器安装与更新 </b></summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

    pip install nonebot-plugin-bing-chat ---upgrade


打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_bing_chat"]

</details>

## ⚙️ 配置
<details>
<summary> <b> 在 nonebot2 项目的`data/BingChat`文件中添加`cookies.json（必须） </b> </summary>

- 在浏览器安装 `cookie-editor` 的插件 
  - [Chrome/Edge](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)（需要魔法）
  - [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
- 打开[`www.bing.com`](https://www.bing.com/)（需要魔法）（**不是**`cn.bing.com`）
- 打开 `cookie-editor` 插件
- 点击右下角的 `Export` 按钮（这会把cookie保存到你的剪切板上）
- 把你复制道德内容放到 `cookies.json` 文件里
 <img src="https://raw.githubusercontent.com/Harry-Jing/nonebot-plugin-bing-chat/main/resources/How_to_export_cookies.png" max-height="100" alt="How_to_export_cookies" />
  
</details>


<details>
<summary> <b> 在 nonebot2 项目的`.env`文件中添加下表中的配置（都为可选项） </b> </summary>

<b> 对默认的命令进行修改 </b>
| 配置项 | 类型 | 默认值 | 说明 |
|:-----:|:-----:|:----:|:----:|
| bingchat_command_chat | str/list[str] | ["chat"] | 对话命令 |
| bingchat_command_new_chat | str/list[str] | ["chat-new", "刷新对话"] | 新建对话命令 |
| bingchat_command_history_chat | str/list[str] | ["chat-history"] | 返回历史对话命令 |
  
 <b> 对行为进行配置 </b>
| 配置项 | 类型 | 默认值 | 说明 |
|:-----:|:-----:|:----:|:----:|
| bingchat_auto_refresh_conversation | bool | False | 到达命令上线后是否自动刷新 |

<b> 对特定群聊进行屏蔽 </b>
| 配置项 | 类型 | 默认值 | 说明 |
|:-----:|:-----:|:----:|:----:|
| bingchat_group_filter_mode | "whitelist"/"blacklist" | "blacklist" | 对群聊屏蔽的模式 |
| bingchat_group_filter_blacklist | list[int] | [] | 黑名单列表 |
| bingchat_group_filter_whitelist | list[int] | [] | 白名单列表 |
  
</details>

## 🎉 使用
### 指令表
以下为指令可以在配置文件中更改
| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| chat | 所有人 | 否 | 私聊/群聊 | 与Bing进行对话 |
| chat-new | 所有人 | 否 | 私聊/群聊 | 新建一个对话 |
| chat-history | 所有人 | 否 | 私聊/群聊 | 返回历史对话 |

  
## 📄 ToDo

<details>
  
  如果你有更多需求，请发布[issue](https://github.com/Harry-Jing/nonebot-plugin-bing-chat/issues/new)让我知道

</details>


  
## 🌸 致谢
- [@A-kirami](https://github.com/A-kirami)  项目使用了README[模板](https://github.com/A-kirami/nonebot-plugin-template)
- [@acheong08](https://github.com/acheong08)  项目使用了与Bing通讯的接口 [EdgeGPT](https://github.com/acheong08/EdgeGPT)
