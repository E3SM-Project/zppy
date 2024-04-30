.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/ac90fa116b1a62eaacfa9c4efbe4d31c8c1a5e5c/zppy/templates/default.ini>`_
on GitHub for a complete list of parameters and their default values. 
You can also view the most up-to-date, 
`unreleased parameter defaults <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/default.ini>`_.
