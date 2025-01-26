import os
import requests

# OAuth 2.0 Token Endpoint
TOKEN_URL = os.getenv("TOKEN_URL")
SESSION_TOKEN_URL = os.getenv("SESSION_TOKEN_URL")

# Get client credentials from environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SESSION_USERNAME = os.getenv("SESSION_USERNAME")
SESSION_TOKEN_PASSWORD = os.getenv("SESSION_TOKEN_PASSWORD")

if not CLIENT_ID or not CLIENT_SECRET or not TOKEN_URL:
    raise ValueError("CLIENT_ID and CLIENT_SECRET environment variables must be set.")


def get_access_token():
    payload = {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(TOKEN_URL, data=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise RuntimeError(f"Failed to obtain session token: {response.status_code} {response.text}")


def get_session_token(access_token):
    payload = {"username": SESSION_USERNAME, "password": SESSION_TOKEN_PASSWORD, "from": "pipeline_scripts"}

    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(SESSION_TOKEN_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("result").get("csrfToken")
    else:
        raise RuntimeError(f"Failed to obtain access token: {response.status_code} {response.text}")


if __name__ == "__main__":
    try:
        token = get_access_token()
        print("Access Token:", token)
        session_token = get_session_token(token)
        print("Session Token:", session_token)
    except Exception as e:
        print("Error:", e)
