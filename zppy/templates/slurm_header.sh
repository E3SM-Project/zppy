
# Running on {{ machine }}

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account={{ account }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
{% if reservation  %}
#SBATCH  --reservation={{ reservation }}
{% endif %}
{% if machine in ['anvil', 'chrysalis'] %}
#SBATCH  --partition={{ partition }}

{% elif machine == 'compy' %}
#SBATCH  --qos={{ qos }}
#SBATCH  --partition={{ partition }}

{% elif machine in ['cori-haswell', 'pm-cpu', 'pm-gpu'] %}
#SBATCH  --qos={{ qos }}
#SBATCH  --constraint={{ constraint }}

{% endif %}
