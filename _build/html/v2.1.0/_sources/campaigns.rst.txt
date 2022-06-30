.. _campaigns:

***************
Campaigns
***************

The ``campaign`` parameter allows users to choose a template of default values for their ``zppy`` run.
Inheritance in configuration files still works with campaigns, so users may override values from a campaign's configuration file.

Campaign configuration files can be found in the `zppy/zppy/templates directory <https://github.com/E3SM-Project/zppy/tree/main/zppy/templates>`_. ``zppy`` currently supports the following campaigns:

- cryosphere.cfg
- high_res_v1.cfg
- water_cycle.cfg

High-resolution analysis (``campaign = "high_res_v1"``) is only appropriate for some simulations
(e.g., those with the oRRS18to6 ocean and sea-ice mesh).
It will only work if you:

- have access to the `bigmem nodes on Cori <https://docs.nersc.gov/systems/cori-largemem/#access-to-the-large-memory-nodes>`_
- first load the necessary module with ``module load cmem``.
