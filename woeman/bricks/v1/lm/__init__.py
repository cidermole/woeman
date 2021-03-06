from woeman import brick, Brick


@brick
class KenLM(Brick):
    """KenLM language model estimator"""

    mosesDir = None  #: path containing bin/lmplz

    def __init__(self, corpus):
        """
        :param corpus: tokenized training corpus
        """
        Brick.__init__(self)

    def output(self, languageModel):
        """
        :param languageModel: binarized KenLM
        """
        pass

    def configure(self, ngramOrder=5, prune="0 0 1", otherOptions=None):
        """
        :param ngramOrder:   n-gram order
        :param prune:        "0 0 1" means prune singleton trigrams and above
        :param otherOptions: additional lmplz options dict (e.g. 'discount_fallback' for small corpora)
        """
        if otherOptions is None:
            otherOptions = {}

        extraOptions = ''
        for key in otherOptions:
            if key == 'discount_fallback':
                extraOptions += ' --discount_fallback'
            else:
                raise ValueError('KenLM: unsupported extraOptions key "%s"' % key)

        self.extraOptions = extraOptions
        del otherOptions  # avoid adding these to the object below.
        # (note: the local extraOptions will also redundantly be copied to self.extraOptions again)
        Brick.configure(self, locals())
