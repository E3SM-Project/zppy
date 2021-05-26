# zppy

**zppy** (pronounced zippee) is a post-processing toolchain for E3SM written 
in Python. The goal of zppy is to speed-up the post-processing of E3SM 
simulations by automating commonly performed tasks.

See [documentation](https://e3sm-project.github.io/zppy) for more details.

Run `python -m unittest discover -s tests -p "test_*.py"` to run all tests.
Run `python -m unittest tests/test_*.py` to run only unit tests.
Run `python -m unittest tests/integration/test_*.py` to run only integration tests (on server)
