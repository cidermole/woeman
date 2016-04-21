#!/usr/bin/env python

import sys
sys.path.append('/home/david/mmt/woeman')

import os
import woeman

from woeman.fs import Filesystem
from woeman.bricks.v1.lm import KenLM

fs = Filesystem()
kenlm = KenLM(corpus='/data/corpus')
#kenlm.setBasePath(os.path.dirname(os.path.realpath(__file__)))  # points to woeman/extras package
kenlm.setBasePath(os.path.dirname(os.path.abspath(__file__)))  # finds the symlinked.py folder
kenlm.createInOuts(fs)
#KenLM.mosesDir = '/home/david/mmt/mmt-src-nosync/mosesdecoder'
kenlm.loadDefaultConfig()
kenlm.configure(ngramOrder=5)

# like render(), but write to the FS.
kenlm.write(fs)

