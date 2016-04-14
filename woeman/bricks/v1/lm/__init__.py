from woeman import brick, Brick


@brick
class KenLM:
    """KenLM language model estimator"""
    def __init__(self, corpus):
        pass

    def output(self, languageModel):
        """
        :param languageModel: binarized KenLM
        """
        pass

    def configure(self, mosesDir, ngramOrder=5, prune="0 0 1", extraOptions=""):
        """
        :param mosesDir:     path to bin/lmplz
        :param ngramOrder:   n-gram order
        :param prune:        "0 0 1" means prune singleton trigrams and above
        :param extraOptions: additional lmplz options (e.g. --discount_fallback for small corpora)
        """
        Brick.configure(self)
