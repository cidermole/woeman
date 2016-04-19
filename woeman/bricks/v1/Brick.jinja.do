{#
 # Basic Brick.do shell script template, written in Jinja2
 # (see http://jinja.pocoo.org/docs/dev/templates/). This is
 # a Jinja comment that is not output into the generated file.
 #
 # Minus characters '-' at opening/closing Jinja tags control
 # (trim away) whitespace.
 #
 # To set up PyCharm IDE syntax highlighting correctly:
 #
 # * install BashSupport plugin
 # * Configure the Jinja template language under Settings -> 'Languages & Frameworks' -> 'Python Template Languages'
 #   * add 'Bourne Again Shell' under 'Template file types'
 # * assign *.do to 'Bourne Again Shell' under 'File Types'
 # * mark 'woeman/bricks/v1' as a Template Folder [2]
 # * disable 'Add missing shebang to file' warning for BashSupport under Settings -> 'Editor/Inspections'
 # * disable 'Show popup in the editor' under Settings -> 'Tools/Web Browsers'
 #
 # [1] https://www.jetbrains.com/help/pycharm/2016.1/configuring-template-languages.html
 # [2] https://www.jetbrains.com/help/pycharm/2016.1/defining-template-directories.html
 #}

{#- *** Add notice about our origins to generated files. *** -#}

{% block Shebang %}{% endblock %}
# If this shell script is called "brick.do", it was GENERATED from
# templates and an experiment config file, and may be OVERWRITTEN.
# Please EDIT THE JINJA TEMPLATE instead. You've been warned.

{#- *** End of notice. *** #}

{#
 # Instead of outputting each dependency as "redo-ifchange dependency",
 # we collect them onto one "redo-ifchange", to improve parallelism.
 #}

{% block Dependencies %}
# Dependency list generated in Brick.jinja.do
{%- for dependencyType in ['input', 'output'] %}
# {{ dependencyType }} dependencies
(
{%- for dependency in dependencyFiles(dependencyType) %}
    echo {{ dependency }}
{%- endfor -%}

{% if dependencyFiles(dependencyType) | length == 0 %}
    # no {{ dependencyType }} dependencies
    true
{%- endif %}
) | xargs redo-ifchange
{% endfor %}
{% endblock %}

# Redirect stdout and stderr of coming commands to logfiles.
#exec 6<&1  # backup stdout to fd=6
#exec 7<&2  # backup stderr to fd=7

#exec 1>brick.STDOUT
#exec 2>brick.STDERR

### Begin actual work ###

{% block Work %}
    # extend the template "brick.jinja.do" and override the
    # block Work to do something useful in this Brick.
{%- endblock %}

### End actual work ###

# Restore stdout
#exec 1<&6  # restore stdout from fd=6

{% block Complete %}
    # mark as completed (stdout goes to our target file "brick")
    echo "{{ brickPath() }}"
{% endblock %}
