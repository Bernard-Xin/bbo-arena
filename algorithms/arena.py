import sys
from lhssearch import *
from randsearch import *
from tpe import *
from boskopt import boSkOpt
from hillclimbing import hcOpt
from simulatedannealing import saOpt
import json
import os
import time
from joblib import Parallel, delayed
from utils import *

def generate_init_samples(types, sizes, number_of_nodes, budget, seed):
    init_samples = []
    count = 0
    np.random.seed(seed)
    while count < budget:
        parameters = {}
        parameters['type'] = np.random.choice(types)
        parameters['size'] = np.random.choice(sizes)
        parameters['num'] = int(np.random.choice(number_of_nodes[parameters['size']]))
        if parameters in init_samples:
            continue
        init_samples.append(parameters)
        count +=1
    return init_samples

def get_existing_experiments(filename, dir='hyperparam/'):
    os.makedirs(dir, exist_ok=True)
    data = dict()
    # print(filename)
    if os.path.isfile(dir+filename):
        try:
            data = json.load(open(dir+filename, 'r'))
        except:
            print("JSON file corruption: " + dir+filename)
            sys.exit()
    else:
        data['experiments'] = []
    
    return len(data['experiments'])

def getResults(search, filename, config, dir='hyperparam/'):
    os.makedirs(dir, exist_ok=True)
    log = config['log']

    results = search.runOptimizer()
    data =dict()
    # print(results)
    if os.path.isfile(dir+filename):
        data = json.load(open(dir+filename, 'r'))
    else:
        data['experiments'] = []
    # print(results)
    data['experiments'].append(results['trials'])

    if log:
        json.dump(data, open(dir+filename, 'w'), indent=4)

def callBO(system, app, datasize, algo, budget, parent_dir, types, sizes, number_of_nodes, config, estimator, 
                                                acq_method, filename, objective_function, n_initial_samples, seeds,
                                                acq_func_kwargs):
    new_filename = filename + '_' + estimator + '_' + acq_method
    print(new_filename)
    if get_existing_experiments(new_filename) >= config["num_of_runs"]:
        print(get_existing_experiments(new_filename))

    for i in range(get_existing_experiments(new_filename), config["num_of_runs"]):
        points_to_evaluate = generate_init_samples(types, sizes, number_of_nodes, config["initial_samples"], seeds[i])
        search = boSkOpt(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function, 
                            points_to_evaluate=points_to_evaluate ,optimizer=estimator, 
                            initial_samples=n_initial_samples, acquisition_method=acq_method, acq_kwargs=acq_func_kwargs)
        getResults(search, new_filename, config)


def callOptimizer(system, app, datasize, algo, budget, parent_dir, types, sizes, number_of_nodes, config):
    filename = system + '_' + app + '_' + datasize + '_' + algo
    print(filename)
    seeds = range(0, config["num_of_runs"]+1)
    # n_initial_samples = config["initial_samples"]
    n_initial_samples = 0

    if "bo" in algo:
        Parallel(n_jobs=nJobs)(delayed(callBO)(system, app, datasize, algo, budget, parent_dir, types, sizes, \
                number_of_nodes, config, estimator, acq_method, filename, objective_function, n_initial_samples, seeds, config["bo_args"])
                    for estimator in config["bo_estimators"] for acq_method in config["bo_acq"][estimator])
        return

    if get_existing_experiments(filename) >= config["num_of_runs"]:
        print(get_existing_experiments(filename))

    for i in range(get_existing_experiments(filename), config["num_of_runs"]):
        points_to_evaluate = generate_init_samples(types, sizes, number_of_nodes, config["initial_samples"], seeds[i])
        if algo == "lhs":
            search = lhsSearch(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function)
        elif algo == "random":
            search = randSearch(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function, seeds[i])
        elif algo == "random2x":
            search = randSearch(app, system, datasize, 2*budget, parent_dir, types, sizes, number_of_nodes, objective_function)
        elif "tpe" in algo:
            search = tpeOptimizer(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function, \
                                points_to_evaluate=points_to_evaluate,
                                initial_samples=n_initial_samples, gamma=config["tpe_args"]["gamma"])

        elif "hc" in algo:
            search = hcOpt(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function, \
                        points_to_evaluate=points_to_evaluate,
                        initial_samples=n_initial_samples, temp=config["sa"]["temp"])
        elif "sa" in algo:
            search = saOpt(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes, objective_function, \
                        points_to_evaluate=points_to_evaluate,
                        initial_samples=n_initial_samples, temp=config["sa"]["temp"], schedule_constant=config["sa"]["schedule_constant"])

        else:
            print("Algorithm not found")


        if "bo" not in algo:
            getResults(search, filename, config)




# python arena.py config/config.json runtime|cost
config = json.load(open(sys.argv[1], 'r'))
objective = sys.argv[2]

objective_function = getExecutionTime
if "cost" in objective:
    objective_function = getExecutionCost

budget = config["budget"]
nJobs = 1

# for system in config["systems"]:
#     for app in config["applications"][system]:
#         for datasize in config["datasizes"]:
#             for algo in config["bbo_algos"]:
#                 callOptimizer(system, app, datasize, algo, budget, parent_dir, types, sizes, number_of_nodes, config) 
                                                

Parallel(n_jobs=9)(delayed(callOptimizer)(system, app, datasize, algo, budget, parent_dir, types, sizes, number_of_nodes, config) 
                for system in config["systems"] for app in config["applications"][system] for datasize in config["datasizes"] for algo in config["bbo_algos"] )


# search = boGPyOpt(app, system, datasize, budget, parent_dir, types, sizes, number_of_nodes)
