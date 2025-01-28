import requests
import os
import argparse
from oauth import get_access_token, get_session_token
from yaml_utils import load_and_validate_yaml

BASE_URL = os.getenv("BASE_URL")
ORG_GUID = os.getenv("ORG_GUID")


def create_team(data):
    access_token = get_access_token()
    # API_TOKEN = get_session_token(access_token)
    API_TOKEN = access_token

    payload = {"name": data.get("name"), "desc": data.get("description"), "org_guid": ORG_GUID, "tags": data.get("tags", [])}

    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.post(f"{BASE_URL}/team", json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("result")
    else:
        raise RuntimeError(f"Failed to create Team: {response.status_code} {response.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a team using a YAML configuration file.")
    parser.add_argument("--yaml-file", required=True, help="Path to the YAML configuration file")
    args = parser.parse_args()

    data = load_and_validate_yaml([args.yaml_file])
    result = create_team(data.get("team"))
    print(result)
