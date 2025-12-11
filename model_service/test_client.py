"""
Menu-driven test client for model_service endpoints.

Works with updated API:
    - /refresh-db now requires: identity + multiple files
"""

import sys
import os
import json
import requests
import base64
from pathlib import Path
from getpass import getpass

DEFAULT_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:8080')

# Auth state (populated by ensure_auth)
AUTH_USERNAME = os.environ.get('MODEL_SERVICE_USER')
AUTH_PASSWORD = None
AUTH_ACCESS_TOKEN = None
AUTH_REFRESH_TOKEN = None
AUTH_API_KEY = os.environ.get('MODEL_SERVICE_API_KEY')


def ensure_auth():
    """Ensure we have an access token and api key. Prompts user if needed.

    Flow:
    - If env vars provide API key and user/pass, use them.
    - Otherwise prompt to register or login, then create an API key.
    """
    global AUTH_USERNAME, AUTH_PASSWORD, AUTH_ACCESS_TOKEN, AUTH_REFRESH_TOKEN, AUTH_API_KEY

    if AUTH_API_KEY and AUTH_ACCESS_TOKEN:
        return

    # get username/password from env or prompt
    if not AUTH_USERNAME:
        print("\nNo username provided via MODEL_SERVICE_USER. Please enter credentials to login/register.")
        AUTH_USERNAME = input('Username: ').strip()
    if not AUTH_PASSWORD:
        # avoid echoing password
        AUTH_PASSWORD = os.environ.get('MODEL_SERVICE_PASS') or getpass('Password: ')

    # Ask whether to register
    print('\nDo you need to register this user on the service? (y/N)')
    r = input('> ').strip().lower()
    if r == 'y' or r == 'yes':
        resp = requests.post(f"{DEFAULT_URL}/register", data={"username": AUTH_USERNAME, "password": AUTH_PASSWORD})
        if resp.status_code not in (200, 201):
            print('Register failed:', resp.status_code, resp.text)
        else:
            print('Registered:', resp.json())

    # Login to get tokens
    resp = requests.post(f"{DEFAULT_URL}/login", data={"username": AUTH_USERNAME, "password": AUTH_PASSWORD})
    if resp.status_code != 200:
        print('Login failed:', resp.status_code, resp.text)
        raise SystemExit(1)
    tokens = resp.json()
    AUTH_ACCESS_TOKEN = tokens.get('access_token')
    AUTH_REFRESH_TOKEN = tokens.get('refresh_token')
    print('Obtained access token and refresh token.')

    # Create API key if not provided
    if not AUTH_API_KEY:
        resp = requests.post(f"{DEFAULT_URL}/apikey/create", data={"username": AUTH_USERNAME, "password": AUTH_PASSWORD})
        if resp.status_code != 200:
            print('API key creation failed:', resp.status_code, resp.text)
            raise SystemExit(1)
        AUTH_API_KEY = resp.json().get('api_key')
        print('Created API key.')


def auth_headers():
    headers = {}
    if AUTH_ACCESS_TOKEN:
        headers['Authorization'] = f"Bearer {AUTH_ACCESS_TOKEN}"
    if AUTH_API_KEY:
        headers['x-api-key'] = AUTH_API_KEY
    return headers


# ------------------------------------------------------
# UTIL PROMPTS
# ------------------------------------------------------

def prompt_files(prompt_text, multiple=False):
    print(prompt_text)
    if multiple:
        print('Enter file paths separated by commas:')
        s = input('> ').strip()
        if not s:
            return []
        paths = [p.strip(' "') for p in s.split(',') if p.strip()]
        return paths
    else:
        p = input('Enter file path: ').strip()
        if not p:
            return None
        return p


# ------------------------------------------------------
# /refresh-db  (UPDATED)
# ------------------------------------------------------

def call_refresh_db():
    print("\n=== Refresh ArcFace DB ===")
    identity = input("Enter identity (student ID): ").strip()
    if not identity:
        print("Identity required.")
        return

    paths = prompt_files('Upload images for identity: ' + identity, multiple=True)
    if not paths:
        print("No files selected.")
        return

    validated = []
    for p in paths:
        if not os.path.exists(p):
            print(f"File not found: {p}")
            return
        validated.append(p)

    print(f"\nUploading {len(validated)} images for identity: {identity}")

    files_payload = []
    file_handles = []

    try:
        for p in validated:
            fh = open(p, "rb")
            file_handles.append(fh)
            # multiple files under field name "files"
            files_payload.append(("files", (os.path.basename(p), fh, "image/jpeg")))

        # identity as form-data
        data = {"identity": identity}

        url = f"{DEFAULT_URL}/refresh-db"
        print(f"\nPOST {url} ...")
        # ensure auth and attach headers
        ensure_auth()
        headers = auth_headers()
        resp = requests.post(url, files=files_payload, data=data, headers=headers)

        print("Status:", resp.status_code)
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)

    finally:
        for fh in file_handles:
            try:
                fh.close()
            except:
                pass


# ------------------------------------------------------
# /detect
# ------------------------------------------------------

def call_detect():
    p1 = prompt_files("First image:", multiple=False)
    p2 = prompt_files("Second image:", multiple=False)
    if not p1 or not p2:
        print("Both images required.")
        return
    if not os.path.exists(p1) or not os.path.exists(p2):
        print("Files missing.")
        return

    files = {
        "img1": (os.path.basename(p1), open(p1, "rb"), "image/jpeg"),
        "img2": (os.path.basename(p2), open(p2, "rb"), "image/jpeg"),
    }

    url = f"{DEFAULT_URL}/detect"
    print(f"\nPOST {url} ...")
    ensure_auth()
    headers = auth_headers()
    try:
        resp = requests.post(url, files=files, headers=headers)
        print("Status:", resp.status_code)
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
    finally:
        # close file handles
        for v in files.values():
            try:
                v[1].close()
            except Exception:
                pass


# ------------------------------------------------------
# /recognise (unified)
# - Supports: multipart file, multipart/form (image_b64) and JSON base64
# ------------------------------------------------------


def call_recognize():
    p = prompt_files("Recognize - query image:", multiple=False)
    if not p:
        print("No file.")
        return
    if not os.path.exists(p):
        print("File missing:", p)
        return

    print("\nChoose method:")
    print("1) multipart/form-data file upload (/recognise)")
    print("2) form field base64 (multipart/form or form-urlencoded) (/recognise)")
    print("3) application/json base64 (/recognise)")
    choice = input("> ").strip()

    with open(p, "rb") as fh:
        b = fh.read()

    b64 = base64.b64encode(b).decode()

    if choice == "2":
        # Send as form data (form-urlencoded) - FastAPI Form reads this
        url = f"{DEFAULT_URL}/recognise"
        data = {"image_b64": b64}
        print(f"\nPOST {url} (form) ...")
        ensure_auth()
        headers = auth_headers()
        resp = requests.post(url, data=data, headers=headers)
    elif choice == "3":
        url = f"{DEFAULT_URL}/recognise"
        payload = {"image_b64": b64}
        print(f"\nPOST {url} (json) ...")
        ensure_auth()
        headers = auth_headers()
        resp = requests.post(url, json=payload, headers=headers)
    else:
        url = f"{DEFAULT_URL}/recognise"
        files = {"file": (os.path.basename(p), open(p, "rb"), "image/jpeg")}
        print(f"\nPOST {url} (multipart file) ...")
        ensure_auth()
        headers = auth_headers()
        try:
            resp = requests.post(url, files=files, headers=headers)
        finally:
            # close file handle
            try:
                files['file'][1].close()
            except Exception:
                pass

    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except:
        print(resp.text)


# ------------------------------------------------------
# MENU
# ------------------------------------------------------

def main_menu():
    print("Model Service Test Client")
    print("Service URL:", DEFAULT_URL)
    while True:
        print("\nChoose an action:")
        print("1) Refresh DB (register images for an identity)")
        print("2) Detect / Verify two images")
        print("3) Recognize (query against DB)")
        print("4) Quit")

        c = input("> ").strip()
        if c == "1":
            call_refresh_db()
        elif c == "2":
            call_detect()
        elif c == "3":
            call_recognize()
        elif c in ("4", "q", "quit", "exit"):
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
