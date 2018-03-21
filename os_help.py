import os
import errno


def ignore_exist(func, path):
    """ Ignore errno.EEXIST or errno.ENOENT exceptions """
    try:
        func(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        elif exc.errno == errno.ENOENT:
            pass
        else:
            raise


def ignore_exist2(func, src, dest):
    """ Ignore errno.EEXIST or errno.ENOENT exceptions """
    try:
        func(src, dest)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise
