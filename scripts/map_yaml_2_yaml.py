#!/usr/bin/env python3

import os
import yaml
import argparse
import logging
from collections import OrderedDict
from colorama import init, Fore, Style
import re
import importlib.util
import copy
import shutil

import utils as u
import yaml_utils as y

# Initialize colorama
init(autoreset=True)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()


class ColoredFormatter(logging.Formatter):

    def format(self, record):
        log_color = {"INFO": Fore.WHITE, "WARNING": Fore.YELLOW, "ERROR": Fore.RED, "DEBUG": Fore.BLUE}.get(record.levelname, Fore.WHITE)

        # Colorize single-quoted text (without quotes)
        def colorize_quotes(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.MAGENTA}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize exclamation-mark-wrapped text (without marks)
        def colorize_exclamation(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.CYAN}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize astrik-wrapped text (without marks)
        def colorize_astrik(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.BLUE}{inner_text}{Style.RESET_ALL}{log_color}"

        # Colorize question-mark-wrapped text (without marks)
        def colorize_questionmark(match):
            inner_text = match.group(1)
            return f"{Style.BRIGHT}{Fore.YELLOW}{inner_text}{Style.RESET_ALL}{log_color}"

        def colorize_yaml(match):
            yaml_str = match.group(1)
            formatted_lines = []
            for line in yaml_str.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    formatted_line = f"{Style.BRIGHT}{Fore.YELLOW}{key}{Style.RESET_ALL}:{Style.BRIGHT}{Fore.RED}{value}{Style.RESET_ALL}{log_color}"
                    formatted_lines.append(formatted_line)
            return "\n".join(formatted_lines)

        message = record.getMessage()
        # Apply single-quote highlighting: '...' -> inner text in magenta
        message = re.sub(r"'([^']*)'", colorize_quotes, message)
        # Apply exclamation-mark highlighting: !...! -> inner text in cyan
        message = re.sub(r"!([^!]*)!", colorize_exclamation, message)
        # Apply astrik highlighting: *...* -> inner text in blue
        message = re.sub(r"\*([^!]*)\*", colorize_astrik, message)
        # Apply question-mark highlighting: ?...? -> inner text in yellow
        message = re.sub(r"\?([^!]*)\?", colorize_yaml, message)

        if message.startswith("##"):
            message = message[2:]  # Remove prefix
            return f"{log_color}{message}{Style.RESET_ALL}"

        return f"{log_color}{record.levelname}: {message}{Style.RESET_ALL}"


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)


# Dynamically load all helper functions from _helper_functions.py
def load_helper_functions():
    helper_functions = {}
    helper_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "_helper_functions.py")

    if os.path.exists(helper_file):
        try:
            # Load the module from the file
            spec = importlib.util.spec_from_file_location("helper_functions", helper_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Extract all callable functions defined in the module
            helper_functions = {
                name: func for name, func in vars(module).items() if callable(func) and (not name.startswith("__") and not name.startswith("_"))
            }
            logger.info(f"Loaded helper functions: {', '.join(helper_functions.keys())}")
        except Exception as e:
            logger.error(f"Failed to load helper functions from {helper_file}: {e}")
    else:
        logger.warning(f"_helper_functions.py not found at {helper_file}. No helper functions loaded.")
    return helper_functions


HELPER_FUNCTIONS = load_helper_functions()


def replace_placeholders(template, values, file_name, context=None):
    if context is None:
        kind = template.get("kind", None)
        context = {"kind": kind}

    if context.get("template_key_path") is None:
        context["template_key_path"] = ""

    if isinstance(template, OrderedDict):
        updated_template = OrderedDict()
        for k, v in template.items():
            tmp = copy.deepcopy(context)
            tmp["template_key_path"] = tmp.get("template_key_path") + f".{k}" if tmp.get("template_key_path") else k
            sub = replace_placeholders(v, values, file_name, tmp)
            if isinstance(sub, list):
                if updated_template.get(k, None):
                    updated_template[k].extend(sub)
                else:
                    updated_template[k] = sub
            elif isinstance(sub, dict):
                updated_template[k] = sub
            elif isinstance(sub, str) and sub.isdigit():
                updated_template[k] = int(sub)
            else:
                if sub == "" or sub == None:
                    updated_template.pop(k, None)
                else:
                    updated_template[k] = sub
        return updated_template
    elif isinstance(template, list):
        for item in template:
            return [replace_placeholders(item, values, file_name, context=copy.deepcopy(context))]
    elif isinstance(template, str):
        # Handle the special function prefix {{func.function-name}}
        if "{{func." in template:
            # function_match = re.search(r"{{func\.(.*?)}}", template)
            function_matches = re.finditer(r"{{func\.([^()}]+?)(?:\((.*?)\))?}}", template)
            if len(re.findall(r"{{func\.([^()}]+?)(?:\((.*?)\))?}}", template)) > 1:
                logger.info(f"Multiple function placeholders found in '{file_name}'.")
            for function_match in function_matches:
                if function_match:
                    template = handle_special_functions(template, function_match, values, file_name, context=copy.deepcopy(context))

            if isinstance(template, str) and template.find("{{") == -1 and template.find("}}") == -1:
                return template
        # Replace regular placeholders
        while "{{" in template and "}}" in template:
            start = template.find("{{") + 2
            end = template.find("}}", start)
            if start >= 0 and end >= 0:
                placeholder = template[start:end].strip()
                value = get_nested_value(values, placeholder, context)
                if value is not None:
                    if isinstance(value, dict):
                        logger.info(f"Updating '{placeholder}' in {file_name} with value below:")
                        logger.info(f"##?{y.format_yaml(value)}?")
                    else:
                        logger.info(f"Updating '{placeholder}' in {file_name} with value '{value}'")
                else:
                    logger.warning(f"Placeholder '{placeholder}' in {file_name} has no matching value")
                if isinstance(value, dict) or isinstance(value, list):
                    return value
                else:
                    template = template.replace(f"{{{{{{{placeholder}}}}}}}", yaml.dump(value, default_flow_style=False))

                template = template.replace(f"{{{{{placeholder}}}}}", str(value) if value is not None else "")
                if placeholder == "supportContact.microsoftTeams.url":
                    template = y.FoldedScalarString(template)

        return template
    return template


def handle_special_functions(template, function_match, values, file_name, context=None):
    func_name = function_match.group(1)
    params_str = function_match.group(2)  # Will be None if no parameters
    func = HELPER_FUNCTIONS.get(func_name)
    if callable(func):
        # If we have parameters, process them
        if params_str:
            func_name = f"{function_match.group(1)}({function_match.group(2)})"
            # Split multiple parameters if present
            params = [p.strip() for p in params_str.split(",")]
            # Get the values for each parameter path
            param_values = []
            for param in params:
                # Remove any quotes around the parameter
                param = param.strip("\"'")
                # Get the value from the YAML using the parameter as a path
                param_value = get_nested_value(values, param, context)
                param_values.append(param_value)

            # Call function with context, values, logger, and additional parameters
            result = func(copy.deepcopy(context), copy.deepcopy(values), logger, *param_values)
        else:
            # Call function without additional parameters
            result = func(copy.deepcopy(context), copy.deepcopy(values), logger)

        # result = func(copy.deepcopy(context), copy.deepcopy(values), logger)

        if isinstance(result, list) and (func_name == "lookup_teams_ids" or func_name == "get_asset_name_list" or func_name == "get_asset_resources"):
            return result
        elif isinstance(result, dict) and func_name == "lookup_teams_ids":
            return result
        else:
            logger.info(f"Calling function '{func_name}' in {file_name} with result '{result}'")

            return template.replace(f"{{{{func.{func_name}}}}}", result)
    else:
        logger.warning(f"Function '{func_name}' in {file_name} does not exist.")
        return template  # Leave the placeholder unchanged


def get_nested_value(values, key, context=None):
    context = copy.deepcopy(context)
    keys = key.split(".")
    list_index = context.get("list_index") if context else None
    key_path = context.get("key_path") if context else None
    v = context.get("values") if context else {}
    for k in keys:
        if isinstance(v, dict) and k in v:
            v = v[k]
            if k == "name":
                v = v.lower().replace(" ", "-")
        elif isinstance(v, list) and k == "[]":
            v = v[list_index.pop(0)]
        else:
            return None
    return v


def write_yaml_file(yaml_data, output_folder):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    file_name = f"{yaml_data.get('kind')}.yaml"

    if yaml_data.get("kind") == "Product":
        y.update_icon_in_yaml(yaml_data, "./icons/api-icon.png")
    elif yaml_data.get("kind") == "Asset":
        y.update_icon_in_yaml(yaml_data, "./icons/api-asset-icon.png")

    if yaml_data.get("kind") == "ReleaseTag":
        file_name = (
            f"{yaml_data.get('kind')}-{yaml_data.get("metadata").get("scope").get("kind")}-{yaml_data.get("metadata").get("scope").get("name")}.yaml"
        )
    elif yaml_data.get("kind") == "AccessControlList":
        file_name = f"{yaml_data.get('kind')}-{yaml_data.get("metadata").get("scope").get("kind")}.yaml"

    output_file = os.path.join(output_folder, file_name)
    # Open the file in append mode if it exists, else in write mode
    mode = "a" if os.path.exists(output_file) else "w"
    with open(output_file, mode) as f:
        if mode == "a":
            f.write("\n---\n")
        y.ordered_dump(yaml_data, f, default_flow_style=False)


def walk_keys(values, input_folder, output_folder, parent_key="", context=None):
    if not isinstance(values, dict):
        return
    if u.is_yaml_primitive(values):
        return

    if context is None:
        context = {
            "key_path": "",
            "kind": None,
            "values": values,
            "list_index": None,
        }

    for key, value in values.items():
        current_key = f"{parent_key}.{key}" if parent_key else key
        current_key = f"{current_key}.[]" if isinstance(value, list) else current_key
        context["key_path"] = current_key
        # Check if there's a template for this key

        # !!!!!!!CLEAN UP: Remove this condition
        if current_key == "product.assets.[]":
            continue

        if current_key == "assets.[].services.[].releaseState":
            pass

        template_key = current_key.replace(".[]", "")
        if (file_name := u.get_template_filename(template_key)) and os.path.exists(template_file := os.path.join(input_folder, file_name)):
            logger.info(f"*Processing* key '{current_key}' with template: {template_file}")
            template = y.load_and_validate_yaml([template_file])
            context["kind"] = template.get("kind")
            # Prepare scoped values for the current key

            # If the value is a list, process each item individually (e.g., assets array)
            if isinstance(value, list):
                if key == "accessControlList":
                    logger.info(f"*Processing* key !{current_key}!")
                    context["list_index"].append("*")
                    updated_template = replace_placeholders(template, value, template_file, context=copy.deepcopy(context))
                    # Write the updated template to the output file
                    write_yaml_file(updated_template, output_folder)
                    logger.info(f"*Finished* processing key !{current_key}!")
                    continue

                for index, item in enumerate(value):
                    logger.info(f"*Processing* key !{current_key}! item !{index + 1}! in '{current_key}'")

                    keys = current_key.split(".")  # Split once and reuse
                    # Check if the item has a 'kind' field that matches the template
                    kind = template.get("kind", None)
                    if context.get("list_index") is None:
                        context["list_index"] = [index]
                    else:
                        context["list_index"].append(index)
                    # Replace placeholders in the template for the current item
                    updated_template = replace_placeholders(template, item, template_file, context=copy.deepcopy(context))
                    if key == "accessControlList":
                        template = updated_template

                    # Add tags and attributes if present
                    if isinstance(item, dict):
                        if item.get("tags") or item.get("attributes"):
                            updated_template["tags"] = item.get("tags", [])
                            updated_template["attributes"] = item.get("attributes", {})

                    # Write the updated template to the output file
                    write_yaml_file(updated_template, output_folder)

                    # Recursively process nested keys in the item
                    if isinstance(item, dict):
                        walk_keys(item, input_folder, output_folder, parent_key=current_key, context=copy.deepcopy(context))

                    context["list_index"].pop()
                    logger.info(f"*Finished* processing key !{current_key}! item !{index + 1}! in '{current_key}'")
                    if key == "assets":
                        current_key = f"{parent_key}.{key}" if parent_key else key
                        current_key = f"{current_key}.[]" if isinstance(value, list) else current_key
                        context["key_path"] = current_key
                        del context["list_index"]

            # If the value is a dictionary, process it directly
            elif isinstance(value, dict):
                updated_template = replace_placeholders(template, value, template_file, context=copy.deepcopy(context))

                # Add tags and attributes if present
                if value.get("tags") or value.get("attributes"):
                    environments = y.collect_distinct_by_path(context.get("values", {}), "assets.services.environment")
                    tags = value.get("tags", [])
                    for env in environments:
                        parts = env.split("-")
                        region = "-".join(parts[-3:])
                        # prefix = "-".join(parts[:-3])
                        tags.append(f"env:{env}")
                        tags.append(f"region:{region}")

                    updated_template["tags"] = value.get("tags", [])
                    updated_template["attributes"] = value.get("attributes", {})

                # Write the updated template to the output file
                write_yaml_file(updated_template, output_folder)

        if current_key == "assets.[].services.[].releaseState":
            updated_template = replace_placeholders(template, value, template_file, context=copy.deepcopy(context))
            write_yaml_file(updated_template, output_folder)

        # if current_key == "assets.[].lifecycle":
        #     tmp = template["spec"]
        #     tmp["autoRelease"] = {"releaseType": "major"}
        #     updated_template["spec"] =tmp
        
        # Recursively process nested keys
        if isinstance(value, dict):
            walk_keys(value, input_folder, output_folder, parent_key=current_key, context=copy.deepcopy(context))


def main():
    parser = argparse.ArgumentParser(description="Replace placeholders in YAML templates with values from a YAML file.")
    parser.add_argument("-f", "--filename", nargs="+", required=True, help="YAML file(s) or directory(ies) containing YAML files.")
    parser.add_argument("-o", "--output", help="Folder to write updated YAML files.")
    # values is now filename parameter
    args = parser.parse_args()

    try:
        combined_dict = y.load_and_validate_yaml(args.filename)
        logger.info(f"Combined YAML data from files {args.filename} below:")
        logger.info(f"##?{y.format_yaml(combined_dict)}?")

        defaults_dict = y.load_and_validate_yaml(["./accounts/defaults.yaml"])
        logger.info(f"Defaults YAML data:")
        logger.info(f"##?{y.format_yaml(defaults_dict)}?")

        combined_dict = y.deep_merge(defaults_dict, combined_dict)
        logger.info(f"Combined YAML data after applying defaults:")
        logger.info(f"##?{y.format_yaml(combined_dict)}?")
        write_yaml_file(combined_dict, args.output)

        # Deletes the output folder if it exists and recreates it.
        if os.path.exists(args.output):
            shutil.rmtree(args.output)  # Deletes the folder and its contents
        os.makedirs(args.output, exist_ok=True)

        # Start walking from the root (parent_key="") of the values.yaml file
        walk_keys(combined_dict, "./templates", args.output, parent_key="")

        logger.info(f"All YAML documents written to folder: '{args.output}'")

    except y.DuplicateKeyError as e:
        print("Validation failed:", e)
    except FileNotFoundError as e:
        print(e)


if __name__ == "__main__":
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    main()
