from .api.blueprint import bp as api
from .redirection.blueprint import bp as redirection
from .misc import bp as misc


__all__ = [redirection, api, misc]
