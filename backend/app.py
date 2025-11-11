import os
import psycopg2
import psycopg2.pool
import jwt
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from functools import wraps
from pdf_utils import (
    merge_pdfs, split_pdf, convert_pdf_to_word,
    convert_word_to_pdf, compress_pdf, unlock_pdf,
    protect_pdf
)
import io

# Load environment variables from .env file (for local development)
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- Dynamic CORS Configuration ---
# Get the frontend URL from an environment variable, with a fallback for local development
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
CORS(app, resources={r"/api/*": {"origins": FRONTEND_URL}})

# --- App Configuration ---
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# --- Database Connection Pool ---
pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)

def get_db_connection():
    return pool.getconn()

def release_db_connection(conn):
    pool.putconn(conn)

# --- JWT Authorization Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# --- API Endpoints ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, hashed_password))
            conn.commit()
    except psycopg2.IntegrityError:
        return jsonify({"error": "An unknown error occurred."}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)
    return jsonify({"message": "Account created successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, password_hash FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)
    if user and bcrypt.check_password_hash(user[1], password):
        token = jwt.encode({'user_id': str(user[0]), 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['JWT_SECRET_KEY'], algorithm="HS256")
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401

# --- PDF Operations ---
@app.route('/api/merge', methods=['POST'])
@token_required
def merge_files(current_user_id):
    if 'files' not in request.files: return jsonify({'error': 'No files part'}), 400
    files = request.files.getlist('files')
    if len(files) < 2: return jsonify({'error': 'Please upload at least two files to merge'}), 400
    try:
        merged_pdf_stream = merge_pdfs([f.stream for f in files])
        return send_file(merged_pdf_stream, as_attachment=True, download_name='merged.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/split', methods=['POST'])
@token_required
def split_file(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    if 'ranges' not in request.form: return jsonify({'error': 'No page ranges provided'}), 400
    file, ranges = request.files['file'], request.form['ranges']
    try:
        split_pdf_stream = split_pdf(file.stream, ranges)
        return send_file(split_pdf_stream, as_attachment=True, download_name='split.pdf', mimetype='application/pdf')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/pdf-to-word', methods=['POST'])
@token_required
def pdf_to_word_route(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    try:
        word_stream = convert_pdf_to_word(file.stream)
        filename = file.filename.rsplit('.', 1)[0] + '.docx'
        return send_file(word_stream, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        return jsonify({'error': f'An error occurred during conversion: {str(e)}'}), 500

@app.route('/api/word-to-pdf', methods=['POST'])
@token_required
def word_to_pdf_route(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    try:
        pdf_stream = convert_word_to_pdf(file.stream)
        filename = file.filename.rsplit('.', 1)[0] + '.pdf'
        return send_file(pdf_stream, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': f'An error occurred during conversion: {str(e)}'}), 500

@app.route('/api/compress', methods=['POST'])
@token_required
def compress_route(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    level = request.form.get('level', 'medium')
    try:
        compressed_stream = compress_pdf(file.stream, level)
        return send_file(compressed_stream, as_attachment=True, download_name='compressed.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': f'An error occurred during compression: {str(e)}'}), 500

@app.route('/api/unlock', methods=['POST'])
@token_required
def unlock_route(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    if 'password' not in request.form: return jsonify({'error': 'Password is required'}), 400
    file, password = request.files['file'], request.form['password']
    try:
        unlocked_stream = unlock_pdf(file.stream, password)
        return send_file(unlocked_stream, as_attachment=True, download_name='unlocked.pdf', mimetype='application/pdf')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/protect', methods=['POST'])
@token_required
def protect_route(current_user_id):
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    if 'password' not in request.form: return jsonify({'error': 'Password is required'}), 400
    file, password = request.files['file'], request.form['password']
    try:
        protected_stream = protect_pdf(file.stream, password)
        return send_file(protected_stream, as_attachment=True, download_name='protected.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)