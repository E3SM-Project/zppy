.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

See `parameter defaults <https://github.com/E3SM-Project/zppy/blob/cdd11e983a52ca54e81168de199be611e42d49f8/zppy/templates/default.ini>`_
on GitHub for a complete list of parameters and their default values.
