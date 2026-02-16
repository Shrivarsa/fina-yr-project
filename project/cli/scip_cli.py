#!/usr/bin/env python3
import requests
import json
import sys
import os
import getpass

CONFIG_FILE = 'config.json'
AUTH_FILE = '.scip_auth'

def load_config():
    """Load configuration from config.json"""
    try:
        with open(os.path.join(os.path.dirname(__file__), CONFIG_FILE), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {CONFIG_FILE}")
        sys.exit(1)

def load_auth_token():
    """Load cached authentication token"""
    try:
        with open(os.path.join(os.path.dirname(__file__), AUTH_FILE), 'r') as f:
            auth_data = json.load(f)
            return auth_data.get('access_token')
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def save_auth_token(access_token):
    """Save authentication token for future use"""
    try:
        with open(os.path.join(os.path.dirname(__file__), AUTH_FILE), 'w') as f:
            json.dump({'access_token': access_token}, f)
    except Exception as e:
        print(f"Warning: Could not save auth token: {e}")

def login(api_url, email, password):
    """Authenticate with the backend and get access token"""
    try:
        print("Authenticating...")
        response = requests.post(
            f"{api_url}/api/login",
            json={'email': email, 'password': password}
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            username = data.get('username')
            save_auth_token(access_token)
            print(f"Successfully logged in as {username}")
            return access_token
        else:
            print(f"Login failed: {response.json().get('error', 'Unknown error')}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}")
        print("Make sure the Flask server is running (python scip_orchestrator.py)")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def analyze_file(file_path, api_url, access_token):
    """Send file content to Flask API for analysis"""
    try:
        with open(file_path, 'r') as f:
            code_content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    endpoint = f"{api_url}/api/analyze_commit"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'code_content': code_content,
    }

    try:
        print(f"\nAnalyzing file: {file_path}")
        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code == 401:
            print("Authentication expired. Please login again.")
            return None

        response.raise_for_status()

        result = response.json()
        print("\n" + "=" * 50)
        print("ANALYSIS RESULT")
        print("=" * 50)
        print(f"Commit Hash:      {result['commit_hash']}")
        print(f"Risk Score:       {result['risk_score']:.1f}%")
        print(f"Status:           {result['status']}")
        print(f"DLT Transaction:  {result['dlt_tx_hash']}")
        print(f"Timestamp:        {result['timestamp']}")
        print("=" * 50)

        return result

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}")
        return None
    except requests.exceptions.RequestException as e:
        error_data = e.response.json() if e.response else {}
        print(f"Error: {error_data.get('error', str(e))}")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from server")
        return None

def main():
    config = load_config()
    api_url = config.get('api_url', 'http://localhost:5000')

    if len(sys.argv) < 2:
        print("SCIP Guardian CLI - Code Security Analysis Tool")
        print("Usage: python scip_cli.py <file_path>")
        print("Example: python scip_cli.py example.py")
        sys.exit(1)

    file_path = sys.argv[1]

    access_token = load_auth_token()

    if not access_token:
        print("SCIP Guardian - Multi-User Authentication")
        print("=" * 50)
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")

        access_token = login(api_url, email, password)
        if not access_token:
            sys.exit(1)

    analyze_file(file_path, api_url, access_token)

if __name__ == '__main__':
    main()
