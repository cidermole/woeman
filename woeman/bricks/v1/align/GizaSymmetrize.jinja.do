{#
 # GIZA++/mgiza wrapper.
 #}
{% extends "align/GizaBase.jinja.do" %}

{# overrides GizaBase.jinja.do #}
{% block AddTrainingOptions -%} \
    -do-steps 3 \
    -corpus-dir $(pwd)/input/preparedCorpusDir \
    -giza-e2f $(pwd)/input/gizaDir12 -giza-f2e $(pwd)/input/gizaDir21 \
    -alignment {{ symmetrizationHeuristic }} \
{%- endblock %}

{# overrides GizaBase.jinja.do #}
{% block AddFinishWork %}

    # link to finished word alignment
    ln -sf ../model/aligned.{{ symmetrizationHeuristic }} output/alignment

{% endblock %}
