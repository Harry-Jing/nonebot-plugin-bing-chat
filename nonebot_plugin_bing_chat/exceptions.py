class BaseBingChatException(Exception):
    pass


class BingChatPermissionDeniedException(BaseBingChatException):
    pass


class BingChatGroupNotInListException(BingChatPermissionDeniedException):
    pass


class BingchatReachLimitException(BingChatPermissionDeniedException):
    pass


class BingchatIsWaitingForResponseException(BingChatPermissionDeniedException):
    pass


class BingchatNetworkException(BaseBingChatException):
    pass


class BingChatResponseException(BingchatNetworkException):
    pass
