import yaml
import os

import utils


def get_asset_name_list(context, values, logger):
    kind = context.get("kind", "")
    values = context.get("values", {})
    asset_name_list = []
    if kind == "Product":
        asset_list = values.get("product", {}).get("assets", [])
        check_list = values.get("assets", [])
        for asset in asset_list:
            for check_asset in check_list:
                if asset.get("name") == check_asset.get("name"):
                    name = asset.get("name", None).lower().replace(" ", "-")
                    asset_name_list.append({"name": name})

    return asset_name_list


def get_parent_name(context, values, logger):
    list_index = context.get("list_index") if context else None
    keys = context.get("key_path").split(".") if context else None
    kind = context.get("kind") if context else None
    if (kind == "ReleaseTag" or kind == "AssetMapping" or kind == "AccessControlList") and keys[0] == "assets":
        keys = keys[:2] + ["name"]
    elif kind == "ProductPlan":
        keys = keys[:1] + ["name"]
    elif kind == "Quota":
        keys = keys[:3] + ["name"]
    elif kind == "ReleaseTag" and keys[0] == "product":
        keys = keys[:1] + ["name"]

    v = context.get("values") if context else {}
    parent_name = None
    for k in keys:
        if isinstance(v, dict) and k in v:
            v = v[k]
        elif isinstance(v, list) and k == "[]":
            v = v[list_index.pop(0)]

    return v.lower().replace(" ", "-")


def get_parent_kind(context, values, logger):
    list_index = context.get("list_index") if context else None
    keys = context.get("key_path").split(".") if context else None
    kind = context.get("kind") if context else None
    if context.get("kind") == "ReleaseTag" or context.get("kind") == "AssetMapping" or context.get("kind") == "AccessControlList":
        return utils.KEY_TO_KIND_MAP.get(keys.pop(0))


# Cache the team data for efficiency
TEAM_DATA = None


def _load_team_data(team_file_path):
    global TEAM_DATA
    if TEAM_DATA is None:
        if not os.path.exists(team_file_path):
            raise FileNotFoundError(f"Team data file not found: {team_file_path}")
        with open(team_file_path, "r") as file:
            TEAM_DATA = yaml.safe_load(file).get("teams", [])
    return TEAM_DATA


def lookup_teams_ids(context, values, logger):
    kind = context.get("kind", "")
    v = context.get("values", {})
    team_file_path = os.path.join(os.path.dirname(__file__), "data/central-teams.yaml")
    teams = _load_team_data(team_file_path)
    keys = context.get("key_path").split(".") if context else None
    list_index = context.get("list_index") if context else None
    teams_ids_list = []
    if kind == "AccessControlList":
        for k in keys:
            if isinstance(v, dict) and k in v:
                v = v[k]
            elif isinstance(v, list) and k == "[]":
                if list_index[0] == "*":
                    v = v
                else:
                    v = v[list_index.pop(0)]
        team_name_list = v
        for team in team_name_list:
            team_name = team.get("teamName", None)
            for team in teams:
                if team.get("name") == team_name:
                    teams_ids_list.append({"id": team.get("id"), "type": "team"})

    return teams_ids_list


def lookup_team_id(context, values, logger):
    list_index = context.get("list_index") if context else None
    keys = context.get("key_path").split(".") if context else None
    template_keys = context.get("template_key_path").split(".") if context else None
    kind = context.get("kind") if context else None
    v = context.get("values") if context else {}
    team_name = None

    if kind == "Asset" or kind == "Product":
        keys.extend(["owner", "teamName"])
    elif kind == "ProductPlan":
        keys = keys[:-2]
        keys.extend(["owner", "teamName"])
    for k in keys:
        if isinstance(v, dict) and k in v:
            v = v[k]
        elif isinstance(v, list) and k == "[]":
            v = v[list_index.pop(0)]
    team_name = v

    team_file_path = os.path.join(os.path.dirname(__file__), "data/central-teams.yaml")
    teams = _load_team_data(team_file_path)

    for team in teams:
        if team.get("name") == team_name:
            return team.get("id")
    return None


def generate_asset_name(context, values, logger):
    context["kind"] = "Asset"
    return generate_name(context, values)

def format_name(context, values, logger, param):
    # list_index = context.get("list_index") if context else None
    # keys = context.get("key_path").split(".") if context else None
    # v = context.get("values") if context else {}
    # kind = context.get("kind") if context else None

    # for k in keys:
    #     if isinstance(v, dict) and k in v:
    #         v = v[k]
    #     elif isinstance(v, list) and k == "[]":
    #         v = v[list_index.pop(0)]
    return param.lower().replace(" ", "-")

# Helper function to generate names
def generate_name(context, values, logger):
    list_index = context.get("list_index") if context else None
    keys = context.get("key_path").split(".") if context else None
    v = context.get("values") if context else {}
    kind = context.get("kind") if context else None

    if kind == "Asset" or kind == "Product":
        keys.extend(["name"])
    elif kind == "AssetMapping":
        keys.extend(["name", "services", "[]", "name"])
    elif kind == "ProductPlan":
        keys.extend(["name"])
    elif kind == "Quota":
        keys.extend(["name"])

    for k in keys:
        if isinstance(v, dict) and k in v:
            v = v[k]
        elif isinstance(v, list) and k == "[]":
            v = v[list_index.pop(0)]
    return v.lower().replace(" ", "-")


def access_control_list_subjects(context, values, logger):
    tname = values.get("product", {}).get("assets", {}).get("accessControlList", {}).get("teamName", "")
    id = lookup_team_id
    return values.get("product", {}).get("assets", {}).get("accessControlList", [])


def get_asset_resources(context, values, logger):
    kind = context.get("kind", "")
    v = context.get("values", {})
    list_index = context.get("list_index") if context else None
    keys = context.get("key_path").split(".") if context else None
    asset_resources = []
    if kind == "Quota":
        keys.extend(["services"])
    for k in keys:
        if isinstance(v, dict) and k in v:
            if k == "services":
                asset_resources = v[k]
            else:
                v = v[k]
        elif isinstance(v, list) and k == "[]":
            v = v[list_index.pop(0)]

    asset_name_list = []
    for asset_service in asset_resources:
        service = asset_service.get("name")
        title = _find_asset_title(context.get("values", {}), service)
        if title:
            service = title
        asset = asset_service.get("asset").lower().replace(" ", "-")
        asset_name = f"{asset}/{service}"

        asset_name_list.append({"kind": "AssetResource", "name": asset_name})

    return asset_name_list


def _find_asset_title(v, name, keys=None):
    keys = "assets.[].services.[].title".split(".") if not keys else keys
    for idx, k in enumerate(keys):
        if isinstance(v, dict) and k in v:
            if k == "title" and v.get("name") == name:
                return v[k].lower().replace(" ", "-")
            v = v[k]
        elif isinstance(v, list) and k == "[]":
            for item in v:
                title = _find_asset_title(item, name, keys[idx + 1 :])
                if title:
                    return title

    return None
