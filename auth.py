"""
auth.py

This file defines the authentication blueprint for the Flask application.
It includes routes for user login, signup, logout, account information, updating account details,
deleting the account, and updating the password.

Author: Matt Lucia
Date: 01/30/2024
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import re
import hashlib
import secrets
import sqlite3

# Create authentication blueprint
auth = Blueprint('auth', __name__)

# Set the database filename
DATABASE = 'HarmonyVault.db'

# Function to generate a random salt
def generate_salt():
    return secrets.token_hex(16)

# Function to hash a password using a provided salt
def hash_password(password, salt):
    combined = password + salt
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

# Route for user login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Check if a user is already logged in
    user = session.get('user')
    if user:
        return render_template('login.html', user=user)
    elif request.method == 'POST':
        # Handle user login
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        user = cur.execute(
            'SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if not user:
            flash('Username not found.', category='error')
            return redirect(url_for('auth.login'))
        hashed_password = hash_password(password, user[4])
        if hashed_password != user[3]:
            flash('Email and password do not match.', category='error')
        else:
            # Store user information in the session and redirect to the home page
            flash('Login successful.', category='success')
            session['user'] = {
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'date_of_birth': user[5],
                'admin': user[6]
            }
            cur.close()
            conn.close()
            return redirect(url_for('views.home'))
        cur.close()
        conn.close()
    return render_template('login.html')

# Route for user signup
@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    # Check if a user is already logged in
    user = session.get('user')
    if user:
        return render_template('sign-up.html', user=user)
    elif request.method == 'POST':
        # Handle user signup
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')
        date_of_birth = request.form.get('date_of_birth', '')

        # Validate input fields
        if not bool(re.match(r'^[a-zA-Z0-9_]{8,16}$', username)):
            flash('Username must be between 8-16 characters in length, and be composed of letters, numbers, and underscores.', category='error')
            return redirect(url_for('auth.signup'))
        if not bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,16}$', password1)):
            flash('Password must be between 8-16 characters, must contain at least one uppercase letter (A-Z), at least one lowercase letter (a-z), and at least one digit (0-9)', category='error')
            return redirect(url_for('auth.signup'))
        if password1 != password2:
            flash('Passwords do not match.', category='error')
            return redirect(url_for('auth.signup'))
        else:
            # Connect to the database
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()

            # Check if the username already exists
            username_exists = cur.execute(
                'SELECT * FROM user WHERE username = ?', (username,)).fetchone()
            if username_exists:
                flash('Username has already been registered.', category='error')
            else:
                # Generate salt and hash the password
                salt = generate_salt()
                hashed_password = hash_password(password1, salt)
                admin = 0

                # Insert user data into the database
                user_data = [username, email, hashed_password,
                             salt, date_of_birth, admin]
                try:
                    cur.execute(
                        'INSERT INTO user (username, email, hashed_password, salt, date_of_birth, admin) VALUES (?, ?, ?, ?, ?, ?)', user_data)
                    conn.commit()

                    # Retrieve user ID and create a default playlist for the user
                    user_id = cur.execute(
                        'SELECT user_id FROM user WHERE username = ?', (username,)).fetchone()[0]
                    playlist_data = [user_id, "Library", f"{username}'s music library.", "https://private-user-images.githubusercontent.com/97980526/300536850-f1a2daaf-027a-4889-b86d-c7bb5a774647.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MDY1NDY2NzcsIm5iZiI6MTcwNjU0NjM3NywicGF0aCI6Ii85Nzk4MDUyNi8zMDA1MzY4NTAtZjFhMmRhYWYtMDI3YS00ODg5LWI4NmQtYzdiYjVhNzc0NjQ3LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDAxMjklMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwMTI5VDE2MzkzN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWU0ZTUxNDkyZWI3NmQwYjE4YjVhZmYzOGFkOTFmMDg2N2Fm3YzYTBkYjNiNzg0MzU5ZTA4YzA1OWZlMGIwNjkxNjQmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.zpQK5uUbjZAJQPTZTeJkkEYM3iSG_7O1uj3epEjqUb4"]
                    cur.execute(
                        'INSERT INTO playlist (user_id, title, description, image_url) VALUES (?, ?, ?, ?)', playlist_data)
                    conn.commit()
                except Exception:
                    flash('Error creating account.', category='error')
                cur.close()
                conn.close()
                flash('Account creation successful.', category='success')
                return redirect(url_for('auth.login'))
            cur.close()
            conn.close()
    return render_template('signup.html')

# Route for user logout
@auth.route('logout')
def logout():
    session.clear()
    return render_template('home.html')

# Route for user account information
@auth.route("/account", methods=['GET', 'POST'])
def account():
    user = session.get('user', '')
    if not user:
        return redirect(url_for('auth.login'))
    if request.method == 'GET':
        # Retrieve user information from the session
        return render_template('account.html', user=user)

# Route for updating user account information
@auth.route('/update_account', methods=['POST'])
def update_account():
    if request.method == 'POST':
        # Retrieve updated user information from the form
        newUsername = request.form.get('newEmail', '')
        newEmail = request.form.get('newFirstName', '')
        confirmPassword = request.form.get('confirmPassword', '')

        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        # Retrieve user ID from the session
        user_id = session['user']['user_id']

        try:
            # Update user information in the database
            if newUsername:
                # Check if the new username is in valid format
                if not bool(re.match(r'^[a-zA-Z0-9_]{8,16}$', newUsername)):
                    flash(
                        'Username must be between 8-16 characters in length, and be composed of letters, numbers, and underscores.', category='error')
                    return redirect(url_for('auth.login'))
                # Check if the new username already exists
                user_check = cur.execute(
                    'SELECT * FROM users WHERE username = ?', (newUsername,)).fetchone()
                if user_check:
                    flash('Username already exists. Please try again.',
                          category='error')
                    return render_template('account.html', user=session['user'])
                else:
                    cur.execute(
                        'UPDATE users SET username= ? WHERE user_id = ?', (newUsername, user_id))
                    conn.commit()
                    session['user']['username'] = newUsername
            elif newEmail:
                cur.execute(
                    'UPDATE users SET email = ? WHERE user_id = ?', (newEmail, user_id,))
                session['user']['email'] = newEmail
            elif confirmPassword:
                user_data = cur.execute(
                    'SELECT * FROM user WHERE user_id = ?', (user_id,)).fetchone()
                user_salt = user_data[4]
                password_confirmation = hash_password(
                    confirmPassword, user_salt)
                if password_confirmation == user_data[3]:
                    return redirect(url_for('auth.update_password'))
                else:
                    flash('Error. Password incorrect.', category='error')
                    return redirect(url_for('auth.account'))
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            cur.close()
            conn.close()
            flash('Error updating account.', category="error")
            return redirect(url_for('auth.account'))
        flash('Account updated.', category='success')
        return redirect(url_for('auth.account'))

# Route for deleting user account
@auth.route('/delete_account')
def delete_account():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    user_id = session['user']['user_id']

    try:
        # Delete user account from the database
        cur.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception:
        flash('Error deleting account.', category='error')
        return redirect(url_for('auth.login'))

    flash('Account successfully deleted', category='success')
    return render_template('home.html')

# Route for updating user password
@auth.route('/update_password', methods=['POST', 'GET'])
def update_password():
    user = session.get('user')
    if not user:
        flash('Error. User not found.', category='error')
        return redirect(url_for('auth.account'))
    if request.method == "GET":
        return render_template('update_password.html')
    if request.method == "POST":
        updatePassword1 = request.form.get('updatePassword1', '')
        updatePassword2 = request.form.get('updatePassword2', '')
        if not updatePassword1 == updatePassword2:
            flash(
                'Password and confirmation do not match. Please try again.', category='error')
            return redirect(url_for('auth.account'))
        elif not bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,16}$', updatePassword1)):
            flash('Password must be between 8-16 characters, must contain at least one uppercase letter (A-Z), at least one lowercase letter (a-z), and at least one digit (0-9)', category='error')
            return redirect(url_for('auth.account'))
        else:
            user_id = user['user_id']
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()

            try:
                user_salt = cur.execute(
                    'SELECT salt FROM user WHERE user_id = ?', (user_id,)).fetchone()[0]
                new_hashed_password = hash_password(updatePassword1, user_salt)

                cur.execute('UPDATE user SET hashed_password = ? WHERE user_id = ?',
                            (new_hashed_password, user_id,))
                conn.commit()
            except Exception:
                flash('Error updating password.', category='error')
                return redirect(url_for('auth.account'))

            cur.close()
            conn.close()

            flash('Password updated.', category='success')
            return redirect(url_for('auth.account'))
