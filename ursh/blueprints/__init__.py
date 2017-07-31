from .api.blueprint import bp as api
from .redirection.blueprint import bp as redirection


__all__ = [redirection, api]
