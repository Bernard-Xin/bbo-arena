import seaborn as sns
import json
import pandas as pd
import matplotlib.pyplot as plt
from utils import parseLogs, getBest, getAll, prices
import sys 
import numpy as np
import os
from scipy import stats
from fanova import fANOVA

steps = [6, 12, 18, 24, 30]
# steps = [9, 15, 21, 30]
percentiles = [0.5, 0.95]
sns.set(style="whitegrid")

if len(sys.argv) > 1:
    configJsonName = sys.argv[1]
else:
    configJsonName = "test_configs/all_runs.json"

print(configJsonName)
pd.set_option('display.max_rows', None)
config = json.load(open(configJsonName, 'r'))
prefix = config["prefix"]
scores = dict()
log_dir = config["log_dir"]
value_key = config["value_key"]

# Make sure that the index name is correct for bo case 
algos = list()
for algo in config['bbo_algos']:
    if 'bo' in algo:
        for estimator in config["bo_estimators"]:
            for acq_method in config["bo_acq"][estimator]:
            
                algos.append((algo + '_' + estimator + '_' + acq_method).upper())
    else:
        algos.append(algo.upper())


scores = pd.DataFrame({ 'Algorithms': np.tile(np.repeat(algos, len(percentiles)), len(steps)), 'Score': [0.0]*len(algos)*len(steps)*len(percentiles), 
                    'Budget': np.repeat(steps, len(algos)*len(percentiles) ), 'Percentile': np.tile(percentiles, len(algos)*len(steps) )
                    }).set_index(['Algorithms', 'Budget', 'Percentile'])

slowdown_scores = pd.DataFrame({ 'Algorithms':[], 'Norm. Best Runtime': [], 'Budget': [], 'Percentile': []})

for system in config["systems"]:
    for app in config["applications"][system]:
        for datasize in config["datasizes"]:

            # plt.figure(figsize=(5,3))
            title = system+"_"+app+"_"+datasize
            print(title)

            runtimes = getAll(app, system, datasize, dataset=config["dataset"])
            if len(runtimes) == 0:
                continue
            
            df = pd.DataFrame(runtimes, columns = ['Runtime', 'Num', 'Type', 'Size'])
            df["Cost"] = df.apply(lambda x: (prices[x["Type"] + "." + x["Size"]]/3600.0) * x["Num"] * x["Runtime"] , axis=1)
            # df["Cost"] = (prices[df["Type"] + "." + df["Size"]]/3600.0) * df["Num"] * df["Runtime"] 
            min_runtime = df['Runtime'].min()
            min_cost = df["Cost"].min()

            runtimes = parseLogs(system, app, datasize, configJsonName, logDir=log_dir, value_key=value_key)
            df = pd.DataFrame(runtimes, columns = ['Algorithms', 'Budget', 'Best Runtime', 'Experiment'])
            df_select = df[df['Budget'].isin(steps)]
            df_select['Algorithms'] = df_select['Algorithms'].str.upper()
            # print(df_select)

            total_ranks = pd.DataFrame({'Algorithms':[], 'Budget':[], 'Score':[]})

            workload_slowdown = pd.DataFrame({ 'Algorithms':[], 'Norm. Best Runtime': [], 'Budget': [], 'Percentile': []})

            for budget in steps:

                df_grouped = df_select[df_select['Budget'] == budget].drop(['Budget', 'Experiment'], axis=1).groupby(['Algorithms']) #.describe(percentiles=[0.05, 0.5, 0.95])

                ranks = df_grouped.quantile(percentiles).rank(method='dense')#.reset_index()
                # print(ranks)
                ranks['Budget'] = np.repeat(budget, len(algos)*len(percentiles))
                ranks = ranks.reset_index()#.set_index(['Algorithms', 'Budget'])
                ranks = ranks.rename(columns={'Best Runtime': 'Score', 'level_1': 'Percentile'})
            
                total_ranks = total_ranks.append(ranks)

                s = df_grouped.quantile(percentiles).reset_index()
                s = s.rename(columns={'Best Runtime': 'Score', 'level_1': 'Percentile', 'Best Runtime': 'Norm. Best Runtime'})
                if "Exec. Cost" in config["metric"]:
                    s['Norm. Best Runtime'] = s['Norm. Best Runtime']/min_cost
                else:
                    s['Norm. Best Runtime'] = s['Norm. Best Runtime']/min_runtime 

                s['Budget'] = np.repeat(budget, len(algos)*len(percentiles))
                s['Workload'] =  np.repeat(title, len(algos)*len(percentiles))
                workload_slowdown = workload_slowdown.append(s, ignore_index= True)
            
            slowdown_scores = slowdown_scores.append(workload_slowdown, ignore_index=True)

            for p in percentiles:
                plt.figure(figsize=(4,2.5))
                
                ax = sns.barplot(x='Budget', y='Norm. Best Runtime', hue='Algorithms', data=workload_slowdown[workload_slowdown['Percentile']==p])
                
                h, l = ax.get_legend_handles_labels()
                # print(l)
                if config["legends_outside"]:
                    ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower right", ncol=config["legend_cols"], prop={'size': 10}, handles=h, labels=config["legends"])
                else:
                    ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 10} , handles=h, labels=config["legends"])
                plt.ylim(bottom=1.0)
                plt.ylabel("Norm. Best " + config["metric"])
                dir = 'plots/norm/' + prefix +"/"
                os.makedirs(dir, exist_ok=True)

                plt.savefig(dir + title + '_'+ 'Percentile_'+str(p) + '.pdf', bbox_inches = "tight")
                # plt.show()
                # print(slowdown_scores)
            
            significance_test = pd.DataFrame({ 'algorithm':[], 'statistic': [],'pvalue' : [], 'budget': [], 'test-name': []})
            for budget in steps:
                for algo in algos:
                    if algo in "BO_3_GBRT_PI":
                        continue
                    # print(algo, budget)
                    # print(df_select)
                    X = df_select[(df_select["Algorithms"]=="BO_3_GBRT_PI") & (df_select["Budget"]==budget)]['Best Runtime']
                    Y = df_select[(df_select["Algorithms"]==algo) & (df_select["Budget"]==budget) ]['Best Runtime']
                    # print(X)
                    # print(Y)
                    # print(stats.kruskal(X,Y).pvalue)
                    # print(stats.wilcoxon(X,Y).pvalue)
                    # print(stats.ttest_ind(X, Y).pvalue)

                    significance_test = significance_test.append({ 'algorithm': algo, 'statistic': stats.kruskal(X,Y).statistic, 
                            'pvalue': stats.kruskal(X,Y).pvalue, 'budget': budget, 'test-name': 'kruskal'}, ignore_index=True)
                    significance_test = significance_test.append({ 'algorithm': algo, 'statistic': stats.wilcoxon(X,Y).statistic, 
                            'pvalue': stats.wilcoxon(X,Y).pvalue, 'budget': budget, 'test-name': 'wilcoxon'}, ignore_index=True)
                    significance_test = significance_test.append({ 'algorithm': algo, 'statistic': stats.ttest_ind(X,Y).statistic, 
                            'pvalue': stats.ttest_ind(X,Y).pvalue, 'budget': budget, 'test-name': 't-test'}, ignore_index=True)
            
            significance_test.to_csv('plots/norm/'+ prefix +'/'+ title  + '.csv')
            
            plt.figure(figsize=(4,2.5))
            norm_df = df_select.copy()
            if "Exec. Cost" in config["metric"]:
                norm_df['Norm. Best Runtime'] = norm_df['Best Runtime']/min_cost
            else:
                norm_df['Norm. Best Runtime'] = norm_df['Best Runtime']/min_runtime   

            ax = sns.barplot(x='Budget', y='Norm. Best Runtime', hue='Algorithms', data=norm_df)# , dodge=0.5)
            # ax = sns.boxplot(x='Budget', y='Norm. Best Runtime', hue='Algorithms', data=norm_df)
            h, l = ax.get_legend_handles_labels()
            if config["legends_outside"]:
                ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower right", ncol=config["legend_cols"], prop={'size': 10})
            else:
                ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 10})
            plt.ylim(bottom=1.0)
            plt.ylabel("Norm. Best " + config["metric"])
            dir = 'plots/norm/' + prefix +"/"
            os.makedirs(dir, exist_ok=True)
            plt.savefig(dir + title  + '.pdf', bbox_inches = "tight")
            # plt.show()
            # sys.exit()

            total_ranks = total_ranks.set_index(['Algorithms', 'Budget', 'Percentile'])

            # print(total_ranks)
            # print(scores)
            scores +=  total_ranks
            

            # print(scores+ranks)
                # print(scores[scores['Budget']==budget]['Score'])
                # for t, frame in df_grouped:
                #     stats = frame.describe(percentiles=[0.05, 0.5, 0.95])
                #     print(stats)
                #     print(stats.rank())
                #     # statistics['5%']
                #     print(stats.loc['5%', 'Best Runtime'])
                #     print(stats.loc['50%', 'Best Runtime'])
                    
            
            # stats = df.groupby(['Algo', 'Budget'])['Runtime'].agg(['mean', 'count', 'std'])
            # sns.violinplot(x='Budget', y='Best Runtime', hue="Algorithms", data=df_select, cut=0)

            # sns.boxplot(x='Budget', y='Best Runtime', hue="Algorithms", data=df_select, showfliers=False)
            # best = getBest(app, system, datasize)
            # plt.axhline(best, color='blue')

            # plt.legend(loc='upper right', ncol=3, prop={'size': 7})
            # # plt.savefig('plots/'+prefix+'_'+ title + '.pdf', bbox_inches = "tight")
            # # plt.show()

# print(slowdown_scores.groupby(['Algorithms', 'Budget', 'Percentile']).describe())        

# print(scores)
# print(slowdown_scores)
# # sys.exit()

# for p in percentiles:
#     plt.figure(figsize=(4,2.5))
#     for budget in steps:
#         test = slowdown_scores[(slowdown_scores['Percentile']==p) & (slowdown_scores['Budget']==budget)].set_index(['Workload', 'Budget'])
#         # print(test)
#     slowdown_scores["Budget"] = slowdown_scores["Budget"].astype(int)
#     ax = sns.boxplot(x='Budget', y='Norm. Best Runtime', hue='Algorithms', data=slowdown_scores[slowdown_scores['Percentile']==p], showfliers=False) #
#     h, l = ax.get_legend_handles_labels()
    
#     if config["legends_outside"]:
#         ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower right", ncol=config["legend_cols"], prop={'size': 11}, handles=h, labels=config["legends"])
#     else:
#         ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 11} , handles=h, labels=config["legends"])
#     # ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 10} , handles=h, labels=config["legends"])
#     plt.ylabel("Norm. Best " + config["metric"])
#     dir = 'plots/percentile/'
#     os.makedirs(dir, exist_ok=True)
#     plt.savefig(dir + prefix + '_' + 'Percentile_'+str(p) + '.pdf', bbox_inches = "tight")
#     # plt.show()


# scores = scores.reset_index()
# for p in percentiles:
#     plt.figure(figsize=(4,2.5))
#     scores["Budget"] = scores["Budget"].astype(int)
#     ax = sns.barplot(x='Budget', y='Score', hue='Algorithms', data=scores[scores['Percentile']==p])
#     h, l = ax.get_legend_handles_labels()
#     if config["legends_outside"]:
#         ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower right", ncol=config["legend_cols"], prop={'size': 10}, handles=h, labels=config["legends"])
#     else:
#         ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 10} , handles=h, labels=config["legends"])
#     plt.ylabel("Rank Score")
#     dir = 'plots/scores/'
#     os.makedirs(dir, exist_ok=True)
#     plt.savefig(dir+prefix+'_'+ 'Percentile_'+str(p) + '.pdf', bbox_inches = "tight")
#     # plt.show()

# overall_score = scores.groupby(['Algorithms', 'Budget'])['Score'].sum().reset_index()
# overall_score["Budget"] = overall_score["Budget"].astype(int)
# plt.figure(figsize=(4,2.5))
# ax = sns.barplot(x='Budget', y='Score', hue='Algorithms', data=overall_score)
# h, l = ax.get_legend_handles_labels()
# if config["legends_outside"]:
#     ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower right", ncol=config["legend_cols"], prop={'size': 10}, handles=h, labels=config["legends"])
# else:
#     ax.legend(loc='upper right',  ncol=config["legend_cols"], prop={'size': 10} , handles=h, labels=config["legends"])
# plt.ylabel("Rank Score")
# dir = 'plots/scores/'
# os.makedirs(dir, exist_ok=True)
# plt.savefig(dir+prefix+ '.pdf', bbox_inches = "tight")