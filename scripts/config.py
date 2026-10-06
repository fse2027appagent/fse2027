import os
import yaml


def load_config(config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    configs = dict(os.environ)
    with open(config_path, "r") as file:
        yaml_data = yaml.safe_load(file)
    configs.update(yaml_data)
    for key in ["MODEL_PATH", "TASK_STEPS_PATH", "APP_DESC_PATH"]:
        if key in configs and configs[key]:
            configs[key] = os.path.expanduser(configs[key])
    return configs
