import json
import yaml


def json_load(file_path):
    with open(file_path) as fs:
        return json.load(fs)


def json_dump(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as fs:
        json.dump(data, fs, indent=2, ensure_ascii=False)
        return None


def yaml_load(file_path):
    print(file_path)
    with open(file_path) as fs:
        return yaml.load(fs, Loader=yaml.FullLoader)


def yaml_dump(data, file_path):
    with open(file_path, 'w') as fs:
        yaml.dump(data, fs)
        return None
