#!/usr/bin/env python3
"""
SCIP Guardian CLI - Multi-User Code Security Analysis Tool
"""
import requests
import json
import sys
import os
import argparse
from pathlib import Path

CONFIG_FILE = 'config.json'
AUTH_FILE = '.scip_auth'

def get_auth_file_path():
    """Get the path to the auth file in the CLI directory."""
    return os.path.join(os.path.dirname(__file__), AUTH_FILE)

def load_config():
    """Load configuration from config.json"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {CONFIG_FILE}")
        sys.exit(1)

def get_password(prompt="Password: "):
    """
    Cross-platform password input that correctly handles special characters
    including quotes, semicolons, backslashes, and other symbols on Windows.
    """
    # Try Windows-specific msvcrt first (handles all special chars properly)
    if sys.platform == 'win32':
        try:
            import msvcrt
            print(prompt, end='', flush=True)
            chars = []
            while True:
                ch = msvcrt.getwch()  # Unicode-aware character read
                if ch in ('\r', '\n'):  # Enter key
                    print('')           # newline after input
                    break
                elif ch == '\x03':      # Ctrl+C
                    raise KeyboardInterrupt
                elif ch == '\x08':      # Backspace
                    if chars:
                        chars.pop()
                        # Erase the last * on screen
                        print('\b \b', end='', flush=True)
                else:
                    chars.append(ch)
                    print('*', end='', flush=True)
            return ''.join(chars)
        except ImportError:
            pass  # Fall through to getpass if msvcrt not available

    # Unix fallback — getpass works fine on Linux/Mac
    import getpass
    return getpass.getpass(prompt)

def load_auth_token():
    """Load cached Supabase session token"""
    try:
        auth_path = get_auth_file_path()
        with open(auth_path, 'r') as f:
            auth_data = json.load(f)
            return auth_data.get('access_token'), auth_data.get('refresh_token')
    except FileNotFoundError:
        return None, None
    except json.JSONDecodeError:
        return None, None

def save_auth_token(access_token, refresh_token=None):
    """Save Supabase session token for future use"""
    try:
        auth_path = get_auth_file_path()
        auth_data = {'access_token': access_token}
        if refresh_token:
            auth_data['refresh_token'] = refresh_token

        with open(auth_path, 'w') as f:
            json.dump(auth_data, f)

        try:
            os.chmod(auth_path, 0o600)
        except:
            pass  # Windows doesn't support chmod
    except Exception as e:
        print(f"Warning: Could not save auth token: {e}")

def clear_auth_token():
    """Clear cached authentication token"""
    try:
        auth_path = get_auth_file_path()
        if os.path.exists(auth_path):
            os.remove(auth_path)
            print("Logged out successfully")
    except Exception as e:
        print(f"Warning: Could not clear auth token: {e}")

def login(api_url, email=None, password=None):
    """Authenticate with the backend and get Supabase session token"""
    try:
        if not email:
            email = input("Email: ").strip()
        if not password:
            password = get_password("Password: ")

        print("Authenticating...")
        response = requests.post(
            f"{api_url}/api/login",
            json={'email': email, 'password': password}
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            username = data.get('username')

            if access_token:
                save_auth_token(access_token, refresh_token)
                print(f"Successfully logged in as {username}")
                return access_token
            else:
                print("Login failed: No access token received")
                return None
        else:
            error_msg = (
                response.json().get('error', 'Unknown error')
                if response.headers.get('content-type', '').startswith('application/json')
                else 'Login failed'
            )
            print(f"Login failed: {error_msg}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}")
        print("Make sure the Flask server is running (python backend/scip_orchestrator.py)")
        return None
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def analyze_file(file_path, api_url, access_token):
    """Send file content to Flask API for analysis"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
    payload = {'code_content': code_content}

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

        if result.get('reasoning'):
            print(f"\nReasoning:        {result['reasoning']}")

        if result.get('vulnerabilities'):
            print(f"\nVulnerabilities:")
            for vuln in result['vulnerabilities']:
                print(f"  - {vuln}")

        print("=" * 50)
        return result

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}")
        return None
    except requests.exceptions.RequestException as e:
        error_data = (
            e.response.json()
            if e.response and e.response.headers.get('content-type', '').startswith('application/json')
            else {}
        )
        print(f"Error: {error_data.get('error', str(e))}")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from server")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='SCIP Guardian CLI - Code Security Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scip_cli.py login                    # Interactive login
  scip_cli.py login -e user@email.com  # Login with email (password prompt)
  scip_cli.py logout                   # Clear saved session
  scip_cli.py analyze example.py       # Analyze a file
  scip_cli.py example.py               # Analyze a file (short form)
        """
    )

    parser.add_argument('command', nargs='?', choices=['login', 'logout', 'analyze'],
                        help='Command to execute')
    parser.add_argument('file_path', nargs='?', help='Path to file to analyze')
    parser.add_argument('-e', '--email', help='Email for login')
    parser.add_argument('-p', '--password', help='Password for login (not recommended)')

    args = parser.parse_args()

    config = load_config()
    api_url = config.get('api_url', 'http://localhost:5000')

    if args.command == 'login' or (not args.command and not args.file_path):
        login(api_url, args.email, args.password)
        return

    if args.command == 'logout':
        clear_auth_token()
        return

    file_path = args.file_path if args.command == 'analyze' else (args.file_path or args.command)

    if not file_path:
        parser.print_help()
        sys.exit(1)

    access_token, _ = load_auth_token()

    if not access_token:
        print("SCIP Guardian - Multi-User Authentication")
        print("=" * 50)
        access_token = login(api_url)
        if not access_token:
            sys.exit(1)

    analyze_file(file_path, api_url, access_token)

if __name__ == '__main__':
    main()