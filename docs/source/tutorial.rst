
Main Purpose
-----------------------------

TODO

Prerequisites
-----------------------------

This project assumes you have ``python3.6+`` installed.

To install dependencies you need to run the following command:

.. code-block:: python

   pip install -r requirements.txt


You also need to have installed at least **an ILP Solver**.

Currently, 5 ILP Solvers are supported:


-  GLPK_ - open-source linear programming: It can be installed using brew:

.. code-block:: shell

    brew install glpk

-  CBC_ - COIN-OR CBC: open-source linear programming. It can be installed using brew:

.. code-block:: shell

    brew tap coin-or-tools/coinor
    brew install cbc

-  SCIP_ - free for noncommercial and academic institutes
-  Cplex_ - commercial

-  Gurobi_ - commercial


.. _GLPK: https://www.gnu.org/software/glpk/
.. _CBC: <https://projects.coin-or.org/Cbc
.. _Cplex: <https://www.ibm.com/products/ilog-cplex-optimization-studio
.. _Gurobi: <http://www.gurobi.com/
.. _SCIP: <https://scip.zib.de/>



Quickstart
----------

TODO

To run unit tests:

.. code-block:: shell

   pytest

To build documentation:

.. code-block:: shell

   make html

or

.. code-block:: shell

   make latex

To this end, you need to install both ``sphinx`` and the pip install ``sphinx_rtd_theme theme``.

.. code-block:: python

   pip install sphinx sphinx_rtd_theme
