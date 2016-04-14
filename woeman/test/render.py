import unittest
from woeman import brick, Brick
from woeman.bricks.v1.lm import KenLM

class RenderTests(unittest.TestCase):
    def testTemplatePath(self):
        kenlm = KenLM(corpus='/data/corpus')
        print(kenlm.jinjaTemplatePath())

    def testRenderKenLM(self):
        kenlm = KenLM(corpus='/data/corpus')
        #kenlm.setBasePath('/e')
        #kenlm.createInOuts(fs)
        kenlm.render()
