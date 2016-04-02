import unittest
from woeman import brick, BrickConfigError, Output


class BasicTests(unittest.TestCase):
    def testOutputMissing(self):
        """Defining a Brick without outputs must raise an error."""
        with self.assertRaises(BrickConfigError):
            @brick
            class Experiment:
                def __init__(self):
                    pass

    def testBrickDefinition(self):
        """Define the simplest possible valid Brick, and make sure its constructor runs."""
        @brick
        class Experiment:
            def __init__(self):
                pass
            def output(self, result):
                pass

        e = Experiment()
        self.assertTrue(isinstance(e.result, Output))
