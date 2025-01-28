#!/usr/bin/env python3

import os
import yaml
import argparse
import logging
from collections import OrderedDict
from logger_config import logger
from _helper_functions import load_helper_functions
import re
import copy
import shutil

import utils as u
import yaml_utils as y

# Load helper functions
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
                    if k == "name":
                        v = v.lower().replace(" ", "-")

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
        yaml_data_no_auto_release = yaml_data.copy()
        del yaml_data_no_auto_release["spec"]["autoRelease"]
        output_file = os.path.join(output_folder, f"no-auto-release-{file_name}")
        # Open the file in append mode if it exists, else in write mode
        mode = "a" if os.path.exists(output_file) else "w"
        with open(output_file, mode) as f:
            if mode == "a":
                f.write("\n---\n")
            y.ordered_dump(yaml_data_no_auto_release, f, default_flow_style=False)

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


def update_yaml_with_services(defaults_data, services_data, key_path):
    # Extract services from assets.services
    services = []
    for asset in services_data.get("assets", []):
        for service in asset.get("services", []):
            services.append({"name": service["name"], "asset": asset["name"]})

    # Navigate to the specified key path in defaults.yaml
    keys = key_path.split(".")
    data = defaults_data
    for key in keys:
        if isinstance(data, list):
            data = [d[key] for d in data if key in d]
        else:
            data = data.get(key, {})

    # If we reached a list of quotas, update each one
    if isinstance(data, list):
        for item in data:
            item[0]["services"] = services

    return defaults_data


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

        defaults_dict = update_yaml_with_services(defaults_dict, combined_dict, "product.plans.quotas")
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
