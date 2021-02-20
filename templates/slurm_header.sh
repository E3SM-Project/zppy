{% if machine == 'compy' %}

# Running on compy 

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account=e3sm
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --qos={{ qos }}
#SBATCH  --partition={{ partition }}

{% elif machine == 'cori' %}

# Running on cori-haswell or cori-knl depending on 'partition'

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account=e3sm
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --qos={{ qos }}
#SBATCH  --constraint={{ partition }}

{% elif machine == 'anvil' %}

# Running on anvil 

#SBATCH  --job-name={{ prefix }}
#SBATCH  --account=condo
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}
#SBATCH  --partition={{ partition }}

{% elif machine == 'chrysalis' %}

# Running on chrysalis

#SBATCH  --job-name={{ prefix }}
#SBATCH  --nodes={{ nodes }}
#SBATCH  --output={{ scriptDir }}/{{ prefix }}.o%j
#SBATCH  --exclusive
#SBATCH  --time={{ walltime }}

{% endif %}
