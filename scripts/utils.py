import re

KEY_TO_KIND_MAP = {
    "product": "Product",
    "assets": "Asset",
    "accessControlList": "AccessControlList",
    "services": "AssetMapping",
    "activate": "ReleaseTag",
    "plans": "ProductPlan",
    "quotas": "Quota",
    "marketplace": "PublishedProduct",
}

KEY_TO_TEMPLATE_MAP = {
    "product": "product.yaml",
    "assets": "asset.yaml",
    "assets.accessControlList": "access-control-list.yaml",
    "assets.services": "asset-mapping.yaml",
    "assets.activate": "release-tag-asset.yaml",
    "product.activate": "release-tag-product.yaml",
    "product.plans": "product-plan.yaml",
    "product.plans.quotas": "quota.yaml",
    "product.activate.marketplace": "published-product.yaml",
}


def find_key_path(d, target_key, current_path=None, list_index=None):
    if current_path is None:
        current_path = []

    for key, value in d.items():
        # Append current key to the path
        new_path = current_path + [key]

        if key == target_key:
            return new_path  # Found the target key, return its full path

        # If the value is another dict, recurse into it
        if isinstance(value, dict):
            result = find_key_path(value, target_key, new_path)
            if result is not None:
                return result

        # If the value is a list, recurse into each item
        if isinstance(value, list):
            for i, item in enumerate(value):
                result = find_key_path(item, target_key, new_path + [i])
                if result is not None:
                    return result
    # If not found at this level
    return None


def camel_to_kebab(input_string):
    kebab_case = re.sub(r"(?<!^)(?=[A-Z])", "-", input_string).lower()
    return kebab_case


def is_yaml_primitive(value):
    # Check for primitive types
    if isinstance(value, (str, int, float, bool)) or value is None:
        return True
    # Exclude arrays (lists) and objects (dicts)
    if isinstance(value, (list, dict)):
        return False
    # For any unexpected type, return False
    return False
