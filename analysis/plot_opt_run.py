import seaborn as sns
import json
import pandas as pd
import matplotlib.pyplot as plt
from utils import parseLogs


sns.set(style="whitegrid")
configJsonName = "test_configs/all_runs.json"
config = json.load(open(configJsonName, 'r'))
for system in config["systems"]:
    for app in config["applications"][system]:
        for datasize in config["datasizes"]:
            runtimes = parseLogs(system, app, datasize, configJsonName)
            df = pd.DataFrame(runtimes, columns = ['Algo', 'Budget', 'Runtime', 'Experiment'])
            # stats = df.groupby(['Algo', 'Budget'])['Runtime'].agg(['mean', 'count', 'std'])
            sns.relplot(x='Budget', y='Runtime', hue="Algo", ci="sd", data=df, kind="line")
            # plt.legend(loc='upper right', ncol=3, prop={'size': 8})
            plt.xlim(0, 30)
            plt.show()
