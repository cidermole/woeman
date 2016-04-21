from woeman import brick, Brick


@brick
class KenLM:
    """KenLM language model estimator"""

    mosesDir = None  #: path to bin/lmplz

    def __init__(self, corpus):
        """
        :param corpus: tokenized training corpus
        """
        pass

    def output(self, languageModel):
        """
        :param languageModel: binarized KenLM
        """
        pass

    def configure(self, ngramOrder=5, prune="0 0 1", extraOptions=""):
        """
        :param ngramOrder:   n-gram order
        :param prune:        "0 0 1" means prune singleton trigrams and above
        :param extraOptions: additional lmplz options (e.g. --discount_fallback for small corpora)
        """
        Brick.configure(self)
