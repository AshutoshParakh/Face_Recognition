import os
from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_cors import CORS
import base64
import numpy as np
import cv2
import face_recognition
from werkzeug.security import check_password_hash
import mysql.connector
from deepface import DeepFace

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

app = Flask(__name__)

# CORS settings
CORS(app, resources={r"/signin/*": {"origins": "http://127.0.0.1:5500"}})

# MySQL connection
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',  # your MySQL password
        database='face_login'
    )
    return connection

@app.route('/signin/image', methods=['POST'])
def signin_image():
    try:
        data = request.get_json()
        email = data.get('email')
        image_data = data.get('image')

        if not image_data:
            return jsonify({"error": "No image data provided"}), 400

        # Decode image (base64 without metadata)
        image_data = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_data, np.uint8)
        uploaded_image_path = "uploaded_image.jpg"  # Save uploaded image temporarily
        cv2.imwrite(uploaded_image_path, cv2.imdecode(np_arr, cv2.IMREAD_COLOR))

        # Check email and retrieve stored image path from DB
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT image_path FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        stored_image_path = user[0]

        # Validate stored image path
        if not os.path.exists(stored_image_path):
            print(f"Stored image does not exist: {stored_image_path}")
            return jsonify({"error": "Stored image does not exist"}), 404

        # Log the image paths for the verification process
        print(f"Comparing with stored image at: {stored_image_path}")
        print(f"Uploaded Image Path: {uploaded_image_path}")

        # Check if the uploaded image exists
        if not os.path.exists(uploaded_image_path):
            print(f"Uploaded image does not exist: {uploaded_image_path}")
            return jsonify({"error": "Uploaded image does not exist"}), 404

        # Read and check images
        uploaded_image = cv2.imread(uploaded_image_path)
        stored_image = cv2.imread(stored_image_path)

        if uploaded_image is None:
            raise ValueError("Uploaded image is not valid or could not be read.")
        if stored_image is None:
            raise ValueError("Stored image is not valid or could not be read.")

        # Compare the uploaded face image with the stored face image
        try:
            result = DeepFace.verify(uploaded_image_path, stored_image_path, model_name="VGG-Face")
            print(f"Verification Result: {result}")  # Log the result
        except Exception as e:
            print(f"DeepFace verification error: {str(e)}")
            return jsonify({"error": "Error during face verification: " + str(e)}), 500

        if result['verified']:
            return redirect(url_for('success_page'))
        else:
            return jsonify({"error": "Face does not match"}), 401

    except Exception as e:
        print(f"Error in signin_image: {str(e)}")  # Log the error
        return jsonify({"error": str(e)}), 500

@app.route('/signin', methods=['POST'])
def signin():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT password FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "Invalid email or password"}), 401

        stored_password_hash = user[0]
        
        if check_password_hash(stored_password_hash, password):
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success_page():
    return render_template('success.html')

if __name__ == "__main__":
    app.run(debug=True)
