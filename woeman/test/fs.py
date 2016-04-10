import unittest
from woeman.fs import FilesystemInterface
from woeman import brick


class MockFilesystem(FilesystemInterface):
    """Mock implementation of FilesystemInterface that keeps track of calls."""
    def __init__(self):
        self.symlinks = {}  # dict: symlinks[linkName] = target
        self.dirs = set()   # set([dirs...])

    def symlink(self, target, linkName):
        self.symlinks[linkName] = target

    def makedirs(self, directory):
        self.dirs.add(directory)


class BasicTests(unittest.TestCase):
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
        e.setBasePath('/testpath')
        self.assertEqual(e._brick_path, '/testpath/Experiment')
        self.assertEqual(e.part._brick_path, '/testpath/Experiment/part')
        self.assertEqual(e.parts[0]._brick_path, '/testpath/Experiment/parts_0')
        self.assertEqual(e.mapped['zero']._brick_path, '/testpath/Experiment/mapped_zero')
