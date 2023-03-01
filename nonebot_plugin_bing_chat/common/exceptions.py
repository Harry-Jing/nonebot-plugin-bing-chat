"""
exception hierarchy:

BaseBingChatException
    · BingChatPermissionDeniedException
        - BingchatReachLimitException
        - BingChatGroupNotInListException
        - BingchatIsWaitingForResponseException
    · BingchatNetworkException
        - BingChatResponseException
            + BingChatAccountReachLimitException
            + BingChatConversationReachLimitException
      
"""


class BaseBingChatException(Exception):
    pass


class BingChatPermissionDeniedException(BaseBingChatException):
    pass


class BingchatReachLimitException(BingChatPermissionDeniedException):
    pass


class BingChatGroupNotInListException(BingChatPermissionDeniedException):
    pass


class BingchatIsWaitingForResponseException(BingChatPermissionDeniedException):
    pass


class BingchatNetworkException(BaseBingChatException):
    pass


class BingChatResponseException(BingchatNetworkException):
    pass


class BingChatAccountReachLimitException(BingChatResponseException):
    pass


class BingChatConversationReachLimitException(BingChatResponseException):
    pass
