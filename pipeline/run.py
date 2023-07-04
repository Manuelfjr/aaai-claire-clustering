import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_DIR = Path.cwd()
sys.path.append(str(PROJECT_DIR))
warnings.filterwarnings("ignore")
print(PROJECT_DIR)
from src.claire import CLAIRE
from utils import config
from utils.reader import read_file_yaml

np.random.seed(0)

under_line = "\n{}\n"
title_part_n2 = "PROJECT_DIR: [ {} ]".format(PROJECT_DIR)
title_part_n3 = under_line.format("".join(["-"] * len(title_part_n2)))
title_part_n1 = under_line.format("".join(["-"] * len(title_part_n2)))
print(title_part_n1 + title_part_n2 + title_part_n3)

##### parameters #################################
path_root = PROJECT_DIR / "data"
path_conf = PROJECT_DIR / "conf"
file_path_parameters = path_conf / "parameters.yml"
path_data = [path_root / i for i in config.file_names]

##### read       ##################################
parameters = read_file_yaml(file_path_parameters)
data_all = {i: pd.read_csv(path_data[idx] / Path(i + ".csv")) for idx, i in enumerate(config.file_names)}

#### running     ##################################
_X, _Y = {}, {}

for i in data_all.keys():
    _X[i] = data_all[i].drop("labels", axis=1).values
    _Y[i] = data_all[i]["labels"].values

#### select if it is random include simulation ####
if parameters["include_random_model"]:
    number_random_models = len(np.unique(list(config.models_name_dataset.values())[0]))
else:
    number_random_models = 1
path_result = Path(config.dir_result)
try:
    del config.params["optics"]
except:
    t = -1

step_pause = 0
for k_random in tqdm(range(number_random_models)):
#     if k_random > 0:
#         break
    which_k_random = "n_random_model: [ {} ]".format(k_random+1)
    print(title_part_n1 + which_k_random + title_part_n3)
    if (number_random_models != 1):
        path_result = path_result / Path(f"random_n{k_random+1}")
        if not os.path.exists(PROJECT_DIR / path_result):
            os.makedirs(path_result)
    
    for i in tqdm(config.file_names):
        models_params = (
            config
            .params|{
                "optics": [
                   config._optics_params[i]
                ]
            }
        )
        claire = CLAIRE(
            models_name = np.unique(config.models_name_dataset[i]),
            models = config.models,
            params = models_params,
            _X = _X, 
            _Y = _Y,
            metrics = config.metrics,
            dir_result = path_result,
            path_root = PROJECT_DIR,
        )

        if len(np.unique(_Y[i])) == 1:
            n_clusters = np.random.randint(0, 10)
        else:
            n_clusters = len(np.unique(_Y[i]))
        
        which_k_dataset = "dataset: [ {} ]".format(i)
        print(title_part_n1 + which_k_dataset + title_part_n3)
        #  processing
        combination_models = claire.transform()
        claire.fit_combination_models(combination_models, _X[i])

        data_results = claire.generate_results(combination_models)
        pij = claire.generate_pij_matrix(
            data_results,
            k_random + 1,
            n_clusters
        )

        # set beta4 params
        beta_params = parameters["beta_params"]|{
                "pij": pij, 
                "n_respondents": pij.shape[1],
                "n_items": pij.shape[0]
            }

        # fit
        beta4_model = claire.fit_beta4( **beta_params )

        # metrics
        data_metrics = claire.calculate_metrics(
            data_results,
            beta4_model, 
            claire._X[i],
            claire._Y[i]
        )

        # contents
        dir_contents = [
            (
                "metrics",
                (
                    "metrics.csv",
                    data_metrics.sort_values("abilities", ascending = False),
                ),
                (None),
            ),
            (
                "pij",
                ("pij_true.csv", pij),
                ("pij_pred.csv", pd.DataFrame(claire.b4.pij,
                                              columns = pij.columns)
                ),
            ),
            (
                "params",
                (
                    "abilities.csv",
                    pd.DataFrame(
                        claire.b4.abilities, index = pij.columns, columns = ["abilities"]
                    ),
                ),
                (
                    "diff_disc.csv",
                    pd.DataFrame(
                        {
                            "difficulty": claire.b4.difficulties,
                            "discrimination": claire.b4.discriminations,
                        }
                    ),
                ),
            ),
            ("labels", ("labels.csv", data_results), (None))
        ]

        # save
        claire.save_results(i, dir_contents)
    path_result = Path(config.dir_result)
