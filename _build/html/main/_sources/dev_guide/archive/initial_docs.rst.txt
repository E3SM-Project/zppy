**********************************
How to set up new documentation
**********************************

.. warning::
  The instructions below only apply for the initial configuration of the
  Sphinx documentation on the Github repository. They are documented here
  for reference only. Do not follow them unless you are setting up documentation
  for a new repository. (Adapted from `Sphinx documentation on GitHub
  <http://datadesk.latimes.com/posts/2012/01/sphinx-on-github>`_.)

Create Sphinx conda environment (see above).

Create a new git branch (gh-pages): ::

  $ git branch gh-pages
  $ git checkout gh-pages

Clear out any­thing from the main branch and start fresh ::

  $ git symbolic-ref HEAD refs/heads/gh-pages
  $ rm .git/index
  $ git clean -fdx

Create documentation ::

  $ sphinx-quickstart

accept suggested default options, except ::

  Separate source and build directories (y/N) [n]: y

Edit Makefile and change ``BUILDDIR`` ::

  BUILDDIR = docs

Remove old build directory ::

  $ rmdir build

Change the Sphinx theme to 'ReadTheDocs'. Edit 'source/conf.py and change ::

  html_theme = 'alabaster'

to ::

  import sphinx_rtd_theme
  html_theme = "sphinx_rtd_theme"
  html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

Try building documentation ::

  $ make html

Create an empty .nojekyll file to indicate to GitHub.com that this
is not a Jekyll static website: ::

  $ touch .nojekyll

Create a top-level re-direction file: ::

  $ vi index.html

with the following: ::

  <meta http-equiv="refresh" content="0; url=./docs/html/index.html" />

Commit and push back to GitHub: ::

  $ git add .
  $ git commit
  $ git push origin gh-pages