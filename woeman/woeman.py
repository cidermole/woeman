from .util import obtain_caller_local_var, transfer_caller_local_vars
import inspect
import collections
import jinja2
import os


class Brick:
    """Implicit base class for all Bricks, monkey-patched in as a base class by the @brick decorator."""

    # these are set from BrickDecorator.patchFields()
    _brick_init = None       # original __init__() of Brick
    _brick_inputs = None     # list of input names
    _brick_outputs = None    # list of output names
    _brick_ident = None      # str identifying the Brick for debugging, see brick_ident()
    _brick_sourcefile = None # source file where the Brick was defined

    def __init__(self):
        # this runs on instances, i.e. later than BrickDecorator.create() which runs on class definitions
        if '_brick_initialized' in dir(self):
            # already initialized, when brick __init__ (unnecessarily) calls the super __init__ (us here) explicitly
            return
        self._brick_initialized = True
        self._brick_parts = []          # list of parts (children) in definition order
        self._brick_path = None         # filesystem path to Brick directory

    def output(self, *args):
        """Brick outputs defined through parameters of this method. This method may bind() outputs to parts."""
        pass

    def configure(self, *args):
        """
        Configuration parameters that are not data inputs, defined through parameters in the override of this method.
        Call this super method from configure() in order to automatically set local variables on the object (do not
        pass any arguments).
        """
        if len(args) > 0:
            raise BrickConfigError('Do not pass args to Brick.configure(), it grabs all local vars in %s' % self._brick_ident)
        # call stack: brick.configure() -> woeman.Brick.configure() -> transfer_caller_local_vars()
        transfer_caller_local_vars(self, depth=2)

    def render(self):
        """Render the Jinja script template of this Brick."""
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=Brick._brick_base_template_dir()))
        template = env.get_template(self.jinjaTemplatePath())
        # should we exclude methods like render, output, configure here?
        context = {k: self.__getattribute__(k) for k in dir(self) if not k.startswith('_')}
        brickDo = template.render(context)
        return brickDo  # to do: write to disk, if changed

    def write(self, filesystem):
        """
        Render and write script templates recursively to the filesystem.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        filesystem.replaceFileContents(self.brickDoPath(), self.render())
        for part in self._brick_parts:
            part.write(filesystem)

    def brickDoPath(self):
        """Returns the path to this Brick instance's do script, which is the shell script specifying its execution."""
        return os.path.join(self._brick_path, 'brick.do')

    def jinjaTemplatePath(self):
        """Returns the path to this Brick's Jinja template, commonly located in the same Python package as the class."""
        packagePath = os.path.dirname(self._brick_sourcefile)
        jinjaFile = '%s.jinja.do' % self.__class__.__name__
        # must be relative to searchpath of jinja2.Environment()... Jinja is not happy about an absolute path?!
        return os.path.join(os.path.relpath(packagePath, Brick._brick_base_template_dir()), jinjaFile)

    def setPath(self, path):
        """Recursively set filesystem path where this Brick will be executed."""
        # since there may be several parts of the same Brick type, the caller should set the Brick name.
        self._brick_path = path
        for part in self._brick_parts:
            part.setPath(os.path.join(self._brick_path, self._get_part_name(part)))

    def setBasePath(self, basePath):
        """
        Recursively set filesystem path above this Brick. Appends brick class name to the given 'basePath'.
        Use this only for top level Brick / Experiment.
        """
        self.setPath(os.path.join(basePath, self.__class__.__name__))

    def createInOuts(self, filesystem):
        """
        Recursively create directory structure and input/output symlinks for this brick and its parts.
        Filesystem path must have been set with setPath() or setBasePath() before.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        # create directories and symlinks for inputs and outputs
        for inout_name in self._brick_inputs + self._brick_outputs:
            self.__getattribute__(inout_name).createSymlink(filesystem)

        # recursively create for all parts
        for part in self._brick_parts:
            part.createInOuts(filesystem)

    @classmethod
    def _brick_base_template_dir(cls):
        """Absolute path to woeman/bricks/v1 directory. Template directory base for Jinja search path."""
        return os.path.join(os.path.dirname(inspect.getsourcefile(cls)), 'bricks', 'v1')

    def _brick_setup_pre_init(self):
        """
        Find the parent Brick instance (if present) that this Brick instance is attached to, set paths, ...
        Part of the Brick constructor code that is monkey-patched in. Called prior to the actual Brick constructor.
        """
        # obtain variables in the (Brick constructor) caller's frame, to get 'self' which is our parent
        # call stack: <call_site> -> BrickClass.__init__() -> _brick_setup_before_init() -> obtain_caller_local_var()
        parent = obtain_caller_local_var('self', depth=3)
        if parent is not None and isinstance(parent, Brick) \
                and parent != self:  # this is unwanted in an inheritance scenario when calling the base constructor
            # Brick is part of another Brick (was defined in a Brick constructor [currently, in any Brick method.])
            self.parent = parent
            self.parent._brick_parts.append(self)
        else:
            # top-level Brick, i.e. Experiment
            self.parent = None

    def _brick_setup_post_init(self):
        """
        Late setup that needs to access stuff set up in Brick constructor (like parts).
        """
        self._bind_outputs()

    def _bind_outputs(self):
        self.output(*[self.__getattribute__(output_name) for output_name in self._brick_outputs])

    def _get_part_name(self, part):
        """Find the attribute name that holds a reference to this part. May be contained in a list or dict attribute."""
        for attr_name in dir(self):
            if attr_name.startswith('__') or attr_name == '_brick_parts':
                continue
            attr = self.__getattribute__(attr_name)
            if isinstance(attr, Brick) and attr == part:
                # straight attribute name match (e.g. "part" for self.part = Part() in __init__())
                return attr_name
            elif isinstance(attr, collections.Iterable) and len(attr) > 0:
                # check list/dict (e.g. self.parts[0] = Part() in __init__())
                if isinstance(attr, list) and isinstance(attr[0], Brick):
                    # a list of Bricks, peek inside
                    for i, p in enumerate(attr):
                        if p == part:
                            return '%s_%d' % (attr_name, i)  # e.g. "parts_0"
                elif isinstance(attr, dict):
                    # a dict (maybe) containing Bricks, peek inside
                    for i, p in attr.items():
                        if not isinstance(p, Brick):  # make sure we have a dict of Bricks
                            break
                        if p == part:
                            return '%s_%s' % (attr_name, i)  # e.g. "parts_zero" for self.parts['zero'] = Part()
        raise BrickConfigError('Could not determine part name of part %s in %s' % (part.__class__.__name__, self._brick_ident))


class Input:
    """For Brick attributes representing an input."""
    def __init__(self, brick, name, ref):
        """
        :param brick: the object this Input belongs to
        :param name:  Input name
        :param ref:   the Output which this Input references
        """
        self.brick, self.name, self.ref = brick, name, ref

    def __repr__(self):
        return 'Input(%s, %s, %s)' % (self.brick.__class__, self.name, self.ref)

    def getPath(self):
        """Absolute filesystem path to this Input."""
        return os.path.join(self.brick._brick_path, 'input', self.name)

    def createSymlink(self, filesystem):
        """
        Create the filesystem symlink for this Input.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        filesystem.makedirs(os.path.dirname(self.getPath()))
        if isinstance(self.ref, Input) or isinstance(self.ref, Output):
            # wiring of input to other bricks, either wiring through inputs or wiring to an output
            refPath = self.ref.getPath()
        else:
            # direct definition of input as a path string
            refPath = str(self.ref)
        filesystem.symlink(refPath, self.getPath())


class Output:
    """For Brick attributes representing an output."""
    def __init__(self, brick, name):
        """
        :param brick: the object this Input belongs to
        :param name:  Input name
        """
        self.brick, self.name = brick, name
        self.ref = None

    def bind(self, ref):
        """Bind this Output to a part Brick's Output."""
        if ref.brick.parent != self.brick:
            raise BrickConfigError('Output.bind() of output "%s" must be given a part Brick in %s' %
                                   (self.name, self._brick_ident))
        self.ref = ref

    def __repr__(self):
        if self.ref is None:
            return 'Output(%s, %s)' % (self.brick.__class__, self.name)
        else:
            return 'Output(%s, %s, %s)' % (self.brick.__class__, self.name, self.ref)

    def getPath(self):
        """Absolute filesystem path to this Input."""
        return os.path.join(self.brick._brick_path, 'output', self.name)

    def createSymlink(self, filesystem):
        """
        Create the filesystem symlink for this Output.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        filesystem.makedirs(os.path.dirname(self.getPath()))
        if isinstance(self.ref, Output):
            # output is bound to other brick's output (part's output)
            refPath = self.ref.getPath()
        elif self.ref is None:
            # output left unbound: file written by the Brick's script body
            return
        else:
            raise BrickConfigError('output "%s" must either be bound to a part\'s output or left unbound.' % self.name)
        filesystem.symlink(refPath, self.getPath())


class BrickConfigError(TypeError):
    """Raised for a Brick class with invalid configuration."""
    def __init__(self, *args, **kwargs):
        TypeError.__init__(self, *args, **kwargs)


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
        """Monkey-patch Brick class: add some fields: _brick_inputs, _brick_outputs, _brick_ident"""
        self.cls._brick_inputs = self.inputs
        self.cls._brick_outputs = self.outputs
        self.cls._brick_ident = self.brick_ident
        self.cls._brick_sourcefile = inspect.getsourcefile(self.cls)

    def patchClass(self):
        """Append Brick as a base class."""
        # [1:]: exclude 'object' as a base, which should always come first in __bases__
        bases = tuple([base for base in self.cls.__class__.__bases__[1:] if base != Brick])
        self.cls = self.cls.__class__(self.cls.__name__, (self.cls,) + bases + (Brick,), {})

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
