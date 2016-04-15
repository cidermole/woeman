import unittest
from woeman.fs import FilesystemInterface
from woeman import brick, Brick, Input, Output
import os
import jinja2
from os import path
from jinja2.exceptions import TemplateNotFound


class MockFilesystem(FilesystemInterface):
    """Mock implementation of FilesystemInterface that keeps track of calls."""
    def __init__(self):
        self.symlinks = {}  # dict: symlinks[linkName] = target
        self.dirs = set()   # set([dirs...])
        self.files = {}     # dict: files[fileName] = contents

    def symlink(self, target, linkName):
        self.symlinks[linkName] = target

    def makedirs(self, directory):
        self.dirs.add(directory)

    def replaceFileContents(self, fileName, newContents):
        self.files[fileName] = newContents


def normalizeSymlinks(symlinks):
    """
    Normalize a dict of symlinks with relative symlink paths to become absolute paths.
    :param symlinks: dict: symlinks[linkName] = target
    """
    def normalize(linkName, target):
        if target.startswith('/'):
            return target  # do not change absolute paths
        return os.path.normpath(os.path.join(os.path.dirname(linkName), target))  # normalize relative paths
    return {linkName: normalize(linkName, target) for linkName, target in symlinks.items()}


# override of the jinja2.loaders version
def unsafe_split_template_path(template):
    """Split a path into segments and skip jinja2 sanity check for testing."""
    pieces = []
    for piece in template.split('/'):
        if path.sep in piece \
           or (path.altsep and path.altsep in piece):
            # or piece == path.pardir:  # allows '..' in the path, contrary to jinja2 default implementation
            raise TemplateNotFound(template)
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces


class FilesystemTests(unittest.TestCase):
    def testBrickBasePath(self):
        """Test the mapping of Brick parts to filesystem paths."""
        @brick
        class Part:
            def __init__(self):
                self.p_ran = True

            def output(self, result):
                pass

        @brick
        class Experiment:
            def __init__(self):
                self.e_ran = True
                self.part = Part()
                self.parts = [Part()]
                self.mapped = {'zero': Part()}

            def output(self, result):
                result.bind(self.part.result)

        e = Experiment()
        e.setBasePath('/e')
        self.assertEqual(e._brick_path, '/e/Experiment')
        self.assertEqual(e.part._brick_path, '/e/Experiment/part')
        self.assertEqual(e.parts[0]._brick_path, '/e/Experiment/parts_0')
        self.assertEqual(e.mapped['zero']._brick_path, '/e/Experiment/mapped_zero')

    def testCreateInOuts(self):
        """Test creation of input/output directory structures and symlinks for Bricks and their parts."""

        unitTest = self

        @brick
        class Part:
            def __init__(self, partInput):
                unitTest.assertTrue(isinstance(partInput, Input))

            def output(self, partResult):
                unitTest.assertTrue(isinstance(partResult, Output))

        @brick
        class Experiment:
            def __init__(self, experimentInput):
                """
                Bricks idiomatically pass only their filesystem inputs as __init__() arguments.
                The actual value of 'experimentInput' received in here is wrapped by the woeman.Input() class
                """
                unitTest.assertTrue(isinstance(experimentInput, Input))
                unitTest.assertEquals(experimentInput.ref, '/data/input')
                self.part = Part(experimentInput)

            def output(self, experimentResult):
                experimentResult.bind(self.part.partResult)

        fs = MockFilesystem()
        e = Experiment('/data/input')
        e.setBasePath('/e')
        e.createInOuts(fs)

        dirs = {
            '/e/Experiment/part/input',
            '/e/Experiment/input',
            '/e/Experiment/part/output',
            '/e/Experiment/output'
        }
        self.assertEqual(fs.dirs, dirs)

        symlinks = {
            '/e/Experiment/input/experimentInput': '/data/input',
            '/e/Experiment/part/input/partInput': '../../input/experimentInput',
            '/e/Experiment/output/experimentResult': '../part/output/partResult'
        }
        print(fs.symlinks)
        self.assertEqual(fs.symlinks, normalizeSymlinks(symlinks))

    def testWrite(self):
        """Render and write a Brick's do script."""

        # allows '..' in the path, contrary to jinja2 default implementation
        jinja2.loaders.split_template_path = unsafe_split_template_path

        @brick
        class Basic:
            """Our Jinja template is in the same Python package (same directory) as us, and is called Basic.jinja.do"""
            def __init__(self):
                pass

            def output(self, out):
                pass

            def configure(self, mosesDir, mosesIni):
                Brick.configure(self)

        fs = MockFilesystem()
        b = Basic()
        b.setBasePath('/e')
        b.configure(mosesDir='/moses', mosesIni='/data/ini')
        b.write(fs)

        # original template: "{{ mosesDir }}/bin/moses -f {{ mosesIni }} > output/out"
        files = {'/e/Basic/brick.do': '/moses/bin/moses -f /data/ini > output/out'}
        self.assertEqual(fs.files, files)
