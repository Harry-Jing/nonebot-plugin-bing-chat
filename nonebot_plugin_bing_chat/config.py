from pydantic import BaseModel, Extra, validator

class Config(BaseModel, extra=Extra.ignore):
    bingchat_output = 'text'
    bingchat_command_chat: str | list[str] = ['chat']
    bingchat_command_new_chat: str | list[str] = ['刷新对话']
    bingchat_allow_group = True

    @validator('bingchat_command_chat')
    def bingchat_command_chat_validator(cls, v):
        return list(v)

    @validator('bingchat_command_new_chat')
    def bingchat_command_new_chat_validator(cls, v):
        return list(v)