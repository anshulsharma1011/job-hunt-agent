class SourceBlockedError(Exception):
    pass



class BudgetExceededError(Exception):
    pass


class SchemaValidationError(Exception):
    pass


class LLMTimeoutError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass
