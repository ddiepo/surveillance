import os

class PipesWatcher:
    """ This class watches pipes and when there is data reads a line at a time and sends to the 
        callback function.  Multiple pipes can be watched."""

    def __init__(self, files_to_monitor):
        self._pipes = []
        for path in files_to_monitor:
            if (os.path.exists(path)):
                os.unlink(path)
            os.mkfifo(path)
            pipe_fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            self._pipes.append((os.fdopen(pipe_fd), path))

    def __del__(self):
        for pipe in self._pipes:
            pipe[0].close()
            try:
                os.unlink(pipe[1])
            except OSError:
                pass
            
    def check(self, func):
        for pipe in self._pipes:
            message = pipe[0].readline().rstrip('\n')
            if message:
                func(message, pipe[1])

