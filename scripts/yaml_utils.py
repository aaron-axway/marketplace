import yaml
from copy import deepcopy
from glob import glob
import os
from collections import OrderedDict
import base64
from yaml.dumper import SafeDumper


class FoldedScalarString(str):
    pass


def folded_scalar_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")


def update_icon_in_yaml(data, image_path):
    # Read the image and base64-encode it
    with open(image_path, "rb") as f:
        encoded_str = base64.b64encode(f.read()).decode("utf-8")

    # Construct the data URI
    data_uri = f"data:image/png;base64,{encoded_str}"
    data["icon"] = FoldedScalarString(data_uri)


def ordered_dump(data, stream=None, Dumper=yaml.SafeDumper, **kwds):
    Dumper.add_representer(FoldedScalarString, folded_scalar_representer)

    class OrderedDumper(Dumper):

        def increase_indent(self, flow=False, indentless=False):
            return super(OrderedDumper, self).increase_indent(flow, False)

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

    def _list_representer(dumper, data):
        return dumper.represent_sequence(yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, data, flow_style=False)

    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    OrderedDumper.add_representer(list, _list_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


class DuplicateKeyError(Exception):
    pass


def check_duplicate_keys(loader, node, deep=False):
    mapping = OrderedDict()
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"Duplicate key found: {key}")
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


# Register the custom constructor with the default YAML SafeLoader
class OrderedLoader(yaml.SafeLoader):
    pass


yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, check_duplicate_keys, Loader=OrderedLoader)


def load_and_validate_yaml(filenames):
    yaml_files = []

    for filename in filenames:
        if os.path.isfile(filename) and filename.endswith(".yaml"):
            yaml_files.append(filename)
        elif os.path.isdir(filename):
            yaml_files.extend(glob(os.path.join(filename, "*.yaml")))
        else:
            raise FileNotFoundError(f"Invalid path or no YAML files found: {filename}")

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in specified paths: {filenames}")

    combined_data = OrderedDict()
    for file_path in yaml_files:
        with open(file_path, "r") as f:
            try:
                for doc in yaml.load_all(f, Loader=OrderedLoader):
                    for key, value in doc.items():
                        if key in combined_data:
                            raise DuplicateKeyError(f"Duplicate key '{key}' found across documents.")
                        combined_data[key] = value
            except DuplicateKeyError as e:
                print(f"Error in file {file_path}: {e}")
                raise
    return combined_data


def convert_to_dict(data):
    if isinstance(data, dict):
        return {k: convert_to_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_dict(item) for item in data]
    return data


def format_yaml(data):
    yaml_str = yaml.dump(convert_to_dict(data), default_flow_style=False, sort_keys=False)
    formatted_yaml = "\n".join(f"{'  ' * line.count('  ')}{line}" for line in yaml_str.splitlines())
    return formatted_yaml


def find_defaults_paths(d, path="", paths=None):
    if paths is None:
        paths = []
    for k, v in d.items():
        current_path = f"{path}.{k}" if path else k
        if v == "_DEFAULTS_":
            paths.append(current_path)
        elif isinstance(v, dict):
            find_defaults_paths(v, current_path, paths)
    return paths


def get_by_path(d, path):
    keys = path.split(".")
    value = d
    for key in keys:
        value = value[key]
    return value


def collect_distinct_by_path(data, keys):
    values = collect_by_path(data, keys)
    return list(set(values))


def collect_by_path(data, keys):
    if isinstance(keys, str):
        keys = keys.split(".")
    else:
        keys = list(keys)

    if not keys:
        return [data] if not isinstance(data, list) else data

    key = keys[0]
    if isinstance(data, list):
        values = []
        for item in data:
            if key in item:
                values.extend(collect_by_path(item[key], keys[1:]))
        return values
    elif isinstance(data, dict) and key in data:
        return collect_by_path(data[key], keys[1:])

    return []


def set_by_path(d, path, value):
    keys = path.split(".")
    current = d

    for i, key in enumerate(keys[:-1]):
        if isinstance(current, list):
            key = int(key)  # Convert key to integer if we're inside a list
            if key >= len(current):
                current.append({})
            current = current[key]
        else:
            current = current.setdefault(key, {})

    last_key = keys[-1]

    if isinstance(current, list):
        last_key = int(last_key)  # Convert last key if it's inside a list
        if last_key >= len(current):
            current.append(value)
        else:
            if isinstance(current[last_key], list):
                current[last_key].append(value)
            else:
                current[last_key] = value
    else:
        if last_key in current and isinstance(current[last_key], list):
            current[last_key].append(value)
        else:
            current[last_key] = value

    return d


def deep_merge(source, destination):
    if isinstance(source, dict) and isinstance(destination, dict):
        for key, value in source.items():
            if key in destination:
                destination[key] = deep_merge(value, destination[key])
            else:
                destination[key] = deepcopy(value)
        return destination

    elif isinstance(source, list) and isinstance(destination, list):
        result = []
        # Merge elements at matching indices
        for i in range(max(len(source), len(destination))):
            if i < len(destination) and i < len(source):
                if isinstance(destination[i], (dict, list)):
                    result.append(deep_merge(source[i], deepcopy(destination[i])))
                else:
                    result.append(destination[i])
            elif i < len(source):
                result.append(deepcopy(source[i]))
            else:
                result.append(deepcopy(destination[i]))
        return result

    return destination if destination is not None else deepcopy(source)


def merge_yaml_files(defaults_path, params_path, output_path=None):
    with open(defaults_path) as f:
        defaults = yaml.safe_load(f)

    with open(params_path) as f:
        params = yaml.safe_load(f)

    merged = deep_merge(defaults, deepcopy(params))

    if output_path:
        with open(output_path, "w") as f:
            yaml.dump(merged, f, sort_keys=False)

    return merged
