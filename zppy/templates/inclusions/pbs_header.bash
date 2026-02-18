
# Running on {{ machine }}

#PBS -N {{ prefix }}
#PBS -A {{ account }}
#PBS -l select={{ nodes }}:system={{ machine }}
#PBS -l walltime={{ walltime }}
#PBS -o {{ scriptDir }}/{{ prefix }}.o
#PBS -e {{ scriptDir }}/{{ prefix }}.e
#PBS -l place=scatter
{% if reservation  %}
#PBS -l {{ reservation }}
{% endif %}
{% if machine in ['polaris'] %}
#PBS -q {{ partition }}
#PBS -l filesystems=home:grand

{% elif machine in ['aurora'] %}
#PBS -q {{ partition }}
#PBS -l filesystems=home:flare

{% endif %}
