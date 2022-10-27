{% if machine == 'compy' %}

# Running on compy

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account={{ account }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --qos={{ qos }}
#SBATCH  --partition={{ partition }}

{% elif machine in ['pm-cpu', 'pm-gpu'] %}

# Running on pm-cpu or pm-gpu depending on 'constraint'

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account={{ account }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --qos={{ qos }}
#SBATCH  --constraint={{ constraint }}

{% elif machine == 'anvil' %}

# Running on anvil

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account={{ account }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --partition={{ partition }}

{% elif machine == 'chrysalis' %}

# Running on chrysalis

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account={{ account }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --partition={{ partition }}

{% endif %}
