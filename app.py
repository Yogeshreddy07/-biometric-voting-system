# app.py
import os
import cv2
import face_recognition
from flask import Flask, request, render_template, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16 MB

# Create the upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Function to initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            voter_id TEXT NOT NULL UNIQUE,
            address TEXT NOT NULL,
            photo TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leader_name TEXT NOT NULL,
            party_name TEXT NOT NULL,
            logo TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT NOT NULL,
            candidate_id INTEGER NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'voter' in request.form:
            # Handle voter addition
            name = request.form['voter_name']
            voter_id = request.form['voter_id']
            address = request.form['voter_address']
            photo = request.files['voter_photo']  # Get the uploaded file

            # Validate voter inputs
            if not name or not voter_id or not address or not photo:
                flash('All voter fields are required!', 'error')
                return redirect(url_for('admin'))

            # Save the uploaded photo
            photo_filename = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            photo.save(photo_filename)

            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO voters (name, voter_id, address, photo)
                    VALUES (?, ?, ?, ?)
                ''', (name, voter_id, address, photo_filename))
                conn.commit()
                flash('Voter added successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('Voter ID must be unique!', 'error')
            except Exception as e:
                flash('Error occurred while adding voter!', 'error')
            finally:
                conn.close()

        elif 'candidate' in request.form:
            # Handle candidate addition
            leader_name = request.form['leader_name']
            party_name = request.form['party_name']
            logo = request.files['logo']  # Get the uploaded file

            # Validate candidate inputs
            if not leader_name or not party_name or not logo:
                flash('All candidate fields are required!', 'error')
                return redirect(url_for('admin'))

            # Save the uploaded logo
            logo_filename = os.path.join(app.config['UPLOAD_FOLDER'], logo.filename)
            logo.save(logo_filename)

            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO candidates (leader_name, party_name, logo)
                    VALUES (?, ?, ?)
                ''', (leader_name, party_name, logo_filename))
                conn.commit()
                flash('Candidate added successfully!', 'success')
            except Exception as e:
                flash('Error occurred while adding candidate!', 'error')
            finally:
                conn.close()

    return render_template('admin.html')

@app.route('/voter', methods=['GET', 'POST'])
def voter():
    if request.method == 'POST':
        # Capture the face from webcam
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        
        if ret:
            # Save captured image for recognition
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_image.jpg')
            cv2.imwrite(image_path, frame)

            # Release the video capture
            video_capture.release()
            cv2.destroyAllWindows()

            # Load all voter images for recognition
            known_face_encodings = []
            known_face_ids = []
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT voter_id, photo FROM voters')
            voters = cursor.fetchall()
            for voter_id, photo in voters:
                image = face_recognition.load_image_file(photo)
                encoding = face_recognition.face_encodings(image)[0]
                known_face_encodings.append(encoding)
                known_face_ids.append(voter_id)

            # Load the captured image
            captured_image = face_recognition.load_image_file(image_path)
            captured_face_encoding = face_recognition.face_encodings(captured_image)[0]

            # Compare the faces
            matches = face_recognition.compare_faces(known_face_encodings, captured_face_encoding)

            if True in matches:
                first_match_index = matches.index(True)
                matched_voter_id = known_face_ids[first_match_index]

                # Redirect to voting page with matched voter ID
                return redirect(url_for('voting_page', voter_id=matched_voter_id))
            else:
                flash('No matching voter found!', 'error')
                return redirect(url_for('voter'))

    return render_template('voter.html')

@app.route('/voting/<voter_id>', methods=['GET', 'POST'])
def voting_page(voter_id):
    if request.method == 'POST':
        candidate_id = request.form['candidate_id']
        # Store the vote
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO votes (voter_id, candidate_id) VALUES (?, ?)', (voter_id, candidate_id))
        conn.commit()
        conn.close()
        flash('Vote cast successfully!', 'success')
        return redirect(url_for('voter'))

    # Fetch voter details
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voters WHERE voter_id = ?', (voter_id,))
    voter_data = cursor.fetchone()

    # Fetch candidates
    cursor.execute('SELECT * FROM candidates')
    candidates = cursor.fetchall()
    conn.close()

    return render_template('voting_page.html', voter=voter_data, candidates=candidates)

@app.route('/admin/results', methods=['GET'])
def admin_results():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Query to get candidate results
    cursor.execute('''
        SELECT c.leader_name, c.party_name, COUNT(v.candidate_id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        GROUP BY c.id
    ''')
    results = cursor.fetchall()
    conn.close()

    return render_template('admin_results.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)