# basics
import argparse
import os
import sys
from pathlib import Path

PROJECT_DIR = Path.cwd()
sys.path.append(str(PROJECT_DIR))

from typing import Any

import config
import numpy as np
import pandas as pd

# utils
from reader import read_file_yaml
from sklearn import datasets
from sklearn.datasets import (
    load_breast_cancer,
    load_diabetes,
    load_digits,
    load_iris,
    load_wine,
)
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# basics

file_path_parameters = PROJECT_DIR / "conf" / "parameters.yml"
np.random.seed(0)

# args
parser = argparse.ArgumentParser(description="Process config")
parser.add_argument(
    "integers",
    metavar="N_SAMPLE",
    type=int,
    nargs="?",
    default=[500],
    help="an integer for length of the dataset generated.",
)
parser.add_argument(
    "object",
    metavar="PATH",
    type=str,
    nargs="?",
    default=[file_path_parameters],
    help=f"file path to parameters configuration. (default: {file_path_parameters})",
)
parser.add_argument(
    "random_state",
    metavar="RANDOM_STATE",
    type=int,
    nargs="?",
    default=170,
    help="set random_state for data generation (default: 170)",
)
args = parser.parse_args()

# ============
# read parameters
parameters = read_file_yaml(file_path_parameters)
ext_type = parameters["outputs"]["extension_type"]

_params_dataset = {
    i_name: {
        "params": i_content,
    }
    for i_name, i_content in parameters["generation_params"].items()
}
# ============

# ============
# Generate datasets. We choose the size big enough to see the scalability
# of the algorithms, but not too big to avoid too long running times
# ============
content = {}
noisy_circles = datasets.make_circles(n_samples=args.integers, **_params_dataset["noisy_circles"]["params"])
noisy_moons = datasets.make_moons(n_samples=args.integers, **_params_dataset["noisy_moons"]["params"])
blobs = datasets.make_blobs(n_samples=args.integers, **_params_dataset["blobs"]["params"])
no_structure = np.random.rand(*_params_dataset["no_structure"]["params"]), None

# Anisotropicly distributed data
X, y, *others = datasets.make_blobs(n_samples=args.integers, random_state=args.random_state)
rotation = _params_dataset["aniso"]["params"]["rotation"]
X_aniso = np.dot(X, rotation)
aniso = (X_aniso, y)

# blobs with varied variances
varied = datasets.make_blobs(
    n_samples=args.integers, random_state=args.random_state, **_params_dataset["varied"]["params"]
)
####################### real data
# iris
_iris = load_iris()
_pca_iris = PCA(2).fit_transform(_iris["data"])
_pca_iris = _pca_iris, _iris["target"]
iris = _iris["data"], _iris["target"]

# diabetes
_diabetes = load_diabetes()
_pca_diabetes = PCA(2).fit_transform(_diabetes["data"])
_pca_diabetes = _pca_diabetes, _diabetes["target"]
diabetes = _diabetes["data"], _diabetes["target"]

# wine
_wine = load_wine()
_pca_wine = PCA(2).fit_transform(_wine["data"])
_pca_wine = _pca_wine, _wine["target"]
wine = _wine["data"], _wine["target"]

# digits
_digits = load_digits()
_pca_digits = PCA(2).fit_transform(_digits["data"])
_pca_digits = _pca_digits, _digits["target"]
digits = _digits["data"], _digits["target"]

# cancer
_cancer = load_breast_cancer()
_pca_cancer = PCA(2).fit_transform(_cancer["data"])
_pca_cancer = _pca_cancer, _cancer["target"]
cancer = _cancer["data"], _cancer["target"]
#######################

# organize content
content = {
    "aniso": (aniso, (None, None)),
    "noisy_circles": (noisy_circles, (None, None)),
    "noisy_moons": (noisy_moons, (None, None)),
    "blobs": (blobs, (None, None)),
    "varied": (varied, (None, None)),
    "no_structure": (no_structure, (None, None)),
    "iris": (iris, _pca_iris),
    "diabetes": (diabetes, _pca_diabetes),
    "wine": (wine, _pca_wine),
    "digits": (digits, _pca_digits),
    "breast_cancer": (cancer, _pca_cancer),
}

content = {i: content[i] for i in config.file_names}

_datasets = {
    i_name: {
        "content": content[i_name],
    }
    for i_name in config.file_names
}

dataset_std = []
data = {}


def transform_and_input_target(URL: Any, i_name: str, X: Any, y: Any, data: dict):
    X = StandardScaler().fit_transform(X)
    if not os.path.exists(URL):
        os.makedirs(URL)
    data[i_name] = pd.DataFrame(X)
    data[i_name]["labels"] = y
    return data[i_name]


for i_name, args in _datasets.items():
    URL = PROJECT_DIR / "data" / i_name
    (X, y), (X_pca, y_pca) = args["content"]
    if (X_pca is None) and (y_pca is None):
        data[i_name] = transform_and_input_target(URL, i_name, X, y, data)
        data[i_name].to_csv(URL / Path(i_name + ext_type), index=False)
    else:
        data[i_name] = transform_and_input_target(URL, i_name, X_pca, y_pca, data)
        data[i_name].to_csv(URL / Path(i_name + "_pca" + ext_type), index=False)
