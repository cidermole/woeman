{#
 # GIZA++/mgiza wrapper.
 #}
{% extends "align/GizaBase.jinja.do" %}

{# overrides GizaBase.jinja.do #}
{% block AddPrepareWork %}

GIZA_DIR=$(pwd)/output/gizaDir
mkdir -p $GIZA_DIR

{% endblock %}


{# overrides GizaBase.jinja.do #}
{% block AddTrainingOptions -%} \
    -do-steps 2 \
    -corpus-dir $(pwd)/input/preparedCorpusDir \
{%- if direction == 2 %}
    -giza-e2f $GIZA_DIR -direction 2 \
{%- else %}
    -giza-f2e $GIZA_DIR -direction 1 \
{%- endif -%}
{% endblock %}
