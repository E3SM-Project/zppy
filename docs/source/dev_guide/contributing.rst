**********************************
Contributing to This Documentation
**********************************

.. highlight:: none

Getting Started
===============

This documentation is created using Sphinx, which is an open-source tool
that makes it easy to create intelligent and beautiful documentation, written
by Georg Brandl and licensed under the BSD license.

The documentation is maintained in the ``main`` branch of the GitHub repository.
You can include code and its corresponding documentation updates in a single pull request (PR).

After merging a PR, GitHub Actions automates the documentation building process.
It pushes the HTML build to the ``gh-pages`` branch, which is hosted on GitHub Pages.

Edit Documentation
==================

Sphinx uses `reStructuredText <http://docutils.sourceforge.net/rst.html>`_
as its markup language. For more information on how to write documentation
using Sphinx, you can refer to

* `First Steps with Sphinx <http://www.sphinx-doc.org/en/stable/tutorial.html>`_
* `reStructuredText Primer <http://www.sphinx-doc.org/en/stable/rest.html#external-links>`_

.. code-block:: bash

    # Sphinx is included in the dev environment,
    # so we just need to set one up:
    cd zppy
    conda clean --all --y
    conda env create -f conda/dev.yml -n env-name
    python -m pip install . 

    # Now, we can produce the documentation locally:
    cd docs
    make html

    # And transfer it to a web server path so we can see it online.

    # Example web server paths:
    # Chrysalis: /lcrc/group/e3sm/public_html/diagnostic_output -> https://web.lcrc.anl.gov/public/e3sm/diagnostic_output
    # Compy: /compyfs/www -> https://compy-dtn.pnl.gov
    # Perlmutter: /global/cfs/cdirs/e3sm/www -> https://portal.nersc.gov/cfs/e3sm

    # For more machines, go to:
    # https://github.com/E3SM-Project/mache/tree/main/mache/machines
    # Select the cfg for the machine, and find the `[web_portal]` section.
    # That will show the `base_path` and `base_url`.

    cp -r _build/ base_path/$USER/zppy_docs
    # Needs to be 755 to show up on https://portal.nersc.gov/cfs/e3sm
    chmod -R 755 base_path/$USER/zppy_docs

    # Optional -- if you want to generate and view versioned docs:
    sphinx-multiversion source _build/html

Pull requests should bundle together associated code changes, test changes, and documentation changes. Once you've merged your pull request and GitHub Actions finishes building the docs, changes will be visible on the
`zppy documentation page <https://docs.e3sm.org/zppy/>`_.

How Documentation is Versioned
------------------------------
The `sphinx-multiversion <https://github.com/Holzhaus/sphinx-multiversion>`_ package manages documentation versioning.

``sphinx-multiversion`` is configured to generate versioned docs for available tags and
branches. Ones that don’t contain both the sphinx ``source`` directory and the ``conf.py`` file will be skipped automatically.

    - Run ``sphinx-multiversion source _build/html --dump-metadata`` to see which tags/branches matched.
