How to Prepare a Release
========================

In this guide, we'll cover:

* Preparing The Code For Release
* Creating A Release On GitHub
* Releasing The Software On Anaconda
* Creating a New Version of the Documentation


Preparing The Code For Release
------------------------------

These steps entail modifying files before a release is made.

1. Pull the lastest code from whatever branch you want to release from.
It's usually ``main``.

    ::

        git fetch <upstream-origin> main
        git checkout -b <branch-name> <upstream-origin>/main


2. Edit the ``version`` argument in ``setup.py`` to the new version.
Don't prefix this with a "v".

    .. code-block:: python

        setup(
            name="zppy",
            version="1.0.0",
            author="Ryan Forsyth, Chris Golaz",
            author_email="forsyth2@llnl.gov, golaz1@llnl.gov",
            description="Post-processing software for E3SM",
            python_requires='>=3.6',
            intall_requires=['configobj', 'jinja2'],
            packages=find_packages(exclude=["*.test", "*.test.*", "test.*", "test"]),
            package_data={'': data_files},
            entry_points={"console_scripts": ["zppy=zppy.__main__:main"]},
        )

3. Edit ``__version__`` in ``zppy/__init__.py``.
We use ``__version__`` when generating the webpages.

    ::

        __version__ = 'v1.0.0'

4. Change the ``version`` and ``git_rev`` tag in ``conda/meta.yaml`` by setting ``version``.
``version`` is what the version of the software will be on Anaconda and
``git_rev`` is the tag that we'll setup on GitHub in the next section.

    .. note::
        When running ``conda build``, ``conda`` will download the code tagged by ``git_rev``.
        Even though ``meta.yaml`` is in your local clone of the repo, running ``conda build``
        from here **does not** build the package based on your local code.

    ::

        {% set name = "zppy" %}
        {% set version = "1.0.0" %}

5. Commit and push your changes.

    ::

        git commit -am 'Changes before release.'
        git push <fork-origin> <branch-name>

6. Create a pull request to the main repo and merge it.

.. _github-release:

Creating A Release On GitHub
----------------------------

1. Go to the Releases on the GitHub repo of the project
`here <https://github.com/E3SM-Project/zppy/releases>`_.
and draft a new release.

2. ``Tag version`` and ``Release title`` should both be the version, including the "v".
(They should match ``git_rev`` in step 4 of the previous section).
``Target`` should be ``main``. Use ``Describe this release`` to write what features
the release adds. You can scroll through
`zppy commits <https://github.com/E3SM-Project/zppy/commits/main>`_ to see
what features have been added recently.

Note that you can also change the branch which you want to release from,
this is specified after the tag (@ Target: ``main``).

The title of a release is often the same as the tag, but you can set it to whatever you want.

Remember to write a description.

3. Click "Publish release".

Releasing The Software On Anaconda
----------------------------------

1. Be sure to have already completed :ref:`Creating A Release On GitHub <github-release>`.
This triggers the CI/CD workflow that handles Anaconda releases.

2. Wait until the CI/CD build is successful. You can view all workflows at `All Workflows <https://github.com/E3SM-Project/zppy/actions>`_.

3. Check the https://anaconda.org/e3sm/zppy page to view the newly updated package.

4. Notify the maintainers of the unified E3SM environment about the new release on the
`E3SM Confluence site <https://acme-climate.atlassian.net/wiki/spaces/WORKFLOW/pages/129732419/E3SM+Unified+Anaconda+Environment>`_.
Be sure to only update the ``zppy`` version number in the correct version(s) of
the E3SM Unified environment. This is almost certainly one of the versions listed under
“Next versions”. If you are uncertain of which to update, leave a comment on the page
asking.

Creating a New Version of the Documentation
-------------------------------------------

1. Be sure to have already completed :ref:`Creating A Release On GitHub <github-release>`.
This triggers the CI/CD workflow that handles publishing documentation versions.

2. Wait until the CI/CD build is successful. You can view all workflows at
`All Workflows <https://github.com/E3SM-Project/zppy/actions>`_.

3. Changes will be available on the
`zppy documentation page <https://e3sm-project.github.io/zppy/>`_.
