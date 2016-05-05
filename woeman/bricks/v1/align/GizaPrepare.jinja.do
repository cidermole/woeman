{#
 # GIZA++/mgiza wrapper.
 #}
{% extends "align/GizaBase.jinja.do" %}

{# overrides GizaBase.jinja.do #}
{% block AddPrepareWork %}

    GIZA_CORPUS_DIR=$(pwd)/output/preparedCorpusDir
    mkdir -p $GIZA_CORPUS_DIR

    mkdir -p corpus
    GIZA_CORPUS=$(pwd)/corpus/crp

    # ensure that corpus file names are suffixed properly for train-model.perl
    ln -sf ../input/side1 ${GIZA_CORPUS}.{{ sourceLang }}
    ln -sf ../input/side2 ${GIZA_CORPUS}.{{ targetLang }}

{% endblock %}

{# overrides GizaBase.jinja.do #}
{% block AddTrainingOptions -%} \
    -do-steps 1 \
    -corpus $GIZA_CORPUS \
    -corpus-dir $GIZA_CORPUS_DIR \
{%- endblock %}
