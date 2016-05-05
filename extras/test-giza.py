#!/usr/bin/env python

import sys
sys.path.append('/home/david/mmt/woeman')

import os
import woeman

from woeman.fs import Filesystem
from woeman.bricks.v1.align import Giza

fs = Filesystem()
giza = Giza(src='/data/src', trg='/data/trg')
giza.setBasePath(os.path.dirname(os.path.abspath(__file__)))  # finds the symlinked.py folder
giza.createInOuts(fs)
giza.loadDefaultConfig()
giza.configure(sourceLang='fr', targetLang='en', finalAlignmentModel=1)

# like render(), but write to the FS.
giza.write(fs)
