class ResourceNotFoundError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ResourceConflictError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
