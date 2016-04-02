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


def brick(cls):
    """
    Decorator for Brick classes. Wraps the constructor and sets a number of useful properties:
    * _brick_input: a tuple of str input names in order
    * _brick_output: a tuple of str output names in order
    :param cls: Brick class definition
    """

    brick_ident = 'Brick %s [%s:%d]' % (cls.__name__, inspect.getsourcefile(cls), inspect.getsourcelines(cls)[1])

    # constructor arguments define Brick inputs
    if not '__init__' in dir(cls):
        raise TypeError('%s is missing mandatory __init__() which defines its inputs' % brick_ident)
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
        raise TypeError('%s is missing mandatory output() which defines its outputs' % brick_ident)
    output_func = cls.output

    # output argument names, in order
    output_args = output_func.__code__.co_varnames[1:output_func.__code__.co_argcount]  # except 'self'
    if len(output_args) == 0:
        raise TypeError('%s needs at least one output' % brick_ident)
    cls._brick_output = output_args

    #########

    # body for new constructor
    init_code = 'def brick_init(' + ', '.join(['self'] + mandatory + optional) + '):\n'
    # inputs
    for arg in init_args:
        init_code += '    self.%s = Input(self, "%s", %s)\n' % (arg, arg, arg)
    # outputs
    for arg in output_args:
        init_code += '    self.%s = Output(self, "%s")\n' % (arg, arg)

    # need to call the precise class's method (even in an inheritance structure)
    # (otherwise super class will call into subclass' _brick_init(), and we have an infinite recursion)
    init_code += '    ' + cls.__name__ + '._brick_init(' + ', '.join(['self'] + list(init_args)) + ')'

    brick_init = None  # make IDE happy. replaced in exec()

    # compile the new constructor
    exec(init_code)

    # replace class constructor
    cls.__init__ = brick_init

    return cls
