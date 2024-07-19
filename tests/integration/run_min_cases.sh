# Edit the list below to list the min cases you think would be affected by your code changes:
min_cases=("1st min case" "2nd min case")

# Edit this to be the machine you're on
machine=chrysalis

pip install . && python tests/integration/utils.py
for min_case in "${min_cases[@]}"
do
  zppy -c tests/integration/generated/test_min_case_${min_case}_${machine}.cfg
done

# For two-cfg cases, you'll need to run the _2 cfgs after the _1 cfgs' jobs have finished.
