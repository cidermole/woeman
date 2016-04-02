import inspect


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


def brick(cls):
    """
    Decorator for Brick classes. Wraps the constructor and sets a number of useful properties:
    * _brick_input: a tuple of str input names in order
    * _brick_output: a tuple of str output names in order
    :param cls: Brick class definition
    """

    brick_ident = 'Brick %s in File "%s", line %d' % (cls.__name__, inspect.getsourcefile(cls), inspect.getsourcelines(cls)[1])

    # constructor arguments define Brick inputs
    if not '__init__' in dir(cls):
        raise BrickConfigError('missing mandatory __init__() which defines its inputs in %s' % brick_ident)
    input_func = cls.__init__
    cls._brick_init = input_func  # back up to call it later

    # constructor argument names, in order
    init_args = input_func.__code__.co_varnames[1:input_func.__code__.co_argcount]  # except 'self'
    cls._brick_input = init_args

    # default arguments (apply at end of arguments, in order)
    defaults = list(input_func.__defaults__) if input_func.__defaults__ is not None else []

    # argument list for new constructor, with default values at the end
    num_mandatory = len(init_args) - len(defaults)
    mandatory = list(init_args[0:num_mandatory])
    optional = ['%s=%s' % (a, str(d)) for a, d in zip(init_args[num_mandatory:], defaults)]

    #########

    # arguments of output() define Brick outputs
    if not 'output' in dir(cls):
        raise BrickConfigError('missing mandatory output() which defines Brick outputs in %s' % brick_ident)
    output_func = cls.output

    # output argument names, in order
    output_args = output_func.__code__.co_varnames[1:output_func.__code__.co_argcount]  # except 'self'
    if len(output_args) == 0:
        raise BrickConfigError('need at least one output in %s' % brick_ident)
    cls._brick_output = output_args

    #########

    # these must be available at the time the Brick constructor is actually called
    cls._Input = Input
    cls._Output = Output

    # TODO: how to set Python source and line numbers so we get reasonable stacktraces if the generated code fails?

    # body for new constructor
    init_code = 'def brick_init(' + ', '.join(['self'] + mandatory + optional) + '):\n'
    # inputs
    for arg in init_args:
        init_code += '    self.%s = %s._Input(self, "%s", %s)\n' % (arg, cls.__name__, arg, arg)
    # outputs
    for arg in output_args:
        init_code += '    self.%s = %s._Output(self, "%s")\n' % (arg, cls.__name__, arg)

    # need to call the precise class's method (even in an inheritance structure)
    # (otherwise super class will call into subclass' _brick_init(), and we have an infinite recursion)
    init_code += '    ' + cls.__name__ + '._brick_init(' + ', '.join(['self'] + list(init_args)) + ')'

    init_code += '\n%s.__init__ = brick_init\n' % cls.__name__  # replace class constructor ("monkey patching")

    brick_init = None  # make IDE happy. replaced in exec()

    # compile the new constructor

    # note: strangely, if the actual method definition of brick_init() is here in brick(cls) locally, it seems to be
    # garbage-collected away; the Brick constructor fails at runtime with "TypeError: 'NoneType' object is not callable."
    # We need to make sure it exists in some namespace, so let's put it directly onto the class itself within exec().
    ns = {cls.__name__: cls}
    exec(init_code, ns)

    return cls
