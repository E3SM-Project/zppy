# Datathon Project

## How to use

1. Run `python simulation_output_reviewer.py > available_data.txt`
2. Run `python zppy_config_generator.py`, after setting `ZPPY_CFG_LOCATION = "/home/ac.forsyth2/ez/zppy/config_builder/"` and a `UNIQUE_ID`. That will produce a starting point `zppy` `cfg` at `/home/ac.forsyth2/ez/zppy/config_builder/zppy_config_<UNIQUE_ID>.cfg`. (Note: this actually reruns the `simulation_output_reviewer`. For a production use-case we'd only do single data read, and simply write the output as one step.)
3. Run `run_agent.py --base_config=zppy_config_<UNIQUE_ID>.cfg --available_data=available_data.txt --query=<QUERY>`.
