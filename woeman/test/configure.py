import unittest
from woeman import brick, Brick


class ConfigTests(unittest.TestCase):
    def testConfigureSelf(self):
        """Transferring configuration keys to the Brick object via configureSelf()."""
        @brick
        class Experiment:
            def __init__(self):
                pass

            def output(self, result):
                pass

            def configure(self, key):
                Brick.configure(self)

        e = Experiment()
        e.configure(key='value')
        self.assertEqual(e.key, 'value')

    def testConfigureParts(self):
        """Propagation of configuration keys to parts."""
        @brick
        class Part:
            def __init__(self):
                self.p_ran = True

            def output(self, result):
                pass

            def configure(self, partKey):
                Brick.configure(self)

        @brick
        class Experiment:
            def __init__(self):
                self.e_ran = True
                self.part = Part()

            def output(self, result):
                result.bind(self.part.result)

            def configure(self, key):
                self.part.configure(partKey=key)

        e = Experiment()
        e.configure(key='value')
        self.assertEqual(e.part.partKey, 'value')
