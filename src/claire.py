import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from birt import Beta4

from utils.processing.transform import TransformPairwise

PROJECT_DIR = Path.cwd().parent
sys.path.append(str(PROJECT_DIR))
print()


class CLAIRE:
    """CLAIRE applying within an input matrix."""

    def __init__(
        self,
        models_name: List[str],
        models: Dict[str, Any],
        params: Dict[str, Any],
        _X: Dict[str, Any],
        _Y: Dict[str, Any],
        metrics: List[Tuple[str, Callable, bool]],
        dir_result: str,
        path_root: str,
    ):
        """Initialize the CLAIRE.

        Parameters:
        -------------------------------------------------------
            models_name: List of model names.
            models: List of model instances.
            params: Dictionary of parameters for the models.
            _X: Dictionary containing input data.
            _Y: Dictionary containing target labels.
            metrics: List of metrics to calculate.
            dir_result: Output directory to save the results.
            path_root: Root directory for saving the results.
        """
        self.models_name = models_name
        self.models = models
        self.params = params
        self._X = _X
        self._Y = _Y
        self.metrics = metrics
        self.dir_result = dir_result
        self.path_root = path_root

    def transform(self):
        combination_models = TransformPairwise().combination_models(self.models, self.params)
        return combination_models

    def fit_combination_models(self, combination_models: Dict, X_dataset_i: Any) -> Dict:
        """Fit the combination models to the training data.

        Parameters:
        -------------------------------------------------------
            combination_models: List of combination models.
            X_dataset_i: Input data for dataset i.
        """
        for name, model in combination_models.items():
            combination_models[name] = [i_model.fit(X_dataset_i) for i_model in model]
            # model.fit(X_dataset_i)
            # models_fited.append(model)
        return combination_models

    def generate_results(self, data_results: Any) -> pd.DataFrame:
        """Generate the results DataFrame.

        Parameters:
        -------------------------------------------------------
            data_results: Array of model results.

        Returns:
        -------------------------------------------------------
            Results DataFrame.
        """
        self.results = {}
        for name, models in self.models_name.items():
            for idxx, model in enumerate(models):
                if hasattr(data_results[name][idxx], "labels_"):
                    self.results[model] = data_results[name][idxx].labels_
        return pd.DataFrame(self.results)

    def generate_pij_matrix(
        self, data_results: pd.DataFrame, experiment_test: bool = False, works: int = os.cpu_count()
    ) -> pd.DataFrame:
        """Generate the pij matrix.

        Parameters:
        -------------------------------------------------------
            data_results: Results DataFrame.

        Returns:
        -------------------------------------------------------
            pij matrix.
        """
        self._data_results = data_results.copy()
        tp = TransformPairwise(works)
        pij = tp.generate_pij_matrix(self._data_results)

        if not experiment_test:
            pij["average_model"] = pij[pij.filter(regex="^(?!.*random_model_n)", axis=1).columns].mean(axis=1)
            pij["optimal_clustering"] = pij[pij.filter(regex="^(?!.*random_model_n)", axis=1).columns].max(axis=1)
        else:
            pij["average_model"] = pij.mean(axis=1)
            pij["optimal_clustering"] = pij.max(axis=1)

        return pij

    def fit_beta4(self, pij: pd.DataFrame, **kwargs) -> Beta4:
        """Fit the Beta4 model.

        Parameters:
        -------------------------------------------------------
            pij: pij matrix.
            *args: arguments to be passed to the Beta4 class.

        Returns:
        -------------------------------------------------------
            Fitted Beta4 model.
        """
        self.pij = pij
        self.b4 = Beta4(**kwargs)
        self.b4.fit(self.pij.values)
        return self.b4

    def calculate_metrics(
        self,
        data_results: pd.DataFrame,
        models: Beta4,
        X_dataset_i: Any,
        Y_dataset_i: Any,
    ) -> pd.DataFrame:
        """Calculate the evaluation metrics.

        Parameters:
        -------------------------------------------------------
            models: Fitted Beta4 model.
            X_dataset_i: Models response for dataset i.
            Y_dataset_i: Target labels for dataset i.

        Returns:
        -------------------------------------------------------
            Metrics DataFrame.
        """

        data_metrics = pd.DataFrame(index=self.pij.columns, columns=[i[0] for i in self.metrics])

        data_metrics.insert(0, "abilities", models.abilities)
        data_metrics = data_metrics.T

        params_metric = {
            "mood1": {"labels_true": Y_dataset_i},
            "mood2": {"X": X_dataset_i},
        }

        for model in data_metrics.columns:
            for metric in self.metrics:
                if model not in ["optimal_clustering", "average_model"]:
                    if metric[-1]:
                        _params = params_metric["mood1"] | {"labels_pred": data_results[model]}
                    else:
                        _params = params_metric["mood2"] | {"labels": data_results[model]}
                    try:
                        data_metrics.loc[metric[0], model] = metric[1](**_params)
                    except:  # noqa: E722
                        data_metrics.loc[metric[0], model] = np.nan
                else:
                    data_metrics.loc[metric[0], model] = np.nan
        data_metrics = data_metrics.T
        return data_metrics

    def save_results(self, _name: str, data_contents: List[Tuple[str, Any]]) -> None:
        """Save the results to files.

        Parameters:
        -------------------------------------------------------
            _name: Name of the dataset.
            data_contents: List of data to be saved.
        """
        dir_save_dataset_i = self.dir_result / Path(_name)
        url_save_dataset_i = [dir_save_dataset_i / Path(i[0]) for i in data_contents]
        for url in url_save_dataset_i:
            if not os.path.exists(url):
                os.makedirs(url)

        for content, url in zip(data_contents, url_save_dataset_i):
            for data_save in content[1:]:
                if data_save is not None:
                    # print(url / data_save[0])
                    data_save[1].to_csv(url / data_save[0])
