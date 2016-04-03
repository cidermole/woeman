import inspect


class Brick:
    """Implicit base class for all Bricks, monkey-patched in."""
    # note: currently does not include monkey-patched attributes here, but we could mention them for doc purposes.
    pass


class Input:
    """Denotes that a Brick class member is an input."""
    def __init__(self, brick, name, ref):
        """
        :param brick: the object this Input belongs to
        :param name:  Input name
        :param ref:   the Output which this Input references
        """
        self.brick, self.name, self.ref = brick, name, ref

    def __repr__(self):
        return 'Input(%s, %s, %s)' % (self.brick.__class__, self.name, self.ref)


class Output:
    """Denotes that a Brick class member is an output."""
    def __init__(self, brick, name):
        """
        :param brick: the object this Input belongs to
        :param name:  Input name
        """
        self.brick, self.name = brick, name

    def __repr__(self):
        return 'Output(%s, %s)' % (self.brick.__class__, self.name)


class BrickConfigError(TypeError):
    """Raised for a Brick class with invalid configuration."""
    def __init__(self, *args, **kwargs):
        TypeError.__init__(self, *args, **kwargs)


class BrickDecorator:
    """Factory for Brick classes (not instances), used by @brick decorator."""
    def __init__(self, cls):
        self.cls = cls
        self.brick_ident = 'Brick %s in file "%s", line %d' % (cls.__name__, inspect.getsourcefile(cls), inspect.getsourcelines(cls)[1])
        self.init_args_mandatory = []
        self.init_args_optional = []
        self.inputs = []
        self.outputs = []

    def create(self):
        """Return the wrapped Brick class."""
        self.parseInputs()
        self.parseOutputs()

        self.patchConstructor()
        self.patchFields()
        self.patchClass()

        return self.cls

    def parseInputs(self):
        # constructor arguments define Brick inputs
        if not '__init__' in dir(self.cls):
            raise BrickConfigError('missing mandatory __init__() which defines its inputs in %s' % self.brick_ident)
        input_func = self.cls.__init__

        # constructor argument names, in order
        init_args = input_func.__code__.co_varnames[1:input_func.__code__.co_argcount]  # except 'self'

        # default arguments (apply at end of arguments, in order)
        defaults = list(input_func.__defaults__) if input_func.__defaults__ is not None else []

        # argument list for new constructor, with default values at the end
        num_mandatory = len(init_args) - len(defaults)
        self.init_args_mandatory = list(init_args[0:num_mandatory])
        self.init_args_optional = ['%s=%s' % (a, str(d)) for a, d in zip(init_args[num_mandatory:], defaults)]
        self.inputs = init_args

    def parseOutputs(self):
        # arguments of output() define Brick outputs
        if not 'output' in dir(self.cls):
            raise BrickConfigError('missing mandatory output() which defines Brick outputs in %s' % self.brick_ident)
        output_func = self.cls.output

        # output argument names, in order
        output_args = output_func.__code__.co_varnames[1:output_func.__code__.co_argcount]  # except 'self'
        if len(output_args) == 0:
            raise BrickConfigError('need at least one output in %s' % self.brick_ident)
        self.outputs = output_args

    def patchConstructor(self):
        """Monkey-patch Brick class: wrap constructor"""
        cls = self.cls

        # TODO: how to set Python source and line numbers so we get reasonable stacktraces if the generated code fails?

        # these must be available at the time the Brick constructor is actually called
        cls._Input = Input
        cls._Output = Output
        cls._brick_init = cls.__init__  # to call the original __init__() later
        cls._brick_setup = brick_setup

        # body for new constructor
        init_code = 'def brick_init(' + ', '.join(['self'] + self.init_args_mandatory + self.init_args_optional) + '):\n'
        # inputs
        for arg in self.inputs:
            init_code += '    self.%s = %s._Input(self, "%s", %s)\n' % (arg, cls.__name__, arg, arg)
        # outputs
        for arg in self.outputs:
            init_code += '    self.%s = %s._Output(self, "%s")\n' % (arg, cls.__name__, arg)

        init_code += '    self._brick_setup()\n'

        # need to call the precise class's method (even in an inheritance structure)
        # (otherwise super class will call into subclass' _brick_init(), and we have an infinite recursion)
        init_code += '    ' + cls.__name__ + '._brick_init(' + ', '.join(['self'] + list(self.inputs)) + ')'

        init_code += '\n%s.__init__ = brick_init\n' % cls.__name__  # replace class constructor ("monkey patching")

        ns = {cls.__name__: cls}
        exec(init_code, ns)

    def patchFields(self):
        """Monkey-patch Brick class: add some fields: _brick_inputs, _brick_outputs"""
        self.cls._brick_inputs = self.inputs
        self.cls._brick_outputs = self.outputs

    def patchClass(self):
        """Append Brick as a base class."""

        # exclude 'object' as a base, which should always come first, and which causes an error:
        # TypeError: Cannot create a consistent method resolution order (MRO) for bases object, ...
        #self.cls = self.cls.__class__(self.cls.__name__, self.cls.__class__.__bases__[1:] + (Brick,), {})
        # (self.cls,) + self.cls.__class__.__bases__[1:] + (Brick,)

        #import sys
        #sys.stderr.write('bases[1] = %s\n' % str(self.cls.__class__.__bases__[1]))

        #self.cls = self.cls.__class__(self.cls.__name__, (self.cls,) + (Brick,), {})
        self.cls = self.cls.__class__(self.cls.__name__, (self.cls,) + self.cls.__class__.__bases__[1:] + (Brick,), {})


def brick(cls):
    """Decorator for Brick class definitions."""
    return BrickDecorator(cls).create()


def obtain_caller_local_var(key, depth=3):
    """obtain variable 'key' in the caller's stack frame at 'depth', or None otherwise."""
    frame = inspect.currentframe()
    try:
        f = frame
        for i in range(depth):
            f = f.f_back
        return f.f_locals[key] if key in f.f_locals else None
    finally:
        del frame


def brick_setup(self):
    """
    Find the parent Brick instance (if present) that this Brick instance is attached to, set paths, ...
    Part of the Brick constructor code that is monkey-patched in.
    """
    # obtain variables in the (Brick constructor) caller's frame, to get 'self' which is our parent
    # call stack: <call_site> -> BrickClass.__init__() -> brick_setup() -> obtain_caller_local_var()
    parent = obtain_caller_local_var('self', depth=3)
    if parent is not None and isinstance(parent, Brick):
        # Brick is part of another Brick (was defined in a Brick constructor [currently, in any Brick method.])
        self.parent = parent
    else:
        # top-level Brick, i.e. Experiment
        self.parent = None
