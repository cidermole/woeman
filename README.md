# Workflow and Experiment Manager

Models a scientific workflow, where multiple tools need to be run in a chain, each tool using some (large, computationally expensive) intermediate result files output from previous tools.

Woeman follows a few design goals:

1) Model the experiment as a tree of **bricks**
2) Avoid re-running existing intermediate computations when changing some parts of a workflow, since such computations may be expensive
3) Allow both easy composition of experiments
4) Allow generic tool invocation from brick definitions with sane, familiar syntax
5) Allow grouping of input and output files

For 1), the design is as follows:

    * Each brick has with named **inputs** and **outputs** that represent files
    * Each brick is composed of an optional set of sub-bricks executed first, and a shellscript template

For 2), Woeman builds upon a make-like build system that recognizes changes in input files (`redo`).

For 3), Woeman allows changing parts of existing bricks by using Python inheritance (for wiring inputs and outputs).

For 4), Woeman uses the Jinja templating language for generating shellscripts, and generates the entire experiment tree structure with symlinked input and output files. Then, it provides those files to the shellscripts.

Regarding 5), inputs/outputs may be file lists, in which case directories are generated, containing numbered symlinks for the individual items.

## Types of brick dependencies

* **Input dependency**: Represents a sub-brick's input depending on the input of its parent brick
* **Output dependency**: Represents a parent brick's output depending on a sub-brick's output

## Writing bricks

See `brick.py` and `Brick.jinja.do`.

## Example tree

See https://github.com/cidermole/bricks/blob/master/bricks.py

   # Brick script execution
   # ----------------------
   # Happens via 'redo', each script is run in its Brick working directory.
   # 'bricks.py' sets up a hierarchy of working directories for Bricks,
   # with symlinks of inputs (and outputs for Bricks containing parts.)
   #
   # number of run (always 0 currently, incremental experiments not implemented)
   # |
   # v   name of Brick (outermost Brick is always called Experiment)
   # 0/  v
   #     Experiment/
   #         input/rawCorpusSource -> /data/raw.corpus.en
   #         input/rawCorpusTarget -> /data/raw.corpus.it
   #         output/alignment -> WordAligner0/output/alignment
   #
   #         PrepSrc/
   #             input/raw -> ../../input/rawCorpusSource
   #             output/truecased            < not actually created by bricks.py
   #             <...>
   #
   #         PrepTrg/
   #             input/raw -> ../../input/rawCorpusTarget
   #             output/truecased            < not actually created by bricks.py
   #             <...>
   #
   #         WordAligner0/
   #             # links dangle (target doesn't exist) until actual run of Prep*
   #             input/src -> ../../PrepSrc/output/truecased
   #             input/trg -> ../../PrepTrg/output/truecased
   #
   #             Giza12/
   #                 input/crp1 -> ../../input/src
   #                 <...>
