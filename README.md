![version](https://img.shields.io/badge/version-0.1-blue.svg?cacheSeconds=2592000)
[![Build Status](https://travis-ci.com/atomassi/mapping_distrinet.svg?token=hrhTT4pN2zzCVx7pvXNv&branch=master)](https://travis-ci.com/atomassi/mapping_distrinet)


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
* [Cplex] - free for academic use 
* [Gurobi] - free for academic use
* [GLPK] - open-source linear programming _get_solver
* [CBC] - COIN-OR CBC: open-source linear programming _get_solver
* [SCIP] - free for noncommercial and academic institutes



   [Cplex]: <https://www.ibm.com/products/ilog-cplex-optimization-studio>
   [Gurobi]: <http://www.gurobi.com/>
   [GLPK]: <https://www.gnu.org/software/glpk/>
   [CBC]: <https://projects.coin-or.org/Cbc>
   [SCIP]: <https://scip.zib.de/>
   [embedding/solver.py]: https://github.com/atomassi/mapping_distrinet/blob/897abd1a84017b75bb8fd89b65a4619d5f4c7c69/embedding/solve.py#L12
