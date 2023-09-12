__all__ = ['whoami', 'WhoamiObject']

import sys


def whoami(depth=1):
    return f"{sys._getframe(depth).f_code.co_name}()"


class WhoamiObject(object):
    @classmethod
    def whoami(cls):
        return f"{cls.__name__}.{whoami()}"
