from typing import Any

import yaml


def read_file_yaml(path: str) -> Any:
    with open(path) as file:
        content_yaml = yaml.safe_load(file)
    return content_yaml
