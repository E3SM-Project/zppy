.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

.. warning::
    The ``amwg`` section is user-contributed and is not officially supported/documented!

See `parameter defaults <https://github.com/E3SM-Project/zppy/blob/4d6bb334d24926809b20ef2206a32c702bd89fd0/zppy/templates/default.ini>`_
on GitHub for a complete list of parameters and their default values.
