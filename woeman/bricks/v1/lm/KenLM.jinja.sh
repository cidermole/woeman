{% extends "brick.jinja.do" %}

{% block Work %}

{{ brick.MOSES }}/bin/lmplz --text input/corpus --order {{ brick.ngramOrder }} \\
  --arpa output/languageModel.arpa --prune {{ brick.prune }} -T $(pwd)/output -S 20% \\
  {{ brick.extraOptions }}
{{ brick.MOSES }}/bin/build_binary output/languageModel.arpa output/languageModel
rm -f output/languageModel.arpa

{% endblock %}
