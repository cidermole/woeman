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

    def configure(self, ngramOrder=5, prune="0 0 1", extraOptions=None):
        """
        :param ngramOrder:   n-gram order
        :param prune:        "0 0 1" means prune singleton trigrams and above
        :param extraOptions: additional lmplz options dict (e.g. 'discount_fallback' for small corpora)
        """
        if extraOptions is None:
            extraOptions = {}

        extra_cmd_line = ''
        for key in extraOptions:
            if key == 'discount_fallback':
                extra_cmd_line += ' --discount_fallback'
            else:
                raise ValueError('KenLM: unsupported extraOptions key "%s"' % key)

        self.extraOptions = extra_cmd_line
        del extraOptions, extra_cmd_line  # avoid adding these to the object below. Ugly!
        Brick.configure(self, locals())
