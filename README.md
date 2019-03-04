## Installing requirements ##
```sh
pip install -r requirements.txt
```
## Running the code ##
```sh
python3 reconfiguration/main.py
```
## Testing which _get_solver is currently installed ##
```sh
python3 reconfiguration/test.py
```

## Solvers for the ILP approach ##
* [Cplex] - free for academic use 
* [Gurobi] - free for academic use
* [GLPK] - open-source linear programming _get_solver
* [CBC] - COIN-OR CBC: open-source linear programming _get_solver
* [SCIP] - free for noncommercial and academic institutes

## Adding a mapping algorithm ##
A new algorithm can be added by creating a new class which inherits from the class *Solve* (in [embedding/solve.py]) and defining a **\_\_call\_\_** method in the class.

   [Cplex]: <https://www.ibm.com/products/ilog-cplex-optimization-studio>
   [Gurobi]: <http://www.gurobi.com/>
   [GLPK]: <https://www.gnu.org/software/glpk/>
   [CBC]: <https://projects.coin-or.org/Cbc>
   [SCIP]: <https://scip.zib.de/>
   [embedding/solve.py]: https://github.com/atomassi/mapping_distrinet/blob/897abd1a84017b75bb8fd89b65a4619d5f4c7c69/embedding/solve.py#L12
