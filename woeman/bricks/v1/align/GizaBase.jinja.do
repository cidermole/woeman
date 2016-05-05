{#
 # GIZA++/mgiza wrapper.
 #}
{% extends "Brick.jinja.do" %}

{# overrides Brick.jinja.do #}
{% block Work %}

{% block AddPrepareWork %}{% endblock %}

# note: -alignment [symmetrization-heuristic] is not needed here, as we do not yet symmetrize.

{%- if finalAlignmentModel is number %}
echo >&2 "note: word aligner using non-default --final-alignment-model={{ finalAlignmentModel }}"
{%- endif %}

{{ mosesDir }}/scripts/training/train-model.perl \
{% block AddTrainingOptions %}{% endblock %}
{%- if finalAlignmentModel is number %}
    --final-alignment-model={{ finalAlignmentModel }} \
{%- endif %}
    -external-bin-dir "{{ externalBinDir }}" \
    -mgiza -mgiza-cpus {{ gizaCpus }} -parallel \
    -f {{ sourceLang }} -e {{ targetLang }}

{% block AddFinishWork %}{% endblock %}

{%- endblock %}
