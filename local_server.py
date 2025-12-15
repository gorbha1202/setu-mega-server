import os
import tempfile
from functools import wraps
# UPDATED IMPORT: Added render_template, redirect, url_for
from flask import Flask, request, jsonify, render_template, redirect, url_for 
from mega import Mega

# --- 1. ENVIRONMENT VARIABLE SETUP ---

# Read environment variables for MEGA credentials
MEGA_EMAIL = os.environ.get('MEGA_EMAIL')
MEGA_PASSWORD = os.environ.get('MEGA_PASSWORD')
MEGA_FOLDER_NAME = os.environ.get('MEGA_FOLDER_NAME', 'Uploaded_Data')

# Read the secret API key for security
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

# MODIFIED ROOT ROUTE: Now renders the dashboard.html template
@app.route('/', methods=['GET'])
def index():
    m = login_mega()
    status_class = 'status-error'
    status_message = 'MEGA service is unavailable. Check credentials.'
    storage_used = None
    storage_total = None

    if m:
        try:
            storage = m.get_storage_space(giga=True)
            storage_used = round(storage['used'], 2)
            storage_total = round(storage['total'], 2)
            status_class = 'status-success'
            status_message = 'Server and MEGA are connected.'
        except Exception:
            status_message = 'MEGA connected, but failed to retrieve storage space.'

    # Handle messages passed from redirects (e.g., after an upload)
    message_text = request.args.get('message_text')
    message_class = request.args.get('message_class')
    
    return render_template(
        'dashboard.html',
        status_class=status_class,
        status_message=status_message,
        storage_used=storage_used,
        storage_total=storage_total,
        message_text=message_text,
        message_class=message_class
    )

# NEW ROUTE: Handles file uploads from the web browser form
@app.route('/upload_via_dashboard', methods=['POST'])
def upload_file_dashboard():
    m = login_mega()
    if m is None:
        return redirect(url_for('index', message_text="MEGA service is unavailable.", message_class="msg-error"))

    if 'file' not in request.files:
        return redirect(url_for('index', message_text="No file part in the request.", message_class="msg-error"))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index', message_text="No selected file.", message_class="msg-error"))
    
    filename = file.filename
    temp_file_path = None
    
    try:
        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            file.save(temp)
            temp_file_path = temp.name

        # Find or create the target folder
        mega_folder = m.find(MEGA_FOLDER_NAME)
        if not mega_folder:
            m.create_folder(MEGA_FOLDER_NAME)
            mega_folder = m.find(MEGA_FOLDER_NAME)

        # Upload the file to MEGA
        m.upload(temp_file_path, mega_folder[0])

        # Success redirect
        return redirect(url_for('index', message_text=f"Success! File '{filename}' uploaded to MEGA.", message_class="msg-success"))

    except Exception as e:
        app.logger.error(f"File upload failed: {e}")
        # Error redirect
        return redirect(url_for('index', message_text=f"Upload Failed: An error occurred ({e})", message_class="msg-error"))

    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# EXISTING SECURE ROUTE: Remains for API usage (not dashboard)
@app.route('/upload', methods=['POST'])
@require_api_key 
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

        mega_folder = m.find(MEGA_FOLDER_NAME)
        if not mega_folder:
            m.create_folder(MEGA_FOLDER_NAME)
            mega_folder = m.find(MEGA_FOLDER_NAME)

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
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    app.run(debug=True)
