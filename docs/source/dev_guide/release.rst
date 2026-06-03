.. _release-zppy:

How to Prepare a Release
========================

This guide covers the full release process for both release candidates (RCs)
and production releases. It includes:

- `Preparing the Documentation`_
- `Bumping the Version`_
- `Releasing on GitHub: production releases`_
- `Releasing on conda-forge: production releases`_
- `Creating a New Version of the Documentation`_

References:

- Release notes are tracked in `GitHub Discussions
  <https://github.com/E3SM-Project/zppy/discussions>`_
- Releases page: https://github.com/E3SM-Project/zppy/releases
- Tags page: https://github.com/E3SM-Project/zppy/tags

Preparing the Documentation
---------------------------

This step is **only required for production releases**, not release
candidates.

1. Checkout a branch:

   .. code-block:: bash

      cd ~/ez/zppy
      git status  # confirm no uncommitted changes
      git fetch upstream main
      git checkout -b prepare-docs-for-<version> upstream/main

2. Update ``docs/source/user_guide/parameters.rst``: find the link to
   ``this release's parameter defaults`` and replace the commit hash in
   the URL with the hash of the latest commit on ``main``. You can find
   this at https://github.com/E3SM-Project/zppy/commits/main.

   Before:
   ::

      See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/<OLD_HASH>/zppy/defaults/default.ini>`_

   After:
   ::

      See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/<NEW_HASH>/zppy/defaults/default.ini>`_

3. Run pre-commit and commit:

   .. code-block:: bash

      conda activate <any-zppy-dev-env>
      pre-commit run --all-files  # should pass
      git add -A
      git commit -m "Update parameter documentation pointer for <version>"
      git push upstream prepare-docs-for-<version>

4. Create a PR, add the **Documentation** label, merge, and delete the
   branch on GitHub.

Bumping the Version
-------------------

Determining the new version number
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Review commits since the last release at
https://github.com/E3SM-Project/zppy/commits/main to determine whether the
bump should be major, minor, or patch:

- **Major** (X.0.0): breaking changes to the user-facing API
- **Minor** (x.Y.0): new features that are backward-compatible
- **Patch** (x.y.Z): bug fixes only

Also update the E3SM Unified package table on `Confluence
<https://e3sm.atlassian.net/wiki/spaces/DOC/pages/129732419/Packages+in+the+E3SM+Unified+conda+environment>`_:

.. code-block:: text

   E3SM Unified <NEW_UNIFIED_VERSION>: zppy v<NEW_ZPPY_VERSION>

.. _release-candidates:

Release candidates (zppy repo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Checkout a branch named after the new version:

   .. code-block:: bash

      cd ~/ez/zppy
      git status  # confirm no uncommitted changes
      git fetch upstream main
      git checkout -b v<version>rc<N> upstream/main
      git log --oneline | head -n 3
      # Verify matches https://github.com/E3SM-Project/zppy/commits/main

2. Bump the version using ``tbump``:

   .. code-block:: bash

      conda activate <any-zppy-dev-env>  # must have tbump installed
      tbump <version>rc<N> --no-tag
      # "Error: Command `git push upstream main` failed" is expected
      # (we are not on main)

3. Push and create a PR:

   .. code-block:: bash

      git push upstream v<version>rc<N>

   Create a PR, add the **Update version** label, merge, and delete the
   branch on GitHub.

4. Create the tag on ``main``:

   .. code-block:: bash

      git checkout main
      git fetch upstream
      git reset --hard upstream/main
      git tag -a v<version>rc<N> -m "v<version>rc<N>"
      # Delete the local branch first (avoids push conflicts)
      git branch -D v<version>rc<N>
      git push upstream v<version>rc<N>

   The tag will appear on https://github.com/E3SM-Project/zppy/tags but
   **not** on Releases. This is expected for RCs.

Production releases (zppy repo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Complete `Preparing the Documentation`_ first.

2. Checkout a branch:

   .. code-block:: bash

      cd ~/ez/zppy
      git status  # confirm no uncommitted changes
      git fetch upstream main
      git checkout -b v<version> upstream/main
      git log --oneline | head -n 3

3. Bump the version:

   .. code-block:: bash

      tbump <version> --no-tag
      # "Error: Command `git push upstream main` failed" is expected
      git push upstream v<version>

4. Create a PR, compare the diff against the last RC's bump PR to verify
   correctness, add the **Update version** label, wait for CI checks to
   pass, merge, and delete the branch.

.. _github-release:

Releasing on GitHub: release candidates
-----------------------------------------

See the tagging step above in `Release candidates (zppy repo)`_. RC tags
appear on Tags but not on Releases.

Releasing on GitHub: production releases
------------------------------------------

1. Go to https://github.com/E3SM-Project/zppy/releases and click **Draft a
   new release**.
2. Set **Tag version** to ``v<version>`` (include the ``v``). Set
   **@ Target** to ``main``.
3. Set **Release title** to ``v<version>`` (include the ``v``).
4. Write the release description:

   - **Summary of changes**: a high-level summary of what changed
   - **Full list of changes**: categorized log of commits, organized by
     type (new features, bug fixes, documentation, etc.)

   You can use https://github.com/E3SM-Project/zppy/commits/main to find
   all commits since the last release.

5. Ensure **Set as the latest release** is checked.
6. Click **Publish release**.

   - The CI/CD release workflow is automatically triggered. It publishes
     new docs and, for conda-forge, triggers a bot PR.
   - Unlike RCs, the production version now appears on both
     `Tags <https://github.com/E3SM-Project/zppy/tags>`_ and
     `Releases <https://github.com/E3SM-Project/zppy/releases>`_.

Releasing on conda-forge: release candidates
---------------------------------------------

The conda-forge bot does **not** handle RCs automatically. Do this manually:

1. If you don't have a local clone of the feedstock:

   .. code-block:: bash

      git clone git@github.com:conda-forge/zppy-feedstock.git
      git remote add upstream git@github.com:conda-forge/zppy-feedstock.git

2. If you don't have a fork, create one on
   https://github.com/conda-forge/zppy-feedstock, then:

   .. code-block:: bash

      git remote add <your-fork-name> <SSH path for your fork>

3. Get the sha256 hash of the RC tarball:

   .. code-block:: bash

      curl -sL https://github.com/E3SM-Project/zppy/archive/v<version>rc<N>.tar.gz | openssl sha256

4. Make changes on a branch:

   .. code-block:: bash

      git fetch upstream dev
      git checkout -b v<version>rc<N> upstream/dev

   In ``recipe/recipe.yaml`` (or ``recipe/meta.yaml`` if it still exists),
   update:

   .. code-block:: yaml

      version: <version>rc<N>
      sha256: <hash-from-step-3>
      number: 0  # build number should always be 0 for a new version

   Also update any changed dependencies (compare
   ``https://github.com/E3SM-Project/zppy/compare/v<LAST>...v<NEW>``
   for changes in ``dev.yml`` or ``pyproject.toml``).

   .. code-block:: bash

      git add -A
      git commit -m "v<version>rc<N>"
      git push <your-fork-name> v<version>rc<N>

5. Open a PR from your fork to the ``dev`` branch of
   https://github.com/conda-forge/zppy-feedstock. RC packages get the
   ``zppy_dev`` label.

6. After merging and CI completes, check
   https://anaconda.org/conda-forge/zppy for the new package (allow ~15
   minutes for mirroring).

Releasing on conda-forge: production releases
---------------------------------------------

1. Complete :ref:`Releasing On GitHub <github-release>` first. This
   triggers the CI/CD workflow that opens the bot PR on conda-forge.

2. Wait for the bot PR at https://github.com/conda-forge/zppy-feedstock/pulls
   (can take 1 hour to 1 day). Alternatively, post an issue with
   ``@conda-forge-admin, please update version``.

3. Complete any requirements to merge the PR (re-render if requested, etc.).

4. Check https://anaconda.org/conda-forge/zppy/files to confirm the new
   package has the ``main`` label.

5. Notify maintainers of the E3SM Unified environment on the `Confluence
   packages page
   <https://e3sm.atlassian.net/wiki/spaces/WORKFLOW/pages/129732419/E3SM+Unified+Anaconda+Environment>`_
   about the new release. Update the version number for the correct E3SM
   Unified version(s) under "Next versions".

Creating a New Version of the Documentation
-------------------------------------------

1. Complete :ref:`Releasing On GitHub <github-release>`. This triggers
   the CI/CD release workflow, which publishes new versioned docs.

2. Wait for the CI/CD build to succeed at
   https://github.com/E3SM-Project/zppy/actions.

3. Verify the documentation is available at
   https://docs.e3sm.org/zppy/_build/html/main/

4. Check that the "parameter defaults" link on the parameters page points
   to the correct commit hash (should match the commit before "Update
   parameter documentation pointer" on
   https://github.com/E3SM-Project/zppy/commits/main).

Extra Resources
---------------

- Conda-forge docs: https://conda-forge.org/docs/user/introduction.html
- Admin web services: https://conda-forge.org/docs/maintainer/infrastructure.html#admin-web-services
- E3SM Anaconda release guide: https://acme-climate.atlassian.net/wiki/spaces/IPD/pages/3616735236/Releasing+E3SM+Software+on+Anaconda+conda-forge+channel
