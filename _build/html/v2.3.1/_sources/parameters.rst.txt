.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

See `parameter defaults <https://github.com/E3SM-Project/zppy/blob/ec4216a6d84d1c66c2222df91ae7f1f0abe8f624/zppy/templates/default.ini>`_
on GitHub for a complete list of parameters and their default values.
