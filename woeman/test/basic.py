import unittest
from woeman import brick, Brick, BrickConfigError, Output


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
                self.i_ran = True

            def output(self, result):
                pass

        e = Experiment()
        self.assertTrue(isinstance(e.result, Output))
        self.assertTrue(e.i_ran)
        self.assertTrue(e.parent is None)

    def testBrickParts(self):
        """Define the simplest possible valid Brick with parts, and make sure constructors run."""
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

            def output(self, result):
                result.bind(self.part.result)

        e = Experiment()
        self.assertTrue(isinstance(e.result, Output))
        self.assertTrue(e.e_ran)
        self.assertTrue(e.part.p_ran)
        self.assertTrue(e.parent is None)
        self.assertTrue(e.part.parent == e)
        self.assertTrue(e.result.ref == e.part.result)
        self.assertTrue(e._brick_parts[0] == e.part)

    def testBrickInheritanceParts(self):
        """Inheritance of a part."""
        @brick
        class Part:
            def __init__(self):
                self.p_ran = True

            def output(self, result):
                pass

        @brick
        class Base:
            def __init__(self):
                self.b_ran = True
                self.part = Part()

            def output(self, result):
                result.bind(self.part.result)

        @brick
        class Experiment(Base):
            def __init__(self):
                # note: you CANNOT use a super constructor call as below:
                # super(Experiment, self).__init__()
                # (try to fix this via class hierarchy in BrickDecorator.patchClass() if you feel ambitious)
                Base.__init__(self)
                self.e_ran = True

            def output(self, result):
                # to get output bindings of base, we must either
                # * omit def output() and inherit its implementation,
                # * or explicitly call super output():

                # note: you CANNOT use super(Experiment, self) here - see explanation above at __init__.
                # super(Experiment, self).output(result)
                Base.output(self, result)

        e = Experiment()
        self.assertTrue(e.e_ran)
        self.assertTrue(e.b_ran)
        self.assertTrue(e.part.p_ran)
        self.assertTrue(e.parent is None)
        self.assertTrue(e.part.parent == e)
        self.assertTrue(e.result.ref == e.part.result)
        self.assertTrue(e._brick_parts[0] == e.part)

    def testBrickInheritance(self):
        """The simplest possible inheritance scenario."""
        @brick
        class Base:
            def __init__(self):
                self.b_ran = True

            def output(self, result):
                pass

        @brick
        class Experiment(Base):
            def __init__(self):
                Base.__init__(self)
                self.e_ran = True

            def output(self, result):
                pass

        e = Experiment()
        self.assertTrue(e.e_ran)
        self.assertTrue(e.b_ran)

        # test dependencies
        self.assertEqual(e.result.dependencies(), [])


    def testBrickInheritanceExplicitBrick(self):
        """Test explicitly specifying the super class Brick, and explicitly calling its __init__."""
        @brick
        class Part:
            def __init__(self):
                self.p_ran = True

            def output(self, result):
                pass

        # optionally, we can specify the base class Brick as well, to make IDE happy.
        @brick
        class Experiment(Brick):
            def __init__(self):
                # you do not need to call the base constructor here (it is called by __init__ wrapper),
                # but we should tolerate it (makes IDE and idiomatic programmers happy)
                Brick.__init__(self)

                self.e_ran = True
                self.part = Part()
                self.parts = [Part()]
                self.mapped = {'zero': Part()}

            def output(self, result):
                result.bind(self.part.result)

        e = Experiment()
        self.assertTrue(e.e_ran)
        self.assertTrue(e.part.p_ran)

        # test dependencies
        self.assertEqual(e.result.dependencies(), [e.part])
        # note: why is e.part printed as "<woeman.decorator.Part object at 0x7f0494940470>"?
        # (inheritance hierarchy?)
