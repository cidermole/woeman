from woeman import brick, Brick


@brick
class Giza(Brick):
    """GIZA++ word aligner"""

    cacheDir = None  #: directory to cache word alignments in (to avoid useless recomputation)

    def __init__(self, src, trg):
        """
        :param src: bitext corpus side 1: tokenized, sentence-aligned (one sentence per line)
        :param trg: bitext corpus side 2
        """
        Brick.__init__(self)
        self.gizaPrepare = GizaPrepare(src, trg)
        self.giza12 = GizaAlign(src, trg)
        self.giza21 = GizaAlign(trg, src)
        self.gizaSymmetrize = GizaSymmetrize(self.giza12.alignment, self.giza21.alignment, self.giza12.gizaDir, self.giza21.gizaDir)

    def output(self, alignment):
        """
        :param alignment: word alignment: one line for each sentence pair,
        e.g. "0-0 1-1 2-1 3-4 3-5"
        """
        alignment.bind(self.gizaSymmetrize.alignment)

    # noinspection PyMethodOverriding
    def configure(self, sourceLang, targetLang, symmetrizationHeuristic='grow-diag-final-and', finalAlignmentModel='DEFAULT'):
        """
        :param sourceLang: source language code (independent of direction)
        :param targetLang: target language code (independent of direction)
        :param direction: 2: forward, 1: backward (for train-model.perl)
        :param finalAlignmentModel: type int means use up to that IBM model level, a str like 'DEFAULT' means use GIZA default
        :param symmetrizationHeuristic: see http://www.statmt.org/moses/?n=FactoredTraining.AlignWords
        """
        self.gizaPrepare.configure(sourceLang, targetLang)
        self.giza12.configure(sourceLang, targetLang, direction=2, finalAlignmentModel=finalAlignmentModel)
        self.giza21.configure(sourceLang, targetLang, direction=1, finalAlignmentModel=finalAlignmentModel)
        self.gizaSymmetrize.configure(sourceLang, targetLang)
        Brick.configure(self, locals())


@brick
class GizaAlign(Brick):
    """
    GIZA++ internals.
    Primitive wrapper of train-model.perl for calling word alignment.
    """

    mosesDir = None  #: path containing scripts/training/train-model.perl
    externalBinDir = None  #: path containing mgiza binary and tools (path to mgizapp/bin)

    gizaCpus = 2  #: number of CPUs for mgiza, high numbers not very useful (mgiza just uses more SYS CPU)

    def __init__(self, side1, side2):
        Brick.__init__(self)
        pass

    def output(self, alignment, gizaDir):
        pass

    # noinspection PyMethodOverriding
    def configure(self, sourceLang, targetLang, direction=2, finalAlignmentModel='DEFAULT'):
        """
        :param sourceLang: source language code (independent of direction)
        :param targetLang: target language code (independent of direction)
        :param direction: 2: forward, 1: backward (for train-model.perl)
        :param finalAlignmentModel: type int means use up to that IBM model level, a str like 'DEFAULT' means use GIZA default
        """
        Brick.configure(self, locals())


@brick
class GizaPrepare(GizaAlign):
    """
    GIZA++ internals.
    common preparation steps for both directions (including mkcls)
    """
    # noinspection PyMethodOverriding
    def configure(self, sourceLang, targetLang):
        Brick.configure(self, locals())

    # noinspection PyMethodOverriding
    def output(self, preparedCorpusDir):
        pass


@brick
class GizaSymmetrize(GizaAlign):
    """
    GIZA++ internals.
    Combines forward and backward alignments using a symmetrizationHeuristic.
    """
    def __init__(self, alignment12, alignment21, gizaDir12, gizaDir21):
        Brick.__init__(self)
        pass

    # noinspection PyMethodOverriding
    def configure(self, sourceLang, targetLang):
        Brick.configure(self, locals())
