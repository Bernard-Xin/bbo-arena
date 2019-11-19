# bbo-arena

## Blackbox optimization libraries/algorithms (under test)
- SMAC -> Working using pysmac (There is a problem with SMACv3 on MacOS)
- [CMA-ES](https://github.com/CMA-ES/pycma) -> CMA-ES doesn't seem to have bounds on the search space and it is designed completely for a continuous search space
- GpyOpt -> Working
- HyperOpt -> Working
- Solid -> StochasticHillClimb, SimulatedAnnealing, TabuSearch(Done), Others (In progress)
- BBopt (Wrapper for Hyperopt and scikit optimize) -> Working

**Other potential algorithms**
Iterated local search
Variable neighborhood search
Guided local search
Kriging Surrogate model ([Model based optimization library in R](https://github.com/mlr-org/mlrMBO))
SVM Surrogate model

**Note on Solid**
Solid hasn't been updated for Python3. However, I am working on an implementation to transition the project to Python3.
Both tabu search and simulated annealing do more function evaluations that the maximum number of steps

## Installation
Since I have included scout repo as a submodule if you clone this repo use

`git clone --recurse-submodules https://github.com/MBtech/bbo-arena.git`

Make sure you have python 3.5.2 or above installed on your system
If you are on mac make sure that you have xcode tools installed using

`xcode-select --install`


`apt-get install swig` or `brew install swig@3` if you are on mac. Make sure you have swig 3 and not version 4.

`pip install cython smac[all] cma gpyopt hyperopt solidpy pysmac bbopt`

## Notes:
Single solution based [metaheuristics methods](https://en.wikipedia.org/wiki/Metaheuristic) are more appropriate for cloud configuration problem

Guided local search is a special case of tabu search.

Hill climbing (with restart) is a case of iterated local search.


## TODO:
- The libraries need to be modified in case of continuous optimization algorithms cases so that same configurations aren't counted twice.
- Fix the max number of step case for tabu search and for SimulatedAnnealing since max steps don't equal max function evaluations.
