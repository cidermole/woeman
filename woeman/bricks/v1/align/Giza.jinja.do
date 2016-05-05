{#
 # Decides whether to provide cached alignment or to actually compute it using our parts.
 #}
{% extends "Brick.jinja.do" %}


# overrides Brick.jinja.do
{% block Dependencies %}

# handle input dependencies (make sure inputs exist)

(
    # dependencies (input only)
    {%- for dependency in dependencyFiles('input') %}
        echo {{ dependency }}
    {%- endfor %}

{% if dependencyFiles('input') | length == 0 %}
    # we have no dependencies
    true
{% endif %}
) | xargs redo-ifchange


# now check input corpus hashes to see if this corpus has been aligned before

srcHash=$(sha1sum input/src | awk '{print $1}')
trgHash=$(sha1sum input/trg | awk '{print $1}')
hash=${srcHash}_${trgHash}
cachedAlignment="{{ cacheDir }}/${hash}.{{ finalAlignmentModel }}"

# do not have cached version? run parts.
if [ ! -e "$cachedAlignment" ]; then

# handle output dependencies (create the alignment)

(
    # dependencies (output only)
    {%- for dependency in dependencyFiles('output') %}
        echo {{ dependency }}
    {%- endfor %}

{% if dependencyFiles('output') | length == 0 %}
    # we have no dependencies
    true
{% endif %}
) | xargs redo-ifchange

fi

{% endblock %}


{% block Work %}

if [ -e "$cachedAlignment" ]; then
  echo "Using precomputed cached word alignment, hash $hash."
  echo "NOTE: hash does not currently include GIZA options."
  zcat "$cachedAlignment" > output/alignment
else
  # cache the resulting alignment (if not yet cached)
  if [ -d "{{ cacheDir }}" ]; then
    gzip -c output/alignment > "$cachedAlignment.tmp.$$"
    # avoid races where the file is still being created
    mv "$cachedAlignment.tmp.$$" "$cachedAlignment"
  fi
fi

{% endblock %}
