#!/usr/bin/env python

import sys
sys.path.append('/home/david/mmt/woeman')

import os
import woeman

from woeman.fs import Filesystem
from woeman.bricks.v1.align import Giza

fs = Filesystem()
giza = Giza(src='/home/david/mmt/data/training/small/ep/train.clean.en', trg='/home/david/mmt/data/training/small/ep/train.clean.it')
giza.setBasePath(os.path.dirname(os.path.abspath(__file__)))  # finds the symlinked.py folder
giza.createInOuts(fs)
giza.loadDefaultConfig()
giza.configure(sourceLang='en', targetLang='it', finalAlignmentModel=1)

# like render(), but write to the FS.
giza.write(fs)
