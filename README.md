# zppy

**zppy** (pronounced zippee) is a post-processing toolchain for E3SM written
in Python. The goal of zppy is to speed-up the post-processing of E3SM
simulations by automating commonly performed tasks.

[![CI/CD Build Workflow](https://github.com/E3SM-Project/zppy/actions/workflows/build_workflow.yml/badge.svg)](https://github.com/E3SM-Project/zppy/actions/workflows/build_workflow.yml)
[![CI/CD Release Workflow](https://github.com/E3SM-Project/zppy/actions/workflows/release_workflow.yml/badge.svg)](https://github.com/E3SM-Project/zppy/actions/workflows/release_workflow.yml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![flake8](https://img.shields.io/badge/flake8-enabled-green)](https://github.com/PyCQA/flake8)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

See [documentation](https://e3sm-project.github.io/zppy) for more details.

- Run `python -m unittest discover -s tests -p "test_*.py"` to run all tests.
- Run `python -m unittest tests/test_*.py` to run only unit tests.
- Run `python -m unittest tests/integration/test_*.py` to run only integration tests (on server).

## License

Copyright (c) 2021, Energy Exascale Earth System Model Project
All rights reserved

SPDX-License-Identifier: (BSD-3-Clause)

See [LICENSE](./LICENSE) for details

Unlimited Open Source - BSD 3-clause Distribution
`LLNL-CODE-819717`
