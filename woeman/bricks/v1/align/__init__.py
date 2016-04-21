from woeman import brick, Brick


@brick
class Giza:
    """GIZA++ word aligner"""
    def __init__(self, src, trg):
        """
        :param src: bitext corpus side 1: tokenized, sentence-aligned (one sentence per line)
        :param trg: bitext corpus side 2
        """
        pass

    def output(self, alignment):
        """
        :param alignment: word alignment: one line for each sentence pair,
        e.g. "0-0 1-1 2-1 3-4 3-5"
        """
        pass

    def configure(self, cacheDir):
        #Brick.configure(self)
        pass
