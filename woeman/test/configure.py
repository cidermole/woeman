import unittest
from woeman import brick, Brick


class ConfigTests(unittest.TestCase):
    def testConfigureSelf(self):
        """
        Test transfering configuration keys to the Brick object via configureSelf().
        """
        @brick
        class Experiment:
            def __init__(self):
                pass

            def output(self, result):
                pass

            def configure(self, key):
                Brick.configureSelf(self)

        e = Experiment()
        e.configure(key='value')
        self.assertEqual(e.key, 'value')
