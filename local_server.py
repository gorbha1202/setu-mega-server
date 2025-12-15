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
    print(f"ERROR: Could not log in to MEGA. Check environment variables. Error: {e}")
    m = None
    remote_folder = None


# --- FLASK ROUTES ---

@app.route('/', methods=['GET'])
def home():
    if m and remote_folder:
        return jsonify({"status": "Server and MEGA are connected.", "storage_plan": "20 GB Free"}), 200
    else:
        return jsonify({"status": "Server is running, but MEGA connection failed."}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    # 1. Check MEGA Connection
    if not m or not remote_folder:
        return jsonify({"message": "Server cannot upload: MEGA storage connection failed."}), 500

    # 2. Check for file in request
    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    if file:
        # 3. Save file temporarily on the local disk (REQUIRED for mega.py)
        # We save it to /tmp, which is designed for temporary use on cloud servers
        temp_filepath = os.path.join('/tmp', file.filename)
        file.save(temp_filepath)

        try:
            # 4. UPLOAD to MEGA storage
            m.upload(temp_filepath, remote_folder[0])
            
            # 5. CLEANUP: Delete the temporary local file immediately
            os.remove(temp_filepath)
            
            return jsonify({
                "message": "File uploaded successfully to MEGA storage.",
                "filename": file.filename,
                "remote_folder": MEGA_FOLDER_NAME
            }), 200

        except Exception as e:
            # 6. Error handling and cleanup if upload fails
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return jsonify({"message": f"MEGA upload failed: {e}"}), 500
