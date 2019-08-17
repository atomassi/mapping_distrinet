![version](https://img.shields.io/badge/version-0.1-blue.svg?cacheSeconds=2592000)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![python](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue.svg?cacheSeconds=2592000)
[![Build Status](https://travis-ci.com/atomassi/mapping_distrinet.svg?token=hrhTT4pN2zzCVx7pvXNv&branch=master)](https://travis-ci.com/atomassi/mapping_distrinet)
[![codecov](https://codecov.io/gh/atomassi/mapping_distrinet/branch/master/graph/badge.svg?token=vkSu7Fw4cq)](https://codecov.io/gh/atomassi/mapping_distrinet) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Installation ##
To install it, make sure you have Python 3.6 or greater installed. Then run
this command from the command prompt:
```python
python setup.py install
```
or
```python
pip install git+https://github.com/atomassi/mapping_distrinet
```


## Supported solvers for the ILP approach ##
* [GLPK] - open-source linear programming.  It can be installed using brew: 
    ```sh 
    brew install glpk
    ```
* [CBC] - COIN-OR CBC: open-source linear programming. It can be installed using brew: 
    ```sh
    brew tap coin-or-tools/coinor
    brew install cbc
    ```
* [Cplex] - free for academic use 
* [Gurobi] - free for academic use
* [SCIP] - free for noncommercial and academic institutes

Installed ILP solvers can be checked by running:
```sh
    pytest check_installed_solvers.py
```


   [Cplex]: <https://www.ibm.com/products/ilog-cplex-optimization-studio>
   [Gurobi]: <http://www.gurobi.com/>
   [GLPK]: <https://www.gnu.org/software/glpk/>
   [CBC]: <https://projects.coin-or.org/Cbc>
   [SCIP]: <https://scip.zib.de/>
   [embedding/solver.py]: https://github.com/atomassi/mapping_distrinet/blob/897abd1a84017b75bb8fd89b65a4619d5f4c7c69/embedding/solve.py#L12

Documentation
---
Documentation is based on Sphinx. In order to build it, follow the following steps:
```python
pip install sphinx sphinx_rtd_theme
cd docs
make html # or make latex
```

Test
---
Tests are based on pytests which can be invoked by running
```sh
pytest
```

