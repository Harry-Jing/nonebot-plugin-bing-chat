class BaseBingChatException(Exception):
    pass

class BingChatPermissionDeniedException(BaseBingChatException):
    pass

class BingchatReachLimitException(BingChatPermissionDeniedException):
    pass

class BingChatGroupPermissionDeniedException(BingChatPermissionDeniedException):
    pass