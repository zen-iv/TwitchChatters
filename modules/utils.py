import yaml
import os
from dataclasses import dataclass

@dataclass
class Personality:
    name: str
    system_prompt: str
    background: str
    examples: str
    response_params: dict

@dataclass
class AccountConfig:
    username: str
    oauth: str
    channel: str
    personality: str

def load_config(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    def replace_env_vars(data):
        if isinstance(data, dict):
            return {k: replace_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [replace_env_vars(i) for i in data]
        if isinstance(data, str) and data.startswith("${"):
            return os.getenv(data[2:-1])
        return data

    config = replace_env_vars(config)

    config['personalities'] = {
        char['name']: Personality(
            name=char['name'],
            system_prompt=char['system_prompt'],
            background=char['background'],
            examples=char['examples'],
            response_params=char['response_params']
        ) for char in config['characters']
    }

    return config
