from .api.blueprint import bp as api
from .misc import bp as misc
from .redirection import bp as redirection


__all__ = [redirection, api, misc]
