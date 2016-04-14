import unittest
from woeman.bricks.v1.lm import KenLM


class RenderTests(unittest.TestCase):
    def testTemplatePath(self):
        """Verify relative path generation for Jinja."""
        kenlm = KenLM(corpus='/data/corpus')
        self.assertEqual(kenlm.jinjaTemplatePath(), 'lm/KenLM.jinja.do')

    def testRenderKenLM(self):
        """Check whether we can render without exceptions."""
        kenlm = KenLM(corpus='/data/corpus')
        #kenlm.setBasePath('/e')
        #kenlm.createInOuts(fs)
        kenlm.render()
