# Copyright 2004-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This is a configuration module for Python.

This module should work under Python versions >= 2.2, and cannot be used with
earlier versions since it uses new-style classes.

Development and testing has only been carried out (so far) on Python 2.3.4 and
Python 2.4.2. See the test module (test_config.py) included in the
U{distribution<http://www.red-dove.com/python_config.html|_blank>} (follow the
download link).

A simple example - with the example configuration file::

    messages:
    [
      {
        stream : `sys.stderr`
        message: 'Welcome'
        name: 'Harry'
      }
      {
        stream : `sys.stdout`
        message: 'Welkom'
        name: 'Ruud'
      }
      {
        stream : $messages[0].stream
        message: 'Bienvenue'
        name: Yves
      }
    ]

a program to read the configuration would be::

    from brick_config import Config

    f = file('simple.cfg')
    cfg = Config(f)
    for m in cfg.messages:
        s = '%s, %s' % (m.message, m.name)
        try:
            print >> m.stream, s
        except IOError, e:
            print e

which, when run, would yield the console output::

    Welcome, Harry
    Welkom, Ruud
    Bienvenue, Yves

See U{this tutorial<http://www.red-dove.com/python_config.html|_blank>} for more
information.

@version: 0.3.9

@author: Vinay Sajip

@copyright: Copyright (C) 2004-2010 Vinay Sajip. All Rights Reserved.


@var streamOpener: The default stream opener. This is a factory function which
takes a string (e.g. filename) and returns a stream suitable for reading. If
unable to open the stream, an IOError exception should be thrown.

The default value of this variable is L{defaultStreamOpener}. For an example
of how it's used, see test_config.py (search for streamOpener).
"""

__author__  = "Vinay Sajip <vinay_sajip@red-dove.com>"
__status__  = "alpha"
__version__ = "0.3.9"
__date__    = "11 May 2010"

import codecs
import logging
import os
import re
import sys

WORD = 'a'
NUMBER = '9'
STRING = '"'
EOF = ''
LCURLY = '{'
RCURLY = '}'
LBRACK = '['
LBRACK2 = 'a['
RBRACK = ']'
LPAREN = '('
LPAREN2 = '(('
RPAREN = ')'
DOT = '.'
PIPE = '|'
COMMA = ','
COLON = ':'
AT = '@'
PLUS = '+'
MINUS = '-'
STAR = '*'
SLASH = '/'
MOD = '%'
BACKTICK = '`'
DOLLAR = '$'
TRUE = 'True'
FALSE = 'False'
NONE = 'None'
UNDERSCORE = '_'

WORDCHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"

if sys.platform == 'win32':
    NEWLINE = '\r\n'
elif os.name == 'mac':
    NEWLINE = '\r'
else:
    NEWLINE = '\n'

import copy

try:
    import encodings.utf_32
    has_utf32 = True
except:
    has_utf32 = False

try:
    from logging.handlers import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(NullHandler())


class ConfigInputStream(object):
    """
    An input stream which can read either ANSI files with default encoding
    or Unicode files with BOMs.

    Handles UTF-8, UTF-16LE, UTF-16BE. Could handle UTF-32 if Python had
    built-in support.
    """
    def __init__(self, stream):
        """
        Initialize an instance.

        @param stream: The underlying stream to be read. Should be seekable.
        @type stream: A stream (file-like object).
        """
        encoding = None
        signature = stream.read(4)
        used = -1
        if has_utf32:
            if signature == codecs.BOM_UTF32_LE:
                encoding = 'utf-32le'
            elif signature == codecs.BOM_UTF32_BE:
                encoding = 'utf-32be'
        if encoding is None:
            if signature[:3] == codecs.BOM_UTF8:
                used = 3
                encoding = 'utf-8'
            elif signature[:2] == codecs.BOM_UTF16_LE:
                used = 2
                encoding = 'utf-16le'
            elif signature[:2] == codecs.BOM_UTF16_BE:
                used = 2
                encoding = 'utf-16be'
            else:
                used = 0
        if used >= 0:
            stream.seek(used)
        if encoding:
            reader = codecs.getreader(encoding)
            stream = reader(stream)
        self.stream = stream
        self.encoding = encoding

    def read(self, size):
        if (size == 0) or (self.encoding is None):
            rv = self.stream.read(size)
        else:
            rv = ''
            while size > 0:
                rv += self.stream.read(1)
                size -= 1
        return rv

    def close(self):
        self.stream.close()

    def readline(self):
        if self.encoding is None:
            line = ''
        else:
            line = ''
        while True:
            c = self.stream.read(1)
            if c:
                line += c
            if c == '\n':
                break
        return line

class ConfigOutputStream(object):
    """
    An output stream which can write either ANSI files with default encoding
    or Unicode files with BOMs.

    Handles UTF-8, UTF-16LE, UTF-16BE. Could handle UTF-32 if Python had
    built-in support.
    """

    def __init__(self, stream, encoding=None):
        """
        Initialize an instance.

        @param stream: The underlying stream to be written.
        @type stream: A stream (file-like object).
        @param encoding: The desired encoding.
        @type encoding: str
        """
        if encoding is not None:
            encoding = str(encoding).lower()
        self.encoding = encoding
        if encoding == "utf-8":
            stream.write(codecs.BOM_UTF8)
        elif encoding == "utf-16be":
            stream.write(codecs.BOM_UTF16_BE)
        elif encoding == "utf-16le":
            stream.write(codecs.BOM_UTF16_LE)
        elif encoding == "utf-32be":
            stream.write(codecs.BOM_UTF32_BE)
        elif encoding == "utf-32le":
            stream.write(codecs.BOM_UTF32_LE)

        if encoding is not None:
            writer = codecs.getwriter(encoding)
            stream = writer(stream)
        self.stream = stream

    def write(self, data):
        self.stream.write(data)

    def flush(self):
        self.stream.flush()

    def close(self):
        self.stream.close()

def defaultStreamOpener(name):
    """
    This function returns a read-only stream, given its name. The name passed
    in should correspond to an existing stream, otherwise an exception will be
    raised.

    This is the default value of L{streamOpener}; assign your own callable to
    streamOpener to return streams based on names. For example, you could use
    urllib2.urlopen().

    @param name: The name of a stream, most commonly a file name.
    @type name: str
    @return: A stream with the specified name.
    @rtype: A read-only stream (file-like object)
    """
    return ConfigInputStream(file(name, 'rb'))

streamOpener = None

class ConfigError(Exception):
    """
    This is the base class of exceptions raised by this module.
    """
    pass

class ConfigFormatError(ConfigError):
    """
    This is the base class of exceptions raised due to syntax errors in
    configurations.
    """
    pass

class ConfigResolutionError(ConfigError):
    """
    This is the base class of exceptions raised due to semantic errors in
    configurations.
    """
    pass

def isWord(s):
    """
    See if a passed-in value is an identifier. If the value passed in is not a
    string, False is returned. An identifier consists of alphanumerics or
    underscore characters.

    Examples::

        isWord('a word') ->False
        isWord('award') -> True
        isWord(9) -> False
        isWord('a_b_c_') ->True

    @note: isWord('9abc') will return True - not exactly correct, but adequate
    for the way it's used here.

    @param s: The name to be tested
    @type s: any
    @return: True if a word, else False
    @rtype: bool
    """
    if type(s) != type(''):
        return False
    s = s.replace('_', '')
    return s.isalnum()

def makePath(prefix, suffix):
    """
    Make a path from a prefix and suffix.

    Examples::

        makePath('', 'suffix') -> 'suffix'
        makePath('prefix', 'suffix') -> 'prefix.suffix'
        makePath('prefix', '[1]') -> 'prefix[1]'

    @param prefix:  The prefix to use. If it evaluates as false, the suffix
                    is returned.
    @type prefix:   str
    @param suffix:  The suffix to use. It is either an identifier or an
                    index in brackets.
    @type suffix:   str
    @return:        The path concatenation of prefix and suffix, with a
                    dot if the suffix is not a bracketed index.
    @rtype:         str

    """
    if not prefix:
        rv = suffix
    elif suffix[0] == '[':
        rv = prefix + suffix
    else:
        rv = prefix + '.' + suffix
    return rv


class Container(object):
    """
    This internal class is the base class for mappings and sequences.

    @ivar path: A string which describes how to get
    to this instance from the root of the hierarchy.

    Example::

        a.list.of[1].or['more'].elements
    """
    def __init__(self, parent):
        """
        Initialize an instance.

        @param parent: The parent of this instance in the hierarchy.
        @type parent: A L{Container} instance.
        """
        object.__setattr__(self, 'parent', parent)
        object.__setattr__(self, 'path', '')

    def setPath(self, path):
        """
        Set the path for this instance.
        @param path: The path - a string which describes how to get
        to this instance from the root of the hierarchy.
        @type path: str
        """
        object.__setattr__(self, 'path', path)

    def evaluate(self, item):
        """
        Evaluate items which are instances of L{Reference} or L{Expression}.

        L{Reference} instances are evaluated using L{Reference.resolve},
        and L{Expression} instances are evaluated using
        L{Expression.evaluate}.

        @param item: The item to be evaluated.
        @type item: any
        @return: If the item is an instance of L{Reference} or L{Expression},
        the evaluated value is returned, otherwise the item is returned
        unchanged.
        """
        if isinstance(item, Reference):
            item = item.resolve(self)
        elif isinstance(item, Expression):
            item = item.evaluate(self)
        return item

    def writeToStream(self, stream, indent, container):
        """
        Write this instance to a stream at the specified indentation level.

        Should be redefined in subclasses.

        @param stream: The stream to write to
        @type stream: A writable stream (file-like object)
        @param indent: The indentation level
        @type indent: int
        @param container: The container of this instance
        @type container: L{Container}
        @raise NotImplementedError: If a subclass does not override this
        """
        raise NotImplementedError

    def writeValue(self, value, stream, indent):
        if isinstance(self, Mapping):
            indstr = ' '
        else:
            indstr = indent * '  '
        if isinstance(value, Reference) or isinstance(value, Expression):
            stream.write('%s%r%s' % (indstr, value, NEWLINE))
        else:
            if (type(value) is str): # and not isWord(value):
                value = repr(value)
            stream.write('%s%s%s' % (indstr, value, NEWLINE))

    def pathParts(self):
        """
        @return: our path, in str parts for either string keys, or numeric sequence keys as str.
        """
        return [_f for _f in re.split(r"[%s]+" % re.escape(".[]"), object.__getattribute__(self, 'path')) if _f]

    def instantiate(self, parent=None, key=None):
        """
        Copy this Container, resolving inheritance, but without resolving References.
        Adds the Container below the parent in a new brick_config tree.
        @param parent: new parent in the brick_config tree we are copying to
        @param key:    name (or index, for Sequence parent) of this Container
        @return: a copy of this Container in the new brick_config tree
        """
        # allow both Sequence and Mapping to be copied with this same code.
        if type(self) is Sequence:
            result = Sequence(parent)
        elif type(self) is Mapping:
            result = Mapping(parent)
        elif type(self) is Config:
            result = Config(parent=parent)
            result.reader = ConfigReader(result, self.reader.searchPath)
        else:
            raise AssertionError('instantiate() only supported on Sequence, Mapping and Config.')

        # resolve inheritance, without resolving References
        if 'extends' in list(self.keys()):
            if not isinstance(self['extends'], Container):
                raise AssertionError("Can only extend non-scalar types in %s - are you missing the dollar sign?" % self.path)
            kopi = self['extends'].instantiate(parent, key)
            result = kopi

        if parent is not None:
            result.setPath(makePath(parent.path, key))


        magicLoop = (type(self) is Sequence and key == 'parts')

        # in output of a magic loop Brick
        #magicOutput = type(self) is Mapping and key == 'output' and 'parts' in self.parent and type(self.parent.parts) is Sequence  # one level above

        haveParent = hasattr(self, 'parent') and object.__getattribute__(self, 'parent') is not None
        haveGrandparent = haveParent and hasattr(self.parent, 'parent') and object.__getattribute__(self.parent, 'parent') is not None

        # is our grandparent a magic loop Brick?
        magicLoopGrandparent = haveGrandparent and 'parts' in self.parent.parent and type(self.parent.parent.parts) is Sequence

        # are we one of the outputs of a magic loop Brick?
        magicLoopOutput = type(self) is Sequence and magicLoopGrandparent and self.pathParts()[-2] == 'output'

        # detect magic loop Brick's magic output syntax:
        # # output: { processedItems: [ $parts[$i].output.processed ] }
        magicOutput = magicLoopOutput and len(list(self.keys())) == 1 and type(self.data[0]) is Reference and self.data[0].isRecursive()

        # resolve magic loop for parts
        if magicLoop:
            # special case for magic loops using parts: [{ ... }] syntax
            assert(len(list(self.keys())) == 1)
            # parent.i is a Sequence of indices to be creating here
            copyKeys = [(0, ei) for ei in parent.i]
        elif magicOutput:
            # special case for magic loop Brick's output, which may use the following syntax:
            # output: { processedItems: [ $parts[$i].output.processed ] }
            # parent.parent.i is a Sequence of indices to be creating here
            copyKeys = [(0, ei) for ei in self.parent.parent.i]
        else:
            # the regular case: walk keys, and write one key each
            copyKeys = [(k, k) for k in list(self.keys())]


        # recursively copy the rest of our keys
        for (k, kTarget) in copyKeys:
            if k == 'extends':
                # inheritance handled above
                continue

            if type(self.data[k]) in [Reference, Expression]:
                kopi = copy.deepcopy(self.data[k])
                if magicOutput:
                    assert(type(self.data[k]) is Reference)
                    # resolve recursions using implicit $i inside a virtual output Mapping
                    outMapping = Mapping(parent)
                    outMapping.__setattr__('i', kTarget)
                    kopi = kopi.resolveRecursions(outMapping)
            elif type(self.data[k]) in [Mapping, Config, Sequence, LazyRange, LazySequence]:
                nextKey = '[%d]' % kTarget if type(result) is Sequence else kTarget
                kopi = self.data[k].instantiate(result, nextKey)
                if magicLoop:
                    # add implicit $i inside the single, looped part definition
                    kopi.__setattr__('i', kTarget)
            else:
                # hopefully only primitive types here
                kopi = copy.deepcopy(self.data[k])
            result.__setattr__(kTarget, kopi)

        return result


class Mapping(Container):
    """
    This internal class implements key-value mappings in configurations.
    """

    def __init__(self, parent=None):
        """
        Initialize an instance.

        @param parent: The parent of this instance in the hierarchy.
        @type parent: A L{Container} instance.
        """
        Container.__init__(self, parent)
        object.__setattr__(self, 'path', '')
        object.__setattr__(self, 'data', {})
        object.__setattr__(self, 'order', [])   # to preserve ordering
        object.__setattr__(self, 'comments', {})
        object.__setattr__(self, 'resolving', set())

    def __delitem__(self, key):
        """
        Remove an item
        """
        data = object.__getattribute__(self, 'data')
        if key not in data:
            raise AttributeError(key)
        order = object.__getattribute__(self, 'order')
        comments = object.__getattribute__(self, 'comments')
        del data[key]
        order.remove(key)
        del comments[key]

    def __getitem__(self, key):
        data = object.__getattribute__(self, 'data')
        if key not in data:
            raise AttributeError(key)
        rv = data[key]
        return self.evaluate(rv)

    __getattr__ = __getitem__

    def __getattribute__(self, name):
        if name == "__dict__":
            return {}
        if name in ["__methods__", "__members__"]:
            return []
        #if name == "__class__":
        #    return ''
        data = object.__getattribute__(self, "data")
        useData = name in data
        if useData:
            rv = getattr(data, name)
        else:
            rv = object.__getattribute__(self, name)
            if rv is None:
                raise AttributeError(name)
        return rv

    def iteritems(self):
        for key in list(self.keys()):
            yield(key, self[key])
        raise StopIteration

    def __contains__(self, item):
        order = object.__getattribute__(self, 'order')
        return item in order

    def addMapping(self, key, value, comment, setting=False):
        """
        Add a key-value mapping with a comment.

        @param key: The key for the mapping.
        @type key: str
        @param value: The value for the mapping.
        @type value: any
        @param comment: The comment for the key (can be None).
        @type comment: str
        @param setting: If True, ignore clashes. This is set
        to true when called from L{__setattr__}.
        @raise ConfigFormatError: If an existing key is seen
        again and setting is False.
        """
        data = object.__getattribute__(self, 'data')
        order = object.__getattribute__(self, 'order')
        comments = object.__getattribute__(self, 'comments')

        data[key] = value
        if key not in order:
            order.append(key)
        elif not setting:
            raise ConfigFormatError("repeated key: %s" % key)
        comments[key] = comment

    def __setattr__(self, name, value):
        self.addMapping(name, value, None, True)

    __setitem__ = __setattr__

    def keys(self):
        """
        Return the keys in a similar way to a dictionary.
        """
        return object.__getattribute__(self, 'order')

    def get(self, key, default=None):
        """
        Allows a dictionary-style get operation.
        """
        if key in self:
            return self[key]
        return default

    def __str__(self):
        return str(object.__getattribute__(self, 'data'))

    def __repr__(self):
        return repr(object.__getattribute__(self, 'data'))

    def __len__(self):
        return len(object.__getattribute__(self, 'order'))

    def __iter__(self):
        return iter(self.keys())

    def iterkeys(self):
        order = object.__getattribute__(self, 'order')
        return order.__iter__()

    def writeToStream(self, stream, indent, container):
        """
        Write this instance to a stream at the specified indentation level.

        Should be redefined in subclasses.

        @param stream: The stream to write to
        @type stream: A writable stream (file-like object)
        @param indent: The indentation level
        @type indent: int
        @param container: The container of this instance
        @type container: L{Container}
        """
        indstr = indent * '  '
        if len(self) == 0:
            stream.write(' { }%s' % NEWLINE)
        else:
            if isinstance(container, Mapping):
                stream.write(NEWLINE)
            stream.write('%s{%s' % (indstr, NEWLINE))
            self.save(stream, indent + 1)
            stream.write('%s}%s' % (indstr, NEWLINE))

    def save(self, stream, indent=0):
        """
        Save this configuration to the specified stream.
        @param stream: A stream to which the configuration is written.
        @type stream: A write-only stream (file-like object).
        @param indent: The indentation level for the output.
        @type indent: int
        """
        indstr = indent * '  '
        order = object.__getattribute__(self, 'order')
        data = object.__getattribute__(self, 'data')
        maxlen = 0 # max(map(lambda x: len(x), order))
        for key in order:
            comment = self.comments[key]
            if isWord(key):
                skey = key
            else:
                skey = repr(key)
            if comment:
                stream.write('%s#%s' % (indstr, comment))
            stream.write('%s%-*s :' % (indstr, maxlen, skey))
            value = data[key]
            if isinstance(value, Container):
                value.writeToStream(stream, indent, self)
            else:
                self.writeValue(value, stream, indent)


    def getByPath(self, path):
        """
        Obtain a value in the configuration via its path.
        @param path: The path of the required value
        @type path: str
        @return the value at the specified path.
        @rtype: any
        @raise ConfigError: If the path is invalid
        """
        s = 'self.' + path
        #sys.stderr.write('getByPath: %s\n' % s)
        try:
            return eval(s)
        except Exception as e:
            raise ConfigError(str(e))

class ConfigSearchPath(object):
    """
    Specify a search path for global brick_config file name references.
    """
    def __init__(self, folders):
        self.folders = folders

    def searchGlobalFile(self, fileName):
        """
        Attempts to find fileName in any of our folders, and
        returns the full path name on success.
        """
        for folder in self.folders:
            p = os.path.join(folder, fileName)
            if os.path.exists(p):
                return p
        raise IOError("No such file or directory: '%s' in ConfigSearchPath %s" % (fileName, str(self.folders)))

    def searchRelativeFile(self, fileName, parentFileName):
        path = os.path.join(os.path.dirname(parentFileName), fileName)
        if not os.path.exists(path):
            raise IOError("No such file or directory: '%s' in ConfigSearchPath from parent '%s'" % (fileName, parentFileName))
        return path


class Config(Mapping):
    """
    This class represents a configuration, and is the only one which clients
    need to interface to, under normal circumstances.
    """

    class Namespace(object):
        """
        This internal class is used for implementing default namespaces.

        An instance acts as a namespace.
        """
        def __init__(self):
            self.sys = sys
            self.os = os

        def __repr__(self):
            return "<Namespace('%s')>" % ','.join(list(self.__dict__.keys()))

    def __init__(self, streamOrFile=None, parent=None, searchPath=None):
        """
        Initializes an instance.

        @param streamOrFile: If specified, causes this instance to be loaded
        from the stream (by calling L{load}). If a string is provided, it is
        passed to L{streamOpener} to open a stream. Otherwise, the passed
        value is assumed to be a stream and used as is.
        @type streamOrFile: A readable stream (file-like object) or a name.
        @param parent: If specified, this becomes the parent of this instance
        in the configuration hierarchy.
        @type parent: a L{Container} instance.
        """
        #print("loading brick_config %s" % streamOrFile)
        Mapping.__init__(self, parent)
        object.__setattr__(self, 'reader', ConfigReader(self, searchPath))
        object.__setattr__(self, 'namespaces', [Config.Namespace()])
        object.__setattr__(self, 'resolving', set())
        if streamOrFile is not None:
            if isinstance(streamOrFile, str):
                global streamOpener
                if streamOpener is None:
                    streamOpener = defaultStreamOpener
                streamOrFile = streamOpener(streamOrFile)
            load = object.__getattribute__(self, "load")
            load(streamOrFile)

    def load(self, stream):
        """
        Load the configuration from the specified stream. Multiple streams can
        be used to populate the same instance, as long as there are no
        clashing keys. The stream is closed.
        @param stream: A stream from which the configuration is read.
        @type stream: A read-only stream (file-like object).
        @raise ConfigError: if keys in the loaded configuration clash with
        existing keys.
        @raise ConfigFormatError: if there is a syntax error in the stream.
        """
        reader = object.__getattribute__(self, 'reader')
        #object.__setattr__(self, 'root', reader.load(stream))
        reader.load(stream)
        stream.close()

    def addNamespace(self, ns, name=None):
        """
        Add a namespace to this configuration which can be used to evaluate
        (resolve) dotted-identifier expressions.
        @param ns: The namespace to be added.
        @type ns: A module or other namespace suitable for passing as an
        argument to vars().
        @param name: A name for the namespace, which, if specified, provides
        an additional level of indirection.
        @type name: str
        """
        namespaces = object.__getattribute__(self, 'namespaces')
        if name is None:
            namespaces.append(ns)
        else:
            setattr(namespaces[0], name, ns)

    def removeNamespace(self, ns, name=None):
        """
        Remove a namespace added with L{addNamespace}.
        @param ns: The namespace to be removed.
        @param name: The name which was specified when L{addNamespace} was
        called.
        @type name: str
        """
        namespaces = object.__getattribute__(self, 'namespaces')
        if name is None:
            namespaces.remove(ns)
        else:
            delattr(namespaces[0], name)

    def save(self, stream, indent=0):
        """
        Save this configuration to the specified stream. The stream is
        closed if this is the top-level configuration in the hierarchy.
        L{Mapping.save} is called to do all the work.
        @param stream: A stream to which the configuration is written.
        @type stream: A write-only stream (file-like object).
        @param indent: The indentation level for the output.
        @type indent: int
        """
        Mapping.save(self, stream, indent)
        if indent == 0:
            stream.close()

    def getByPath(self, path):
        """
        Obtain a value in the configuration via its path.
        @param path: The path of the required value
        @type path: str
        @return the value at the specified path.
        @rtype: any
        @raise ConfigError: If the path is invalid
        """
        s = 'self.' + path
        try:
            return eval(s)
        except Exception as e:
            raise ConfigError(str(e))


class Sequence(Container):
    """
    This internal class implements a value which is a sequence of other values.
    """
    class SeqIter(object):
        """
        This internal class implements an iterator for a L{Sequence} instance.
        """
        def __init__(self, seq):
            self.seq = seq
            self.limit = len(object.__getattribute__(seq, 'data'))
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.index >= self.limit:
                raise StopIteration
            rv = self.seq[self.index]
            self.index += 1
            return rv

    def __init__(self, parent=None):
        """
        Initialize an instance.

        @param parent: The parent of this instance in the hierarchy.
        @type parent: A L{Container} instance.
        """
        Container.__init__(self, parent)
        object.__setattr__(self, 'data', [])
        object.__setattr__(self, 'comments', [])

    def append(self, item, comment):
        """
        Add an item to the sequence.

        @param item: The item to add.
        @type item: any
        @param comment: A comment for the item.
        @type comment: str
        """
        data = object.__getattribute__(self, 'data')
        comments = object.__getattribute__(self, 'comments')
        data.append(item)
        comments.append(comment)

    def evaluate(self, item):
        """
        Overrides Container.evaluate() to prevent attempting to resolve
        references directly inside a Sequence.
        """
        # resolve within parent instead of self
        if isinstance(item, Reference):
            item = item.resolve(self.parent)
        elif isinstance(item, Expression):
            item = item.evaluate(self.parent)
        return item

    def keys(self):
        """
        Return the keys. Compatibility with Mapping.
        """
        return list(range(len(self.data)))

    def __setattr__(self, idx, value):
        """
        Adds a value to the Sequence. Compatibility with Mapping.
        """
        assert(idx == len(self.data))
        self.append(value, '')

    def __getitem__(self, index):
        data = object.__getattribute__(self, 'data')

        # extra non-numeric key: length
        if index == 'length':
            return len(self.data)

        try:
            rv = data[index]
        except (IndexError, KeyError, TypeError):
            raise ConfigResolutionError('%r is not a valid index for %r' % (index, object.__getattribute__(self, 'path')))
        if not isinstance(rv, list):
            rv = self.evaluate(rv)
        else:
            # deal with a slice
            result = []
            for a in rv:
                result.append(self.evaluate(a))
            rv = result
        return rv

    def __iter__(self):
        return Sequence.SeqIter(self)

    def __repr__(self):
        return repr(object.__getattribute__(self, 'data'))

    def __str__(self):
        return str(self[:]) # using the slice evaluates the contents

    def __len__(self):
        return len(object.__getattribute__(self, 'data'))

    def writeToStream(self, stream, indent, container):
        """
        Write this instance to a stream at the specified indentation level.

        Should be redefined in subclasses.

        @param stream: The stream to write to
        @type stream: A writable stream (file-like object)
        @param indent: The indentation level
        @type indent: int
        @param container: The container of this instance
        @type container: L{Container}
        """
        indstr = indent * '  '
        if len(self) == 0:
            stream.write(' [ ]%s' % NEWLINE)
        else:
            if isinstance(container, Mapping):
                stream.write(NEWLINE)
            stream.write('%s[%s' % (indstr, NEWLINE))
            self.save(stream, indent + 1)
            stream.write('%s]%s' % (indstr, NEWLINE))

    def save(self, stream, indent):
        """
        Save this instance to the specified stream.
        @param stream: A stream to which the configuration is written.
        @type stream: A write-only stream (file-like object).
        @param indent: The indentation level for the output, > 0
        @type indent: int
        """
        if indent == 0:
            raise ConfigError("sequence cannot be saved as a top-level item")
        data = object.__getattribute__(self, 'data')
        comments = object.__getattribute__(self, 'comments')
        indstr = indent * '  '
        for i in range(0, len(data)):
            value = data[i]
            comment = comments[i]
            if comment:
                stream.write('%s#%s' % (indstr, comment))
            if isinstance(value, Container):
                value.writeToStream(stream, indent, self)
            else:
                self.writeValue(value, stream, indent)


class LazySequence(Sequence):
    """
    A crossing between Reference and Sequence, this is a Sequence class that
    has a length that is not determined at parse time.
    """
    def __init__(self, dataItem, mapping, parent=None):
        """
        Initialize an instance.

        @param parent: The parent of this instance in the hierarchy.
        @type parent: A L{Container} instance.

        @param mapping: a Mapping containing a key: [range] specification
        """
        Container.__init__(self, parent)
        # data and comments hold the single loop item (as opposed to regular Sequence, which has lists)
        object.__setattr__(self, 'dataItem', dataItem)
        object.__setattr__(self, 'mapping', mapping)

        # lists that will be set by determine()
        # DO NOT define 'data' here.
        #object.__setattr__(self, 'data', [])
        #object.__setattr__(self, 'comments', [])

    def instantiate(self, parent=None, key=None):
        result = LazySequence(None, None, parent)

        dataItem = self.dataItem
        #if type(dataItem) in [Reference, Expression]:
        #    dataItem = copy.deepcopy(dataItem)
        if type(dataItem) in [Mapping, Config, Sequence, LazyRange, LazySequence]:
            dataItem = dataItem.instantiate(result, 0)  # key name is hardcoded 0 here, instead of true list index. That should not matter.
            # (do paths get messed up? any path users?)
            # could we pass a sentinel instead of the 0 here, to see where it propagates to?
        else:
            dataItem = copy.deepcopy(dataItem)

        mapping = self.mapping.instantiate(parent, 'mapping')  # key name is not the original one here ('i' usually), but that should not matter.
        object.__setattr__(result, 'dataItem', dataItem)
        object.__setattr__(result, 'mapping', mapping)
        object.__setattr__(result, 'path', makePath(parent.path, key))
        return result

    def __repr__(self):
        return 'LazySequence(%r, mapping=%r)' % (self.dataItem, self.mapping)

    def __iter__(self):
        if not hasattr(self, 'data'):
            self.determine()
        return Sequence.SeqIter(self)

    def __getitem__(self, index):
        if not hasattr(self, 'data'):
            self.determine()
        # the rest is business as usual
        return Sequence.__getitem__(self, index)

    def __getattr__(self, index):
        if not hasattr(self, 'data'):
            self.determine()
        # the rest is business as usual
        return Sequence.__getattribute__(self, index)

    def determine(self):
        """Determine the actual Sequence."""
        specification = object.__getattribute__(self, 'mapping')
        listExpression = object.__getattribute__(self, 'dataItem')

        assert(len(list(specification.keys())) == 1)
        key = list(specification.keys())[0]

        # build the range
        object.__setattr__(self, 'data', [])
        object.__setattr__(self, 'comments', [])
        for i, val in enumerate(specification[key]):
            # create context to evaluate the loop key reference $i
            context = Mapping(self.parent)
            context.setPath(self.path)
            context[key] = val

            if type(listExpression) in [Expression, Reference]:
                # untested
                resolved = listExpression.resolveRecursions(context)
            elif type(listExpression) in [Mapping, Config, Sequence, LazyRange, LazySequence]:
                # really, parent should be 'self', not 'context', but then we need to set the key here.

                #print('listExpression.instantiate(context, %d, %s=%r)' % (i, key, val))
                resolved = listExpression.instantiate(context, '[%d]' % i)
                #print('%r' % resolved)

                #resolved = listExpression.instantiate(self, '[%d]' % i)
                #resolved[key] = val
            else:
                # deepcopy??
                resolved = listExpression
            self.append(resolved, '')

        return object.__getattribute__(self, 'data')


class LazyRange(Sequence):
    """
    A lazy range (Sequence of numbers) with a length that is not determined
    at parse time.
    """
    def __init__(self, rangeLimits, parent=None):
        Container.__init__(self, parent)
        object.__setattr__(self, 'rangeLimits', rangeLimits)

        # lists that will be set by determine()
        # DO NOT define 'data' here.
        #object.__setattr__(self, 'data', [])
        #object.__setattr__(self, 'comments', [])

    def instantiate(self, parent=None, key=None):
        result = LazyRange(self.rangeLimits.instantiate(self, 'rangeLimits'), parent)  # key name is not the original one here ('i' usually), but that should not matter.
        object.__setattr__(result, 'path', makePath(parent.path, key))
        return result

    def __repr__(self):
        return 'LazyRange(%r)' % self.rangeLimits

    def __iter__(self):
        if not hasattr(self, 'data'):
            self.determine()
        return Sequence.SeqIter(self)

    def __getitem__(self, index):
        # data attribute is defined dynamically
        if not hasattr(self, 'data'):
            self.determine()
        # the rest is business as usual
        return Sequence.__getitem__(self, index)

    def determine(self):
        """Determine the actual Sequence."""

        rangeLimits = object.__getattribute__(self, 'rangeLimits')

        # why are literal ints parsed into float?
        begin = int(rangeLimits.data[0])
        end = rangeLimits.data[1]

        # The range end may be an Expression or Reference.
        if type(end) is Expression:
            end = end.evaluate(self.parent)
        elif type(end) is Reference:
            end = end.resolve(self.parent)
        else:
            end = int(end)

        # build the range
        object.__setattr__(self, 'data', [])
        object.__setattr__(self, 'comments', [])
        for i in range(begin, end + 1):
            self.append(i, '')

        return object.__getattribute__(self, 'data')


class Reference(object):
    """
    This internal class implements a value which is a reference to another value.
    """
    def __init__(self, type, ident):
        """
        Initialize an instance.

        @param type: The type of reference.
        @type type: BACKTICK or DOLLAR
        @param ident: The identifier which starts the reference.
        @type ident: str
        """
        self.type = type
        self.elements = [ident]
        object.__setattr__(self, 'path', '')  # TODO: path vs. path() name clash

    def __deepcopy__(self, memo=None):
        result = Reference(self.type, self.elements[0])
        if memo is not None:
            memo[id(self)] = result
        object.__setattr__(result, 'path', self.path)
        result.elements = copy.deepcopy(self.elements, memo)
        return result

    def pathParts(self):
        """
        @return: our path, in str parts for either string keys, or numeric sequence keys as str.
        """
        return [_f for _f in re.split(r"[%s]+" % re.escape(".[]"), object.__getattribute__(self, 'path')) if _f]

    def resolveRecursions(self, container):
        """
        Copy this Reference, and resolve its internal recursions to make it
        a plain Reference.
        """
        # copy
        result = Reference(self.type, self.elements[0])
        object.__setattr__(result, 'path', self.path)
        elements = copy.deepcopy(self.elements)
        # resolve recursions
        newElements = elements[0:1]
        for (t, e) in elements[1:]:
            if t == DOLLAR:
                e = e.resolve(container)
                # we assume that this has been an index, of the $i sort:
                # $parts[$i].output.processed
                t = LBRACK if type(e) in [int, float] else DOT
            newElements.append((t, e))
        result.elements = newElements
        return result

    def addElement(self, type, ident):
        """
        Add an element to the reference.

        @param type: The type of reference.
        @type type: BACKTICK or DOLLAR
        @param ident: The identifier which continues the reference.
        @type ident: str
        """
        self.elements.append((type, ident))

    def findConfig(self, container):
        """
        Find the closest enclosing configuration to the specified container.

        @param container: The container to start from.
        @type container: L{Container}
        @return: The closest enclosing configuration.
        @rtype: L{Config}
        """
        # find parent *Brick* instead of parent Config
        # TODO: inheritance. this is not a very nice way of testing for a Brick...
        # we need to stop at root (Config) as well as at a Brick
        while (container is not None) and not \
                ((isinstance(container, Mapping) and (('input' in container and 'output' in container) or 'extends' in container)) \
                or isinstance(container, Config)) \
            :
            container = object.__getattribute__(container, 'parent')

        assert container is not None, "findConfig() failed for Reference %s in container %s" % (str(self), container.path)
        return container

    def isRecursive(self):
        """
        @return: True if this Reference contains a Reference index, e.g.
        $parts[$i].output.processed
        """
        return (DOLLAR in zip(*self.elements[1:])[0])

    def resolve(self, container):
        logger.debug("resolve() of reference object = %s -> %s in container = %s", str(self.path), str(self.elements2path(self.elements)), str(container.path))
        return self.resolve2(container)[0]

    def relativeElements(self, container):
        """
        Resolve the relative path of this reference, relative to
        the given container. Attempts to resolve this reference in
        the container or any of its nodes, and returns the successful
        relative path.
        returns e.g. ['_', ('.', '_'), ('.', 'input'), ('.', 'src'), ('[', 0)]
        """
        rv, nup = self.resolve2(container, resolveRefs=False)
        result = []
        result += ['_'] if nup > 0 else []
        result += [('.', '_')] * (nup - 1)
        result += [('.', self.elements[0])] if nup > 0 else [self.elements[0]]

        # e.g. ['_', ('.', '_'), ('.', '_'), ('.', 'input'), ('.', 'corpora'), ('$', $i)]
        # e.g. ['seq', ('[', 2)] for $seq[2]

        # resolve nested references (e.g. $var[$i])
        for r in self.elements[1:]:
            if r[0] == DOLLAR:
                r = (DOLLAR, r[1].resolve(container))
            result.append(r)

        return result

    def elements2path(self, elements):
        """
        Turn an elements list  ['_', ('.', '_'), ('.', 'input'), ('.', 'src'), ('[', 0)]
        to a path ['_', '_', 'input', 'src', '0']
        """
        result = list(elements[0:1])
        result += [str(e[1]) for e in elements[1:]]
        return result

    def relativePath(self, container):
        """
        Relative path from container.path to self.elements, i.e. where
        this Reference is pointing to.
        Returns a path like ['_', '_', 'input', 'src', '0']
        """

        # this is not always true because of inheritance.
        #assert self.pathParts()[:-1] == container.pathParts(), "my hypothesis"
        #
        # e.g. the WordAligner defined in Giza.cfg, extended in mini.cfg
        # within Experiment.parts.WordAligner0 has:
        #
        # self.pathParts()[:-1] == ['WordAligner', 'output']
        # container.pathParts() == ['Experiment', 'parts', 'WordAligner0', 'output']
        #
        # TODO: I think this is a bug that needs fixing.

        return self.elements2path(self.relativeElements(container))

    def resolve2(self, container, resolveRefs=True):
        """
        Resolve this instance in the context of a container.

        @param container: The container to resolve from.
        @type container: L{Container}
        @return: The resolved value, nup: number of ancestors to walk up
        @rtype: any
        @raise ConfigResolutionError: If resolution fails.
        """
        rv = None
        nup = 0
        path = object.__getattribute__(container, 'path')
        #current = self.findConfig(container)
        #parentConfig = self.findConfig(container)
        parentConfig = None
        current = container
        elements = list(self.elements)
        while current is not None:
            if elements[0] == UNDERSCORE:
                #logger.debug("Walking up")
                # walk up to parent container
                current = object.__getattribute__(current, 'parent')
                # remove '_', ('_', '.') from the front
                #logger.debug("BEFORE Elements: %s, self.elements: %s", str(elements), str(self.elements))
                elements = elements[1:]

                assert(type(elements[0]) is tuple)
                # replace the first word, which is not a tuple (why though?)
                elements[0] = elements[0][1]

                #logger.debug("Elements: %s, self.elements: %s", str(elements), str(self.elements))
                continue

            if self.type == BACKTICK:
                namespaces = object.__getattribute__(current, 'namespaces')
                found = False
                s = str(self)[1:-1]
                for ns in namespaces:
                    try:
                        try:
                            rv = eval(s, vars(ns))
                        except TypeError: #Python 2.7 - vars is a dictproxy
                            rv = eval(s, {}, vars(ns))
                        found = True
                        break
                    except:
                        logger.debug("unable to resolve %r in %r", s, ns)
                        pass
                if found:
                    break
            else:
                if parentConfig is None:
                    # find container from the level indicated by _._ -> start in the right container
                    parentConfig = self.findConfig(current)

                firstkey = elements[0]
                try:
                    parentConfig.resolving
                except AttributeError:
                    self.findConfig(container)
                if firstkey in parentConfig.resolving:
                    parentConfig.resolving.remove(firstkey)
                    raise ConfigResolutionError("Circular reference: %r" % firstkey)
                parentConfig.resolving.add(firstkey)
                key = firstkey
                try:
                    logger.debug("Trying to resolve key = %s on current = %s in container = %s", str(key), str(current.path), str(container.path))
                    if type(key) is str and isinstance(current, Sequence):
                        # avoid attempting to resolve str keys on Sequence
                        # this would yield ConfigResolutionError from Sequence.__getitem__
                        rv = None
                        raise AttributeError(key)
                    rv = current[key] if resolveRefs else current.data[key]
                    for item in elements[1:]:
                        key = item[1]
                        if type(key) is Reference:
                            # recursive key resolution support (enables us to use references in indices, like configKey: $Part.definition[$i])
                            # TODO: this assert() does not work as it is caught below.
                            #assert(resolveRefs==True)
                            key = key.resolve2(container, resolveRefs)[0]
                        #rv = rv[key] if resolveRefs else rv.data[key]
                        if resolveRefs:
                            rv = rv[key]
                        elif type(rv) is Reference:
                            # did not ask to resolve Reference to Reference...
                            # this case happens if you ask to resolve2() a Sequence item Reference on a Reference
                            # e.g. ref: $array[0], array: $other, other: [1,2,3]
                            rv = None
                        else:
                            rv = rv.data[key]
                    parentConfig.resolving.remove(firstkey)
                    break
                except ConfigResolutionError:
                    raise
                except:
                    # TODO: explicitly specify the errors that can occur here.
                    logger.debug("Unable to resolve %r: %s", key, sys.exc_info()[1])
                    rv = None
                    pass
                parentConfig.resolving.discard(firstkey)
            # check parent container
            current = object.__getattribute__(current, 'parent')
            nup += 1
        if current is None:
            raise ConfigResolutionError("unable to evaluate %r in the configuration %s" % (self, path))
        return rv, nup

    def __str__(self):
        s = self.elements[0]
        for tt, tv in self.elements[1:]:
            if tt == DOT:
                s += '.%s' % tv
            else:
                s += '[%r]' % tv
        if self.type == BACKTICK:
            return BACKTICK + s + BACKTICK
        else:
            return DOLLAR + s

    def __repr__(self):
        return self.__str__()

class Expression(object):
    """
    This internal class implements a value which is obtained by evaluating an expression.
    """
    def __init__(self, op, lhs, rhs=None):
        """
        Initialize an instance.

        @param op: the operation expressed in the expression.
        @type op: PLUS, MINUS, STAR, SLASH, MOD
        @param lhs: the left-hand-side operand of the expression.
        @type lhs: any Expression or primary value.
        @param rhs: the right-hand-side operand of the expression.
        @type rhs: any Expression or primary value.
        """
        self.op = op
        self.lhs = lhs
        self.rhs = rhs
        object.__setattr__(self, 'path', '')

    def __str__(self):
        return '%r %s %r' % (self.lhs, self.op, self.rhs)

    def __repr__(self):
        return self.__str__()

    def __deepcopy__(self, memo=None):
        result = Expression(self.op, copy.deepcopy(self.lhs), copy.deepcopy(self.rhs))
        object.__setattr__(result, 'path', self.path)
        if memo is not None:
            memo[id(self)] = result
        return result

    def _internalResolveRecursions(self, container):
        lhs = self.lhs
        if isinstance(lhs, Reference):
            self.lhs = lhs.resolveRecursions(container)
        elif isinstance(lhs, Expression):
            lhs._internalResolveRecursions(container)
        rhs = self.rhs
        if isinstance(rhs, Reference):
            self.rhs = rhs.resolveRecursions(container)
        elif isinstance(rhs, Expression):
            rhs._internalResolveRecursions(container)

    def resolveRecursions(self, container):
        """
        Copy this Expression, and resolve its internal Reference recursions to make it
        use plain References.
        """
        # copy
        result = copy.deepcopy(self)
        # resolve recursions
        result._internalResolveRecursions(container)
        return result

    def evaluate(self, container):
        """
        Evaluate this instance in the context of a container.

        @param container: The container to evaluate in from.
        @type container: L{Container}
        @return: The evaluated value.
        @rtype: any
        @raise ConfigResolutionError: If evaluation fails.
        @raise ZeroDivideError: If division by zero occurs.
        @raise TypeError: If the operation is invalid, e.g.
        subtracting one string from another.
        """
        lhs = self.lhs
        if isinstance(lhs, Reference):
            lhs = lhs.resolve(container)
        elif isinstance(lhs, Expression):
            lhs = lhs.evaluate(container)
        rhs = self.rhs
        if isinstance(rhs, Reference):
            rhs = rhs.resolve(container)
        elif isinstance(rhs, Expression):
            rhs = rhs.evaluate(container)
        op = self.op
        if op == PLUS:
            rv = lhs + rhs
        elif op == MINUS:
            rv = lhs - rhs
        elif op == STAR:
            rv = lhs * rhs
        elif op == SLASH:
            rv = lhs / rhs
        elif op == MOD:
            rv = lhs % rhs
        elif hasattr(op, '__call__'):
            if rhs is None:
                rv = op(lhs)
            else:
                rv = op(lhs, rhs)
        else:
            raise ValueError("Invalid operator %r in Expression %s" % (op, object.__getattribute__(self, 'path')))
        return rv

class ConfigReader(object):
    """
    This internal class implements a parser for configurations.
    """

    def __init__(self, config, searchPath=None):
        self.filename = None
        self.config = config
        self.lineno = 0
        self.colno = 0
        self.lastc = None
        self.last_token = None
        self.commentchars = '#'
        self.whitespace = ' \t\r\n'
        self.quotes = '\'"<>'
        self.punct = ':-+*/%,.{}[]()@`$|'
        self.digits = '0123456789'
        self.wordchars = '%s' % WORDCHARS # make a copy
        self.identchars = self.wordchars + self.digits
        self.pbchars = []
        self.pbtokens = []
        self.comment = None
        self.searchPath = searchPath if searchPath is not None else ConfigSearchPath([])

    def location(self):
        """
        Return the current location (filename, line, column) in the stream
        as a string.

        Used when printing error messages,

        @return: A string representing a location in the stream being read.
        @rtype: str
        """
        return "%s(%d,%d)" % (self.filename, self.lineno, self.colno)

    def getChar(self):
        """
        Get the next char from the stream. Update line and column numbers
        appropriately.

        @return: The next character from the stream.
        @rtype: str
        """
        if self.pbchars:
            c = self.pbchars.pop()
        else:
            c = self.stream.read(1)
            self.colno += 1
            if c == '\n':
                self.lineno += 1
                self.colno = 1
        return c

    def __repr__(self):
        return "<ConfigReader at 0x%08x>" % id(self)

    __str__ = __repr__

    def getToken(self):
        """
        Get a token from the stream. String values are returned in a form
        where you need to eval() the returned value to get the actual
        string. The return value is (token_type, token_value).

        Multiline string tokenizing is thanks to David Janes (BlogMatrix)

        @return: The next token.
        @rtype: A token tuple.
        """
        if self.pbtokens:
            return self.pbtokens.pop()
        stream = self.stream
        self.comment = None
        token = ''
        tt = EOF
        while True:
            c = self.getChar()
            if not c:
                break
            elif c == '#':
                self.comment = stream.readline()
                self.lineno += 1
                continue
            if c in self.quotes:
                token = c
                quote = c if c != '<' else '>'
                tt = STRING
                escaped = False
                multiline = False
                c1 = self.getChar()
                if c1 == quote:
                    c2 = self.getChar()
                    if c2 == quote:
                        multiline = True
                        token += quote
                        token += quote
                    else:
                        self.pbchars.append(c2)
                        self.pbchars.append(c1)
                else:
                    self.pbchars.append(c1)
                while True:
                    c = self.getChar()
                    if not c:
                        break
                    token += c
                    if (c == quote) and not escaped:
                        if not multiline or (len(token) >= 6 and token.endswith(token[:3]) and token[-4] != '\\'):
                            break
                    if c == '\\':
                        escaped = not escaped
                    else:
                        escaped = False
                if not c:
                    raise ConfigFormatError('%s: Unterminated quoted string: %r, %r' % (self.location(), token, c))
                break
            if c in self.whitespace:
                self.lastc = c
                continue
            elif c in self.punct:
                token = c
                tt = c
                if (self.lastc == ']') or (self.lastc in self.identchars):
                    if c == '[':
                        tt = LBRACK2
                    elif c == '(':
                        tt = LPAREN2
                break
            elif c in self.digits:
                token = c
                tt = NUMBER
                in_exponent=False
                while True:
                    c = self.getChar()
                    if not c:
                        break
                    if c in self.digits:
                        token += c
                    elif (c == '.') and token.find('.') < 0 and not in_exponent:
                        token += c
                    elif (c == '-') and token.find('-') < 0 and in_exponent:
                        token += c
                    elif (c in 'eE') and token.find('e') < 0 and\
                         token.find('E') < 0:
                        token += c
                        in_exponent = True
                    else:
                        if c and (c not in self.whitespace):
                            self.pbchars.append(c)
                        break
                break
            elif c in self.wordchars:
                token = c
                tt = WORD
                c = self.getChar()
                while c and (c in self.identchars):
                    token += c
                    c = self.getChar()
                if c: # and c not in self.whitespace:
                    self.pbchars.append(c)
                if token == "True":
                    tt = TRUE
                elif token == "False":
                    tt = FALSE
                elif token == "None":
                    tt = NONE
                break
            else:
                raise ConfigFormatError('%s: Unexpected character: %r' % (self.location(), c))
        if token:
            self.lastc = token[-1]
        else:
            self.lastc = None
        self.last_token = tt
        return (tt, token)

    def load(self, stream, parent=None, suffix=None):
        """
        Load the configuration from the specified stream.

        @param stream: A stream from which to load the configuration.
        @type stream: A stream (file-like object).
        @param parent: The parent of the configuration (to which this reader
        belongs) in the hierarchy. Specified when the configuration is
        included in another one.
        @type parent: A L{Container} instance.
        @param suffix: The suffix of this configuration in the parent
        configuration. Should be specified whenever the parent is not None.
        @raise ConfigError: If parent is specified but suffix is not.
        @raise ConfigFormatError: If there are syntax errors in the stream.
        """
        if parent is not None:
            if suffix is None:
                raise ConfigError("internal error: load called with parent but no suffix")
            self.config.setPath(makePath(object.__getattribute__(parent, 'path'), suffix))
        self.setStream(stream)
        self.token = self.getToken()
        self.parseMappingBody(self.config)
        if self.token[0] != EOF:
            raise ConfigFormatError('%s: expecting EOF, found %r' % (self.location(), self.token[1]))

    def setStream(self, stream):
        """
        Set the stream to the specified value, and prepare to read from it.

        @param stream: A stream from which to load the configuration.
        @type stream: A stream (file-like object).
        """
        self.stream = stream
        if hasattr(stream, 'name'):
            filename = stream.name
        else:
            filename = '?'
        self.filename = filename
        self.lineno = 1
        self.colno = 1

    def match(self, t):
        """
        Ensure that the current token type matches the specified value, and
        advance to the next token.

        @param t: The token type to match.
        @type t: A valid token type.
        @return: The token which was last read from the stream before this
        function is called.
        @rtype: a token tuple - see L{getToken}.
        @raise ConfigFormatError: If the token does not match what's expected.
        """
        if self.token[0] != t:
            raise ConfigFormatError("%s: expecting %s, found %r" % (self.location(), t, self.token[1]))
        rv = self.token
        self.token = self.getToken()
        return rv

    def parseMappingBody(self, current):
        """
        Parse the internals of a mapping, and add entries to the provided
        L{Mapping}.

        @param current: The mapping to add entries to.
        @type current: A L{Mapping} instance.
        """
        while self.token[0] in [WORD, STRING]:
            self.parseKeyValuePair(current)

    def parseKeyValuePair(self, parent, allowRbrack=False):
        """
        Parse a key-value pair, and add it to the provided L{Mapping}.

        @param parent: The mapping to add entries to.
        @type parent: A L{Mapping} instance.
        @raise ConfigFormatError: if a syntax error is found.
        """
        comment = self.comment
        tt, tv = self.token
        if tt == WORD:
            key = tv
            suffix = tv
        elif tt == STRING:
            key = eval(tv)
            suffix = '[%s]' % tv
        else:
            msg = "%s: expecting word or string, found %r"
            raise ConfigFormatError(msg % (self.location(), tv))
        self.token = self.getToken()
        # for now, we allow key on its own as a short form of key : True
        if self.token[0] == COLON:
            self.token = self.getToken()
            value = self.parseValue(parent, suffix)
        else:
            value = True
        try:
            parent.addMapping(key, value, comment)
        except Exception as e:
            raise ConfigFormatError("%s: %s, %r" % (self.location(), e,
                                    self.token[1]))
        tt = self.token[0]
        allow = [EOF, WORD, STRING, RCURLY, COMMA] + ([RBRACK] if allowRbrack else [])
        if tt not in allow:
            msg = "%s: expecting one of EOF, WORD, STRING,\
RCURLY, COMMA, [RBRACK] found %r"
            raise ConfigFormatError(msg  % (self.location(), self.token[1]))
        if tt == COMMA:
            self.token = self.getToken()

    def parseValue(self, parent, suffix):
        """
        Parse a value.

        @param parent: The container to which the value will be added.
        @type parent: A L{Container} instance.
        @param suffix: The suffix for the value.
        @type suffix: str
        @return: The value
        @rtype: any
        @raise ConfigFormatError: if a syntax error is found.
        """
        tt = self.token[0]
        if tt in [STRING, WORD, NUMBER, LPAREN, DOLLAR,
                  TRUE, FALSE, NONE, BACKTICK, MINUS]:
            rv = self.parseScalar()
            if type(rv) in [Reference, Expression]:
                parentPath = object.__getattribute__(parent, 'path')
                object.__setattr__(rv, 'path', makePath(parentPath, suffix))
        elif tt == LBRACK:
            rv = self.parseSequence(parent, suffix)
        elif tt in [LCURLY, AT]:
            rv = self.parseMapping(parent, suffix)
        else:
            raise ConfigFormatError("%s: unexpected input: %r" %
               (self.location(), self.token[1]))
        return rv

    def parseSequence(self, parent, suffix):
        """
        Parse a sequence.

        @param parent: The container to which the sequence will be added.
        @type parent: A L{Container} instance.
        @param suffix: The suffix for the value.
        @type suffix: str
        @return: a L{Sequence} instance representing the sequence.
        @rtype: L{Sequence}
        @raise ConfigFormatError: if a syntax error is found.
        """
        rv = Sequence(parent)
        rv.setPath(makePath(object.__getattribute__(parent, 'path'), suffix))
        self.match(LBRACK)
        comment = self.comment
        tt = self.token[0]
        while tt in [STRING, WORD, NUMBER, LCURLY, LBRACK, LPAREN, DOLLAR,
                     TRUE, FALSE, NONE, BACKTICK, MINUS]:
            lsuffix = '[%d]' % len(rv)
            value = self.parseValue(rv, lsuffix)
            rv.append(value, comment)
            tt = self.token[0]
            comment = self.comment
            if tt == COMMA:
                self.match(COMMA)
                tt = self.token[0]
                comment = self.comment
                continue

        # parse range syntax, e.g. [1..3] -> [1,2,3]
        specification = Mapping(parent)

        if self.parseRange(rv, specification, parent, suffix):
            rv = LazyRange(specification['rangeLimits'], parent)
            rv.setPath(makePath(object.__getattribute__(parent, 'path'), suffix))
            return rv
        elif self.parseListComprehension(rv, specification, parent, suffix):
            self.match(RBRACK)
            rv = LazySequence(rv.data[0], specification, parent)
            rv.setPath(makePath(object.__getattribute__(parent, 'path'), suffix))
            # TODO: DRY. is this possible below?
            return rv
        else:
            self.match(RBRACK)
            return rv

    def parseListComprehension(self, rv, specification, parent, suffix):
        """
        Quick hack to add [$elems[$i] | i: [0..1]] style ranges which are expanded to a Sequence [$elems[0], $elems[1]]
        This only works with References, since there is no straightforward, intuitive way to partially evaluate an Expression
        @return True if a list comprehension has been found. We should always match an RBRACK afterwards.
        """
        # check for list comprehension syntax
        #  and (type(rv.data[0]) in [Expression, Reference])
        if not (len(rv.data) == 1 and self.token[0] == PIPE):
            return False

        self.match(PIPE)

        # parse the key: [range] specification
        self.parseKeyValuePair(specification, allowRbrack=True)

        return True

    def parseRange(self, rv, specification, parent, suffix):
        """
        Quick hack to add [1..3] style ranges which are expanded to a Sequence [1,2,3]
        @return True if a range has been found, False if we should match an RBRACK.
        """
        # check for range syntax, e.g. [1..3] -> [1,2,3]
        # why are literal ints parsed into float?
        if not (len(rv.data) == 1 and (type(rv.data[0]) in [int, float]) and self.token[0] == DOT):
            return False

        self.token = (LBRACK, LBRACK) # fake begin range
        # parse the range end (for now, as Sequence...)
        end = self.parseSequence(parent, suffix)

        rangeLimits = Sequence(parent)
        rangeLimits.append(rv.data[0], '')
        rangeLimits.append(end.data[0], '')
        # add dummy key 'rangeLimits'
        specification.addMapping('rangeLimits', rangeLimits, '')

        if len(end.data) != 1:
            raise ConfigFormatError("%s: expecting single number for end of range" % (self.location()))

        return True

    def parseMapping(self, parent, suffix):
        """
        Parse a mapping.

        @param parent: The container to which the mapping will be added.
        @type parent: A L{Container} instance.
        @param suffix: The suffix for the value.
        @type suffix: str
        @return: a L{Mapping} instance representing the mapping.
        @rtype: L{Mapping}
        @raise ConfigFormatError: if a syntax error is found.
        """
        if self.token[0] == LCURLY:
            self.match(LCURLY)
            rv = Mapping(parent)
            rv.setPath(
               makePath(object.__getattribute__(parent, 'path'), suffix))
            self.parseMappingBody(rv)
            self.match(RCURLY)
        else:
            self.match(AT)
            if self.token[0] == STRING:
                tt, fn = self.match(STRING)
                if fn[0] == '<':
                    # global brick_config file path
                    fn = fn.replace('<', '"').replace('>', '"')
                    fn = eval(fn)  # evaluate string
                    fn = self.searchPath.searchGlobalFile(fn)
                else:
                    fn = eval(fn)  # evaluate string
                    fn = self.searchPath.searchRelativeFile(fn, self.filename)
            rv = Config(open(fn), parent, searchPath=self.searchPath)
        return rv

    def parseScalar(self):
        """
        Parse a scalar - a terminal value such as a string or number, or
        an L{Expression} or L{Reference}.

        @return: the parsed scalar
        @rtype: any scalar
        @raise ConfigFormatError: if a syntax error is found.
        """
        lhs = self.parseTerm()
        tt = self.token[0]
        while tt in [PLUS, MINUS]:
            self.match(tt)
            rhs = self.parseTerm()
            lhs = Expression(tt, lhs, rhs)
            tt = self.token[0]
        return lhs

    def parseTerm(self):
        """
        Parse a term in an additive expression (a + b, a - b)

        @return: the parsed term
        @rtype: any scalar
        @raise ConfigFormatError: if a syntax error is found.
        """
        lhs = self.parseFactor()
        tt = self.token[0]
        while tt in [STAR, SLASH, MOD]:
            self.match(tt)
            rhs = self.parseFactor()
            lhs = Expression(tt, lhs, rhs)
            tt = self.token[0]
        return lhs

    def parseFactor(self):
        """
        Parse a factor in an multiplicative expression (a * b, a / b, a % b)

        @return: the parsed factor
        @rtype: any scalar
        @raise ConfigFormatError: if a syntax error is found.
        """
        tt = self.token[0]
        if tt in [NUMBER, WORD, STRING, TRUE, FALSE, NONE]:
            rv = self.token[1]
            if tt != WORD:
                rv = eval(rv)
            self.match(tt)
        elif tt == LPAREN:
            self.match(LPAREN)
            rv = self.parseScalar()
            self.match(RPAREN)
        elif tt == DOLLAR:
            self.match(DOLLAR)
            rv = self.parseReference(DOLLAR)
        elif tt == BACKTICK:
            self.match(BACKTICK)
            rv = self.parseReference(BACKTICK)
            self.match(BACKTICK)
        elif tt == MINUS:
            self.match(MINUS)
            rv = -self.parseScalar()
        else:
            raise ConfigFormatError("%s: unexpected input: %r" %
               (self.location(), self.token[1]))
        return rv

    def parseReference(self, type):
        """
        Parse a reference.

        @return: the parsed reference
        @rtype: L{Reference}
        @raise ConfigFormatError: if a syntax error is found.
        """
        tt = self.token[0]
        if tt == WORD:
            word = self.match(WORD)
            rv = Reference(type, word[1])
            while self.token[0] in [DOT, LBRACK2]:
                self.parseSuffix(rv)
        elif tt == LCURLY and type == DOLLAR:
            self.match(LCURLY)
            functionName = self.match(WORD)
            self.match(LPAREN2)
            #functionArg = self.parseScalar()
            mapping = Mapping()
            functionArg = self.parseValue(mapping, 'arg')
            self.match(RPAREN)
            self.match(RCURLY)

            if functionName[0] != WORD:
                raise ConfigFormatError("%s: expected function name word: %r" % (self.location(), functionName))
            rv = Expression(eval(functionName[1]), functionArg)
        else:
            raise ConfigFormatError("%s: unexpected input: %r" %
               (self.location(), self.token[1]))
        return rv

    def parseSuffix(self, ref):
        """
        Parse a reference suffix.

        @param ref: The reference of which this suffix is a part.
        @type ref: L{Reference}.
        @raise ConfigFormatError: if a syntax error is found.
        """
        tt = self.token[0]
        if tt == DOT:
            self.match(DOT)
            word = self.match(WORD)
            ref.addElement(DOT, word[1])
        else:
            self.match(LBRACK2)
            tt, tv = self.token
            if tt not in [NUMBER, STRING, DOLLAR]:
                raise ConfigFormatError("%s: expected number or string, found %r" % (self.location(), tv))
            if tt == DOLLAR:
                self.token = self.getToken()
                rv = self.parseReference(DOLLAR)
                self.match(RBRACK)
                ref.addElement(DOLLAR, rv)
            else:
                self.token = self.getToken()
                tv = eval(tv)
                self.match(RBRACK)
                ref.addElement(LBRACK, tv)

def defaultMergeResolve(map1, map2, key):
    """
    A default resolver for merge conflicts. Returns a string
    indicating what action to take to resolve the conflict.

    @param map1: The map being merged into.
    @type map1: L{Mapping}.
    @param map2: The map being used as the merge operand.
    @type map2: L{Mapping}.
    @param key: The key in map2 (which also exists in map1).
    @type key: str
    @return: One of "merge", "append", "mismatch" or "overwrite"
             indicating what action should be taken. This should
             be appropriate to the objects being merged - e.g.
             there is no point returning "merge" if the two objects
             are instances of L{Sequence}.
    @rtype: str
    """
    obj1 = map1[key]
    obj2 = map2[key]
    if isinstance(obj1, Mapping) and isinstance(obj2, Mapping):
        rv = "merge"
    elif isinstance(obj1, Sequence) and isinstance(obj2, Sequence):
        rv = "append"
    else:
        rv = "mismatch"
    return rv

def overwriteMergeResolve(map1, map2, key):
    """
    An overwriting resolver for merge conflicts. Calls L{defaultMergeResolve},
    but where a "mismatch" is detected, returns "overwrite" instead.

    @param map1: The map being merged into.
    @type map1: L{Mapping}.
    @param map2: The map being used as the merge operand.
    @type map2: L{Mapping}.
    @param key: The key in map2 (which also exists in map1).
    @type key: str
    """
    rv = defaultMergeResolve(map1, map2, key)
    if rv == "mismatch":
        rv = "overwrite"
    return rv

def overwriteResolve(map1, map2, key):
    """
    Forces overwrite at all times. Avoids merging maps, evaluating
    their keys before their time has come (enables us to inherit
    lazy references without having to construct a dependency graph).
    """
    return "overwrite"

class ConfigMerger(object):
    """
    This class is used for merging two configurations. If a key exists in the
    merge operand but not the merge target, then the entry is copied from the
    merge operand to the merge target. If a key exists in both configurations,
    then a resolver (a callable) is called to decide how to handle the
    conflict.
    """

    def __init__(self, resolver=defaultMergeResolve):
        """
        Initialise an instance.

        @param resolver:
        @type resolver: A callable which takes the argument list
        (map1, map2, key) where map1 is the mapping being merged into,
        map2 is the merge operand and key is the clashing key. The callable
        should return a string indicating how the conflict should be resolved.
        For possible return values, see L{defaultMergeResolve}. The default
        value preserves the old behaviour
        """
        self.resolver = resolver

    def merge(self, merged, mergee):
        """
        Merge two configurations. The second configuration is unchanged,
        and the first is changed to reflect the results of the merge.

        @param merged: The configuration to merge into.
        @type merged: L{Config}.
        @param mergee: The configuration to merge.
        @type mergee: L{Config}.
        """
        self.mergeMapping(merged, mergee)

    def mergeMapping(self, map1, map2):
        """
        Merge two mappings recursively. The second mapping is unchanged,
        and the first is changed to reflect the results of the merge.

        @param map1: The mapping to merge into.
        @type map1: L{Mapping}.
        @param map2: The mapping to merge.
        @type map2: L{Mapping}.
        """
        keys = list(map1.keys())
        for key in list(map2.keys()):
            if key not in keys:
                map1[key] = map2[key]
            else:
                obj1 = map1[key]
                obj2 = map2[key]
                decision = self.resolver(map1, map2, key)
                if decision == "merge":
                    self.mergeMapping(obj1, obj2)
                elif decision == "append":
                    self.mergeSequence(obj1, obj2)
                elif decision == "overwrite":
                    map1[key] = obj2
                elif decision == "mismatch":
                    self.handleMismatch(obj1, obj2)
                else:
                    msg = "unable to merge: don't know how to implement %r"
                    raise ValueError(msg % decision)

    def mergeSequence(self, seq1, seq2):
        """
        Merge two sequences. The second sequence is unchanged,
        and the first is changed to have the elements of the second
        appended to it.

        @param seq1: The sequence to merge into.
        @type seq1: L{Sequence}.
        @param seq2: The sequence to merge.
        @type seq2: L{Sequence}.
        """
        data1 = object.__getattribute__(seq1, 'data')
        data2 = object.__getattribute__(seq2, 'data')
        for obj in data2:
            data1.append(obj)
        comment1 = object.__getattribute__(seq1, 'comments')
        comment2 = object.__getattribute__(seq2, 'comments')
        for obj in comment2:
            comment1.append(obj)

    def handleMismatch(self, obj1, obj2):
        """
        Handle a mismatch between two objects.

        @param obj1: The object to merge into.
        @type obj1: any
        @param obj2: The object to merge.
        @type obj2: any
        """
        raise ConfigError("unable to merge %r with %r" % (obj1, obj2))

class ConfigList(list):
    """
    This class implements an ordered list of configurations and allows you
    to try getting the configuration from each entry in turn, returning
    the first successfully obtained value.
    """

    def getByPath(self, path):
        """
        Obtain a value from the first configuration in the list which defines
        it.

        @param path: The path of the value to retrieve.
        @type path: str
        @return: The value from the earliest configuration in the list which
        defines it.
        @rtype: any
        @raise ConfigError: If no configuration in the list has an entry with
        the specified path.
        """
        found = False
        rv = None
        for entry in self:
            try:
                rv = entry.getByPath(path)
                found = True
                break
            except ConfigError:
                pass
        if not found:
            raise ConfigError("unable to resolve %r" % path)
        return rv
