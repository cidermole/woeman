import collections
import inspect
import traceback
import os

import jinja2

from .util import obtain_caller_local_var, transfer_caller_local_vars
from brick_config import config


class Brick:
    """Implicit base class for all Bricks, monkey-patched in as a base class by the @brick decorator."""

    # these are set from BrickDecorator.patchFields()
    _brick_init = None       # original __init__() of Brick
    _brick_inputs = None     # list of input names
    _brick_outputs = None    # list of output names
    _brick_ident = None      # str identifying the Brick for debugging, see brick_ident()
    _brick_sourcefile = None # source file where the Brick was defined
    _brick_fullname = None   # fully qualified Brick class name such as 'woeman.bricks.v1.lm.KenLM'

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

    # this is annotated @staticmethod to make IDE happy at the call sites (monkey-patched inheritance which IDE is unaware of).
    @staticmethod
    def configure(self, config_dict):
        """
        Configuration parameters that are not data inputs, defined through parameters in the override of this method.
        The overrides of configure() should implement a chain of configure() calls into every brick part.
        This super configure() on Brick sets local variables from 'config_dict' on the object.
        """
        for key in config_dict:
            if key != 'self':
                object.__setattr__(self, key, config_dict[key])

    def loadDefaultConfig(self):
        """Load default configuration into class attributes. Values either come from 'woeman/bricks/v1/woeman.cfg'
        or can be overridden by the user in '~/.config/woeman/woeman.cfg'."""

        # load from user's config file override if it exists, or fall back to 'woeman.cfg' we ship with woeman
        userCfg = os.path.join(os.path.expanduser('~'), '.config', 'woeman', 'woeman.cfg')
        woemanDefaultCfg = os.path.join(Brick._brick_base_template_dir(), 'woeman.cfg')
        if os.path.exists(userCfg):
            cfgFileName = userCfg
        else:
            cfgFileName = woemanDefaultCfg

        # search path for @<v1/included.cfg> style includes in config files
        searchPath = os.path.dirname(Brick._brick_base_template_dir())

        configSearchPath = config.ConfigSearchPath([searchPath])
        cfg = config.Config(open(cfgFileName), searchPath=configSearchPath)
        cfg = cfg.instantiate()

        # configure ourselves and parts recursively
        self._load_default_config(cfg)

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

    def brickTargetPath(self):
        """Returns the path to this Brick instance's do target (build system target file)."""
        return os.path.join(self._brick_path, 'brick')

    def brickDoPath(self):
        """Returns the path to this Brick instance's do script, which is the shell script specifying its execution."""
        return os.path.join(self._brick_path, 'brick.do')

    def brickPath(self):
        """Path to this Brick instance's run directory, containing brick.do, input/ and output/"""
        return self._brick_path

    @classmethod
    def jinjaTemplatePath(cls, subclass=None):
        """Returns the path to this Brick's Jinja template, commonly located in the same Python package as the class."""
        if subclass is None:
            subclass = cls
        packagePath = os.path.dirname(subclass._brick_sourcefile)
        jinjaFile = '%s.jinja.do' % subclass.__name__
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

    def dependencyFiles(self, type):
        """
        Returns the list of input or output (part) dependencies (build system target files).
        Provided to the build system by the Jinja base template 'Brick.jinja.do'.
        :param type: either 'input' or 'output'
        """
        if type == 'input':
            inout_names = self._brick_inputs
        elif type == 'output':
            inout_names = self._brick_outputs
        else:
            raise BrickConfigError('Invalid type in dependencyFiles() in %s' % self._brick_ident)

        deps = []
        for d in self._inout_dependencies(inout_names):
            deps.append(os.path.relpath(d.brickTargetPath(), self._brick_path))
        return deps

    def _inout_dependencies(self, inout_names):
        """Return the list of all Input/Output dependencies depending on
        whether self._brick_inputs or self._brick_outputs is passed in."""
        deps = []
        for inout_name in inout_names:
            deps += self.__getattribute__(inout_name).dependencies()
        return deps

    def _load_default_config(self, configRoot):
        """Load default configuration into class attributes. Config mappings correspond to the Python namespace from v1,
        so the class attributes of 'bricks.v1.lm.KenLM' can be configured as `lm: { KenLM: { mosesDir: "/dir" } }`"""
        _brick_fullname = None

        # find config map for the current Brick, or walk the parent classes to find one which has a config map
        cls = self.__class__
        while True:
            # _brick_fullname 'woeman.bricks.v1.lm.KenLM' -> entryPath 'lm.KenLM'
            entryPath = '.'.join(cls._brick_fullname.split('.')[3:])
            try:
                configEntry = configRoot.getByPath(entryPath)
                break
            except config.ConfigError as e:
                # key not found, check if there are parents
                possible_brick_parent = len(self.__class__.__bases__) > 0 and len(self.__class__.__bases__[0].__bases__) > 0
                cls = self.__class__.__bases__[0].__bases__[0] if possible_brick_parent else None

                if cls is None or not '_brick_fullname' in dir(cls):
                    raise BrickConfigError('Could not get config key "%s" for loading default config for class attributes in %s' % (entryPath, self._brick_ident))

        # set class attributes available from config keys
        for attr_name in dir(self.__class__):
            if attr_name.startswith('_'):
                # skip builtin names and brick info class attributes
                continue
            if attr_name in configEntry:
                object.__setattr__(self, attr_name, configEntry[attr_name])

        # recursively configure all parts
        for part in self._brick_parts:
            part._load_default_config(configRoot)

    @classmethod
    def _brick_base_template_dir(cls):
        """Absolute path to 'woeman/bricks/v1' directory.
        Template directory base for Jinja search path and 'woeman.cfg'."""
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
        """For debugging"""
        return 'Input(%s, %s, %s)' % (self.brick.__class__.__name__, self.name, self.ref)

    def __str__(self):
        """For insertion as an absolute path in Jinja templates"""
        return self.getPath()

    def getPath(self):
        """Absolute filesystem path to this Input."""
        return os.path.join(self.brick._brick_path, 'input', self.name)

    def createSymlink(self, filesystem):
        """
        Create the filesystem symlink for this Input.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        filesystem.makedirs(os.path.dirname(self.getPath()))
        if self._isDependent():
            # wiring of input to other bricks, either wiring through inputs or wiring to an output
            refPath = self.ref.getPath()
        else:
            # direct definition of input as a path string
            refPath = str(self.ref)
        filesystem.symlink(refPath, self.getPath())

    def dependencies(self):
        """Return list of brick objects which this Input depends on."""
        if self._isDependent():
            return [self.ref.brick]
        else:
            return []

    def _isDependent(self):
        """Whether this Input is wired to another brick's Input or Output."""
        return isinstance(self.ref, Input) or isinstance(self.ref, Output)

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
        """For debugging"""
        if self.ref is None:
            return 'Output(%s, %s)' % (self.brick.__class__, self.name)
        else:
            return 'Output(%s, %s, %s)' % (self.brick.__class__, self.name, self.ref)

    def __str__(self):
        """For insertion as an absolute path in Jinja templates"""
        return self.getPath()

    def getPath(self):
        """Absolute filesystem path to this Input."""
        return os.path.join(self.brick._brick_path, 'output', self.name)

    def createSymlink(self, filesystem):
        """
        Create the filesystem symlink for this Output.
        :param filesystem: an fs.FilesystemInterface object to abstract filesystem calls
        """
        filesystem.makedirs(os.path.dirname(self.getPath()))
        if self._isDependent():
            # output is bound to other brick's Output (part's Output)
            refPath = self.ref.getPath()
        elif self.ref is None:
            # output left unbound: file written by the Brick's script body
            return
        else:
            raise BrickConfigError('output "%s" must either be bound to a part\'s output or left unbound.' % self.name)
        filesystem.symlink(refPath, self.getPath())

    def dependencies(self):
        """Return list of brick objects which this Output depends on."""
        if self._isDependent():
            return [self.ref.brick]
        else:
            return []

    def _isDependent(self):
        """Whether this Output is bound to another brick's Output (part's Output)."""
        return isinstance(self.ref, Output)


class BrickConfigError(TypeError):
    """Raised for a Brick class with invalid configuration."""
    def __init__(self, *args, **kwargs):
        TypeError.__init__(self, *args, **kwargs)
