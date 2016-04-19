import unittest

import jinja2

from woeman import brick, Brick
from woeman.fs import MockFilesystem, unsafe_jinja_split_template_path
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

    def testWrite(self):
        """Render and write a Brick's do script."""

        # allows '..' in the template path, contrary to jinja2 default implementation
        # (the jinja relative path to Basic.jinja.do is '../../test/Basic.jinja.do')
        jinja2.loaders.split_template_path = unsafe_jinja_split_template_path

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
