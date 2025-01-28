import os
import requests
import sys
import argparse
from oauth import get_access_token, get_session_token
from yaml_utils import load_and_validate_yaml
from fetch_team_ids import fetch_team_ids

# Load required environment variables
BASE_URL = os.getenv("BASE_URL")
ORG_ID = os.getenv("ORG_ID")
IDP_ID = os.getenv("IDP_ID")
API_TOKEN = "your_api_token"  # Keep this manually set or load it securely

# Validate that required environment variables are set
if not BASE_URL or not ORG_ID or not IDP_ID:
    print("Error: Missing required environment variables. Ensure BASE_URL, ORG_ID, and IDP_ID are set.")
    sys.exit(1)


# Function to get the current IDP data
def get_idp():
    url = f"{BASE_URL}/org/{ORG_ID}/idp/{IDP_ID}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching IDP: {response.status_code}, {response.text}")
        return None


# Function to transform GET IDP response to PUT request format
def transform_idp_data(idp_data):
    if not idp_data or "result" not in idp_data:
        print("Error: Invalid IDP data received.")
        return None

    result = idp_data["result"]

    transformed_data = {
        "providerId": "oidc",  # Ensure providerId is always set to "oidc"
        "allowedClockSkew": int(result.get("allowedClockSkew", 0)),
        "authorizationUrl": result.get("base_uri", ""),
        "clientAuthMethod": result["idp"].get("config", {}).get("clientAuthMethod", ""),
        "clientId": result["idp"].get("config", {}).get("clientId", ""),
        "clientSecret": result["idp"].get("config", {}).get("clientSecret", ""),
        "defaultScope": result["idp"].get("config", {}).get("defaultScope", ""),
        "defaultRoles": result.get("default_roles", []),
        "defaultTeams": result.get("default_teams", []),
        "description": result.get("description", ""),
        "enforceMappedTeams": result.get("enforce_mapped_teams", False),
        "mappedRoles": result.get("mapped_roles", []),
        "mappedTeams": result.get("mapped_teams", []),
        "name": result.get("name", ""),
        "pkceEnabled": result["idp"].get("config", {}).get("pkceEnabled", False),
        "sendClientIdOnLogout": result["idp"].get("config", {}).get("sendClientIdOnLogout", False),
        "sendIdTokenOnLogout": result["idp"].get("config", {}).get("sendIdTokenOnLogout", False),
        "tokenUrl": result["idp"].get("config", {}).get("tokenUrl", ""),
        "useJwksUrl": result["idp"].get("config", {}).get("useJwksUrl", False),
        "validateSignature": result["idp"].get("config", {}).get("validateSignature", False),
    }

    return transformed_data


# Function to update the IDP with a new mapped team
def update_idp(new_team):
    idp_data = get_idp()
    if not idp_data:
        return

    # Transform the GET response into the PUT format
    transformed_idp_data = transform_idp_data(idp_data)
    if not transformed_idp_data:
        return

    # Ensure "mappedTeams" exists
    if "mappedTeams" not in transformed_idp_data:
        transformed_idp_data["mappedTeams"] = []

    # Append new mapped team
    transformed_idp_data["mappedTeams"].append(new_team)

    # Prepare PUT request
    url = f"{BASE_URL}/org/{ORG_ID}/idp/{IDP_ID}"
    response = requests.put(url, headers=HEADERS, json=transformed_idp_data)

    if response.status_code == 200:
        print("IDP updated successfully!")
    else:
        print(f"Error updating IDP: {response.status_code}, {response.text}")


access_token = get_access_token()


API_TOKEN = access_token

# Headers for authentication
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a team using a YAML configuration file.")
    parser.add_argument("--yaml-file", required=True, help="Path to the YAML configuration file")
    args = parser.parse_args()

    data = load_and_validate_yaml([args.yaml_file])

    idpData = data["team"]["idpMapping"]
    teamName = data["team"]["name"]

    team_list = fetch_team_ids()
    for team in team_list:
        if team.get("name") == teamName:
            idpData["team_guid"] = team.get("guid")
            break

    # Run the update
    update_idp(idpData)
