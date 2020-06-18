import sys

def whoami(depth=1):
    return f"{sys._getframe(depth).f_code.co_name}()"
