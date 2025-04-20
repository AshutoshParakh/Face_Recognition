import os
import base64
import logging
import numpy as np
from flask import Flask, request, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Enable CORS for all routes with specific allowed origins
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}})

# Directory to store images
IMAGE_DIR = os.path.join(os.getcwd(), 'images')
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Database configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'face_login',
}

# Registration route
@app.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.json
        logging.info(f"Received data: {data}")
        
        # Extracting fields from request
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        base64_str = data.get('image')
        face_encoding = data.get('face_encoding')  # Get face encoding as array

        # Check if any field is missing
        if not (name and email and phone and password and base64_str and face_encoding):
            missing_fields = []
            if not name:
                missing_fields.append('name')
            if not email:
                missing_fields.append('email')
            if not phone:
                missing_fields.append('phone')
            if not password:
                missing_fields.append('password')
            if not base64_str:
                missing_fields.append('image')
            if not face_encoding:
                missing_fields.append('face_encoding')
            logging.error(f"Missing fields: {missing_fields}")
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

        # Debug: Print the face encoding to inspect
        logging.info(f"Received face encoding: {face_encoding}")

        # Ensure face_encoding is a numpy array and check its size
        face_encoding_array = np.array(face_encoding, dtype=float)  # Convert to numpy array
        logging.info(f"Face encoding array size: {face_encoding_array.size}")  # Log the size

        # *** NEW ADDITION: Log the face encoding length during registration ***
        logging.info(f"Face encoding length during registration: {len(face_encoding)}")

        if face_encoding_array.size != 128:
            logging.error(f"Invalid face encoding size: {face_encoding_array.size}")
            return jsonify({'error': 'Invalid face encoding size. It must be 128 floats.'}), 400

        # Convert face encoding to bytes to store in the database
        face_encoding_bytes = face_encoding_array.astype(np.float64).tobytes()

        # Connect to MySQL database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Check if the user already exists
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            logging.error(f"User with email {email} already exists")
            return jsonify({'error': 'User already exists'}), 400

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Save the image
        img_data = base64.b64decode(base64_str.split(',')[1])  # Decode base64 image
        img_filename = f"{name.replace(' ', '_')}.jpg"  # Use a formatted name for the image
        img_path = os.path.join(IMAGE_DIR, img_filename)

        with open(img_path, 'wb') as img_file:
            img_file.write(img_data)

        # Store user data in database
        try:
            cursor.execute(
                "INSERT INTO user (name, email, phone, password, image, face_encoding, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, email, phone, hashed_password, img_filename, face_encoding_bytes, img_path)  # Save as bytes and path
            )
            conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")  # Log the database error
            return jsonify({'error': 'Failed to register user due to database error.'}), 500
        finally:
            cursor.close()
            conn.close()

        return jsonify({'message': 'User registered successfully!'}), 201

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")  # Log any unexpected error
        return jsonify({'error': f"Unexpected error: {str(e)}"}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
