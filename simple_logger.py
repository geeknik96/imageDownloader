__author__ = 'lukyanets'


class SimpleLogger:
    def __init__(self, thread: str='Main thread', prefix: str=''):
        self.thread = thread
        self.prefix = prefix

    def log(self, *args, **kwargs):
        args_msg = ', '.join(args)
        kwargs_msg = ', '.join('{0} -> {1}'.format(name, value) for (name, value) in sorted(kwargs.items()))
        msg = ''
        if not args_msg and not kwargs_msg:
            return
        elif args_msg:
            msg = args_msg + ('; ' + kwargs_msg if kwargs_msg else '')
        else:
            msg = kwargs_msg
        print((self.thread + ': ' + ('[{0}] '.format(self.prefix) if self.prefix else '') + msg).encode())

    def update_prefix(self, prefix: str=''):
        self.prefix = prefix
