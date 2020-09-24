import sys

def whoami(depth=1):
    return f"{sys._getframe(depth).f_code.co_name}()"

class WhoamiObject:
    def whoami(self):
        return f"{self.__class__.__name__}.{whoami(2)}"
