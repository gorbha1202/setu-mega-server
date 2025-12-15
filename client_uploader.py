import requests
import os

# --- Configuration ---
# Your live Render server URL
SERVER_URL = "https://setu-mega-server.onrender.com"
UPLOAD_ENDPOINT = f"{SERVER_URL}/upload"

# The file you want to upload (this will be created if it doesn't exist)
FILE_TO_UPLOAD = "secure_test_file.txt" 

# NEW: The secret key required by the server (copied from the generator)
API_KEY = "683b0c86ac1be79bd11384d31c8b8cdaee0f7161b1baa3dd021aa677148fb912" 

# --- Prepare and Send the Request ---

def upload_file_to_cloud(filepath):
    """Sends a file to the Render cloud server for storage on MEGA."""

    if not os.path.exists(filepath):
        print(f"Error: File not found at path: {filepath}")
        return

    print(f"Attempting to upload file: {filepath} to {UPLOAD_ENDPOINT}...")

    # Define the header with the required key
    headers = {'X-API-KEY': API_KEY} # <-- THIS IS THE SECURITY IMPLEMENTATION

    # The 'file' key must match the request.files['file'] key in local_server.py
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f)}

        try:
            # Send the POST request, now including the headers
            response = requests.post(UPLOAD_ENDPOINT, files=files, headers=headers)

            # Check for a successful response (status code 200)
            if response.status_code == 200:
                print("\n✅ UPLOAD SUCCESSFUL")
                print(f"Server Response: {response.json()}")
            else:
                print("\n❌ UPLOAD FAILED (Server Error)")
                print(f"Status Code: {response.status_code}")
                print(f"Server Error: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"\n❌ UPLOAD FAILED (Connection Error)")
            print(f"Error Details: {e}")

# --- Execution ---
if __name__ == "__main__":
    # Create a dummy file if the target file doesn't exist
    if not os.path.exists(FILE_TO_UPLOAD):
        with open(FILE_TO_UPLOAD, 'w') as f:
            f.write("This is a placeholder file for your app's actual data.")
        print(f"Created dummy file: {FILE_TO_UPLOAD}")

    upload_file_to_cloud(FILE_TO_UPLOAD)
