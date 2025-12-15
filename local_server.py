import os
import tempfile
from functools import wraps
from flask import Flask, request, jsonify
from mega import Mega

# --- 1. ENVIRONMENT VARIABLE SETUP ---

# Read environment variables for MEGA credentials
MEGA_EMAIL = os.environ.get('MEGA_EMAIL')
MEGA_PASSWORD = os.environ.get('MEGA_PASSWORD')
MEGA_FOLDER_NAME = os.environ.get('MEGA_FOLDER_NAME', 'Uploaded_Data')

# NEW: Read the secret API key for security
API_SECRET_KEY = os.environ.get('API_SECRET_KEY') 

app = Flask(__name__)
mega = None

# --- 2. MEGA LOGIN FUNCTION ---

def login_mega():
    global mega
    if mega is None:
        try:
            mega = Mega.from_login(MEGA_EMAIL, MEGA_PASSWORD)
        except Exception as e:
            app.logger.error(f"MEGA Login Failed: {e}")
            return None
    return mega

# --- 3. SECURITY DECORATOR ---

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for the key in the request header 'X-API-KEY'
        key = request.headers.get('X-API-KEY')
        
        if not key or key != API_SECRET_KEY:
            # Return 401 Unauthorized if the key is missing or invalid
            return jsonify({"status": "error", "message": "Unauthorized: Missing or invalid API Key."}), 401
        
        return f(*args, **kwargs)
    return decorated

# --- 4. ROUTES ---

@app.route('/', methods=['GET'])
def index():
    m = login_mega()
    if m:
        # Simple health check
        return jsonify({
            "status": "Server and MEGA are connected.",
            "storage_plan": f"{m.get_storage_space(giga=True)['used']} GB Used / {m.get_storage_space(giga=True)['total']} GB Total"
        })
    else:
        return jsonify({"status": "error", "message": "MEGA service is unavailable."}), 503

@app.route('/upload', methods=['POST'])
@require_api_key # <-- SECURITY APPLIED HERE
def upload_file():
    m = login_mega()
    if m is None:
        return jsonify({"status": "error", "message": "MEGA service is unavailable."}), 503

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file."}), 400
    
    filename = file.filename
    temp_file_path = None
    
    try:
        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            file.save(temp)
            temp_file_path = temp.name

        # Create the target folder if it doesn't exist
        mega_folder = m.find(MEGA_FOLDER_NAME)
        if not mega_folder:
            m.create_folder(MEGA_FOLDER_NAME)
            mega_folder = m.find(MEGA_FOLDER_NAME)

        # Upload the file to MEGA
        m.upload(temp_file_path, mega_folder[0])

        return jsonify({
            "filename": filename,
            "message": "File uploaded successfully to MEGA storage.",
            "remote_folder": MEGA_FOLDER_NAME
        })

    except Exception as e:
        app.logger.error(f"File upload failed: {e}")
        return jsonify({"status": "error", "message": f"An error occurred during upload: {e}"}), 500

    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    # This block is for local development only. Render uses gunicorn.
    app.run(debug=True)
  GNU nano 7.2                                                                 local_server.py                                                                           
import os
from flask import Flask, request, jsonify
from mega import Mega

# --- CONFIGURATION (Render uses these environment variables) ---
# NOTE: Render will require you to set these values in its dashboard
MEGA_EMAIL = os.environ.get('MEGA_EMAIL')
MEGA_PASSWORD = os.environ.get('MEGA_PASSWORD')
MEGA_FOLDER_NAME = os.environ.get('MEGA_FOLDER_NAME', 'Uploaded_Data')

app = Flask(__name__)

# --- MEGA LOGIN & INITIALIZATION ---
# This happens once when the server starts
try:
    # Attempt to log in to MEGA
    mega = Mega()
    m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)
    
    # Check if the destination folder exists, create it if not
    try:
        remote_folder = m.find(MEGA_FOLDER_NAME)
        if not remote_folder:
            print(f"MEGA folder '{MEGA_FOLDER_NAME}' not found. Creating it...")
            m.create_folder(MEGA_FOLDER_NAME)
            remote_folder = m.find(MEGA_FOLDER_NAME)
        print("Successfully connected to MEGA and located destination folder.")
    except Exception as e:
        print(f"Error finding/creating MEGA folder: {e}")
        remote_folder = None

except Exception as e:
