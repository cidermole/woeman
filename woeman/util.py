import inspect


def overrides(interface_class):
    """
    Decorator to indicate that a method overrides a parent's method.
    Usage:
        @overrides(ParentClass)
        def method(self):
            pass
    """
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider


def obtain_caller_local_var(key, depth):
    """obtain variable 'key' in the caller's stack frame at 'depth', or None otherwise."""
    frame = inspect.currentframe()
    try:
        f = frame
        for i in range(depth):
            f = f.f_back
        return f.f_locals[key] if key in f.f_locals else None
    finally:
        del frame


def transfer_caller_local_vars(target, depth):
    """
    Copy all local variables in the caller's stack frame at 'depth' to make attributes on the 'target' object.
    Excludes the 'self' variable.
    """
    frame = inspect.currentframe()
    try:
        f = frame
        for i in range(depth):
            f = f.f_back
        for key in f.f_locals:
            if key != 'self':
                object.__setattr__(target, key, f.f_locals[key])
    finally:
        del frame

