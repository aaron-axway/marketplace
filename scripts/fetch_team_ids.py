import requests
import os
from oauth import get_access_token, get_session_token
from yaml_utils import ordered_dump
import logging

BASE_URL = os.getenv("BASE_URL")


def fetch_team_ids():
    access_token = get_access_token()
    # API_TOKEN = get_session_token(access_token)
    API_TOKEN = access_token
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.get(f"{BASE_URL}/team", headers=headers)

    if response.status_code == 200:
        return response.json().get("result")
    else:
        raise RuntimeError(f"Failed to fetch team IDs: {response.status_code} {response.text}")


if __name__ == "__main__":
    current_dir = os.getcwd()
    team_list = fetch_team_ids()
    team_yaml = {"teams": []}
    for team in team_list:
        team_yaml["teams"].append({"id": team.get("guid"), "name": team.get("name")})

    output_file = os.path.join(current_dir, "test.yaml")
    # Open the file in append mode if it exists, else in write mode
    mode = "a" if os.path.exists(output_file) else "w"
    with open(output_file, mode) as f:
        if mode == "a":
            f.write("\n---\n")
        ordered_dump(team_yaml, f, default_flow_style=False)
