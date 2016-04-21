import inspect

from .brick import Brick, Input, Output, BrickConfigError


class BrickDecorator:
    """Factory for Brick classes (not instances), used by @brick decorator."""
    def __init__(self, cls):
        self.cls = cls
        self.brick_ident = brick_ident(cls)
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
            raise BrickConfigError('need to override output() with at least one argument in %s' % self.brick_ident)
        self.outputs = output_args

    def patchConstructor(self):
        """Monkey-patch Brick class: wrap constructor"""
        cls = self.cls

        # TODO: how to set Python source and line numbers so we get reasonable stacktraces if the generated code fails?

        # these must be available at the time the Brick constructor is actually called
        cls._Brick = Brick
        cls._Input = Input
        cls._Output = Output
        cls._brick_init = cls.__init__  # to call the original __init__() later

        # body for new constructor
        init_code = 'def brick_init(' + ', '.join(['self'] + self.init_args_mandatory + self.init_args_optional) + '):\n'
        init_code += '    %s._Brick.__init__(self)\n' % (cls.__name__)
        # inputs
        for arg in self.inputs:
            init_code += '    self.%s = %s._Input(self, "%s", %s)\n' % (arg, cls.__name__, arg, arg)
        # outputs
        for arg in self.outputs:
            init_code += '    self.%s = %s._Output(self, "%s")\n' % (arg, cls.__name__, arg)

        init_code += '    self._brick_setup_pre_init()\n'

        # need to call the precise class's method (even in an inheritance structure)
        # (otherwise super class will call into subclass' _brick_init(), and we have an infinite recursion)
        # pass the Input() wrapped args to the original __init__() - makes wiring through to parts easier
        selfInputs = ['self.%s' % input_name for input_name in self.inputs]
        init_code += '    ' + cls.__name__ + '._brick_init(' + ', '.join(['self'] + selfInputs) + ')\n'

        init_code += '    self._brick_setup_post_init()\n'

        init_code += '%s.__init__ = brick_init\n' % cls.__name__  # replace class constructor ("monkey patching")

        ns = {cls.__name__: cls}
        exec(init_code, ns)

    def patchFields(self):
        """Monkey-patch Brick class: initialize some class attributes of Brick."""
        cls = self.cls
        cls._brick_inputs = self.inputs
        cls._brick_outputs = self.outputs
        cls._brick_ident = self.brick_ident
        cls._brick_sourcefile = inspect.getsourcefile(cls)
        cls._brick_fullname = cls.__module__ + "." + cls.__name__

    def patchClass(self):
        """Append Brick as a base class."""
        cls = self.cls
        # [1:]: exclude 'object' as a base, which should always come first in __bases__
        bases = tuple([base for base in cls.__class__.__bases__[1:] if base != Brick])
        self.cls = cls.__class__(cls.__name__, (cls,) + bases + (Brick,), {})

        # note: class hierarchy:
        # Experiment[wrap] -> (Experiment[code], bases..., Brick)
        #
        # (this may not be ideal, especially if people derive Experiment[code] explicitly from Brick...)
        # (also, it is currently difficult to get the super(Experiment, self) style __init__ and other calls right)


def brick(cls):
    """Decorator for Brick class definitions."""
    return BrickDecorator(cls).create()


def brick_ident(cls):
    return 'Brick %s in file "%s", line %d' % (cls.__name__, inspect.getsourcefile(cls), inspect.getsourcelines(cls)[1])
