{% extends "Brick.jinja.do" %}

{% block Work %}

{{ mosesDir }}/bin/lmplz --text input/corpus --order {{ ngramOrder }} \\
  --arpa output/languageModel.arpa --prune {{ prune }} -T $(pwd)/output -S 20% \\
  {{ extraOptions }}
{{ mosesDir }}/bin/build_binary output/languageModel.arpa output/languageModel
rm -f output/languageModel.arpa

{% endblock %}
