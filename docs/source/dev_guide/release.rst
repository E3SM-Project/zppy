How to Prepare a Release
========================

In this guide, we'll cover:

* Preparing the Documentation
* Bumping the Version
* Releasing On GitHub
* Releasing The Software On Anaconda
* Creating a New Version of the Documentation

Preparing the Documentation
---------------------------

1. Checkout a branch

   ::

      git fetch upstream main
      git checkout -b versioned-docs upstream/main

2. Edit ``docs/source/parameters.rst``: in ``https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/default.ini``, replace ``main`` with the hash of the latest commit.
3. Create a pull request to the main repo and merge it. Now, when the next version of the documentation is created (see last part of this page), it will point to the relevant defaults.

Bumping the Version
-------------------

1. Checkout the latest ``main``.
2. Checkout a branch with the name of the version.

    ::

        # Prepend "v" to <version>
        # For release candidates, append "rc" to <version>
        git fetch upstream main
        git checkout -b v<version> upstream/main

3. Bump version using tbump.

    ::

        # Exclude "v" and <version> should match step 2
        # --no-tag is required since tagging is handled in "Releasing on GitHub"
        $ tbump <version> --no-tag

        :: Bumping from 1.0.0 to 1.1.0
        => Would patch these files
        - setup.py:26 version="1.0.0",
        + setup.py:26 version="1.1.0",
        - zppy/__init__.py:1 __version__ = "v1.0.0"
        + zppy/__init__.py:1 __version__ = "v1.1.0"
        - conda/meta.yaml:2 {% set version = "1.0.0" %}
        + conda/meta.yaml:2 {% set version = "1.1.0" %}
        - tbump.toml:5 current = "1.0.0"
        + tbump.toml:5 current = "1.1.0"
        => Would run these git commands
        $ git add --update
        $ git commit --message Bump to 1.1.0
        $ git push origin v1.1.0
        :: Looking good? (y/N)
        >
4. Create a pull request to the main repo and merge it.

.. _github-release:

Releasing on GitHub: release candidates
---------------------------------------

1. Create a tag for the release candidate at https://github.com/E3SM-Project/zppy/tags.

Releasing on GitHub: production releases
----------------------------------------

1. Draft a new release `here <https://github.com/E3SM-Project/zppy/releases>`_.
2. Set `Tag version` to ``v<version>``, **including the "v"**. `@Target` should be ``main``.
3. Set `Release title` to ``v<version>``, **including the "v"**.
4. Use `Describe this release` to summarize the changelog.

   * You can scroll through `zppy commits <https://github.com/E3SM-Project/zppy/commits/main>`_ for a list of changes.

5. Click `Publish release`.
6. CI/CD release workflow is automatically triggered.

Releasing on conda-forge: release candidates
--------------------------------------------

1. Make a PR to `conda-forge <https://github.com/conda-forge/zppy-feedstock/>`_ from your fork of the feedstock. Note that the conda-forge bot does not work for release candidates.

   * Start from the current dev branch and update the version number and the sha256 sum manually.
   * Set the build number back to 0 if needed.
   * Make the dev branch the target of the PR. Then, the package build on conda-forge will end up with the ``e3sm_dev`` label.

2. Check the https://anaconda.org/conda-forge/zppy page to view the newly updated package. Release candidates are assigned the ``e3sm_dev`` label.

Releasing on conda-forge: production releases
---------------------------------------------

1. Be sure to have already completed :ref:`Releasing On GitHub <github-release>`. This triggers the CI/CD workflow that handles Anaconda releases.
2. Wait for a bot PR to come up automatically on conda-forge after the GitHub release. This can happen anywhere from 1 hour to 1 day later.
3. Re-render the PR (see `docs <https://conda-forge.org/docs/maintainer/updating_pkgs.html#rerendering-feedstocks>`_).
4. Merge the PR on conda-forge.
5. Check the https://anaconda.org/conda-forge/zppy page to view the newly updated package. Production releases are assigned the ``main`` label.
6. Notify the maintainers of the unified E3SM environment about the new release on the `E3SM Confluence site <https://acme-climate.atlassian.net/wiki/spaces/WORKFLOW/pages/129732419/E3SM+Unified+Anaconda+Environment>`_.

   * Be sure to only update the ``zppy`` version number in the correct version(s) of the E3SM Unified environment.
   * This is almost certainly one of the versions listed under “Next versions”. If you are uncertain of which to update, leave a comment on the page asking.

Creating a New Version of the Documentation
-------------------------------------------

1. Be sure to have already completed :ref:`Releasing On GitHub <github-release>`. This triggers the CI/CD workflow that handles publishing documentation versions.
2. Wait until the CI/CD build is successful. You can view all workflows at `All Workflows <https://github.com/E3SM-Project/zppy/actions>`_.
3. Changes will be available on the `zppy documentation page <https://e3sm-project.github.io/zppy/>`_.
