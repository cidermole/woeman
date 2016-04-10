import unittest
from woeman.fs import FilesystemInterface
from woeman import brick, Input, Output
import os


class MockFilesystem(FilesystemInterface):
    """Mock implementation of FilesystemInterface that keeps track of calls."""
    def __init__(self):
        self.symlinks = {}  # dict: symlinks[linkName] = target
        self.dirs = set()   # set([dirs...])

    def symlink(self, target, linkName):
        self.symlinks[linkName] = target

    def makedirs(self, directory):
        self.dirs.add(directory)


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
