.. _production_releases:

Preparing a production release
==============================

Step 1: Testing
---------------

Be sure to run the entire integration test suite before making a production release.

Step 2: Confluence
------------------

This step should already have been completed during the release-candidate phase, however it is good practice to double check that the `E3SM Unified version tracking page <https://e3sm.atlassian.net/wiki/spaces/DOC/pages/129732419/Packages+in+the+E3SM+Unified+conda+environment>`_ has had the next E3SM Unified version updated with the new ``zppy`` version number.

Step 3: Prepare documentation
------------------------------------------

Similar to the release-candidate directions, we'll use ``v1.2.3`` as an example verison number here.

   .. code-block:: bash

        cd zppy
        git status # Confirm there's no uncommitted changes
        git fetch upstream main # This assumes you've named your remote for the main repo as "upstream"
        git checkout -b prepare-docs-for-1.2.3 upstream/main


Change the "this release's parameter defaults" link on the Parameters documentation page (``docs/source/user_guide/parameters.rst``) to refer to the latest commit's hash. See `zppy commits <https://github.com/E3SM-Project/zppy/commits/main>`_ to find the latest commit.

   .. code-block:: bash

        git add -A
        conda activate env-name # Activate any zppy dev environment you have; we just need the pre-commit hooks
        conda activate env-name
        pre-commit run --all-files
        git commit -m "Update parameter documentation pointer for v1.2.3"
        git push upstream prepare-docs-for-1.2.3


Create a PR, mark yourself as assignee, add the Documentation label, merge the PR and delete the GitHub branch.

Step 4: tbump
-------------

   .. code-block:: bash

    # On Perlmutter
    cd zppy
    git status # Confirm there's no uncommitted changes
    git fetch upstream main # This assumes you've named your remote for the main repo as "upstream"
    git checkout -b v1.2.3 upstream/main
    git log --oneline | head -n 5
    # Check that the latest commits match what's on https://github.com/E3SM-Project/zppy/commits/main/
    tbump 1.2.3 --no-tag
    # This creates a commit, but won't push it (because the branch isn't named `main`)
    git push upstream v1.2.3
    # Create, and "Update version" label" to, and merge the PR; delete the branch on GitHub

Step 5: Make the release on the zppy repo
-----------------------------------------

1. Draft a new release `here <https://github.com/E3SM-Project/zppy/releases>`_. Click "Draft a new release".
2. Set Tag version to ``v1.2.3``, including the “v”. ``@Target`` should be ``main``. Click "Tag", then "Create new tag" and enter "v.1.2.3"
3. Set Release title to ``v1.2.3``, including the “v”.
4. Use "Describe this release" to summarize the changelog. Write two sections: "Summary of changes" (the high-level summary) & "Full list of changes" (the categorized list of commits, from reviewing the `zppy commits <https://github.com/E3SM-Project/zppy/commits/main>`_)
5. Make sure "Set as the latest release" is checked.
6. Click "Publish release". Unlike the RCs, `v1.2.3` should now appear on _both_ `Tags <https://github.com/E3SM-Project/zppy/tags>`_ and `Releases <https://github.com/E3SM-Project/zppy/releases>`_.
7. CI/CD release workflow will be automatically triggered. The docs workflow is just for the docs. Clicking "Publish release" is responsible for triggering the bot PR on conda-forge.

Step 6: zppy-feedstock repo
---------------------------

1. Wait for a bot PR to come up automatically on conda-forge after the GitHub release. This can happen anywhere from 1 hour to 1 day later. Check https://github.com/conda-forge/zppy-feedstock/pulls. (Alternative: open an issue with the bot command: ``@conda-forge-admin, please update version``` and the PR will opened). 
2. Complete any requirements to merge the PR.
3. Check the https://anaconda.org/conda-forge/zppy/files/manage page to view the newly updated package. Check it has the `main` label.

Step 7: Check the docs
----------------------

Wait for the docs workflow to complete successfully. Then go to https://docs.e3sm.org/zppy/_build/html/main/user_guide/parameters.html, and click on "this release’s parameter defaults". That should take you the code at the hash as of the latest commit.
