"""
views.py

This file defines the views blueprint for the Flask application.
It includes routes for the home page, dashboard, playlist songs, search, playlist creation,
browsing, adding songs to playlists, and various other actions related to the user interface.

Author: Matt Lucia
Date: 01/30/2024
"""
from flask import Blueprint, render_template, session, request, redirect, url_for, flash
import sqlite3
import random

# Create authentication blueprint
views = Blueprint('views', __name__)

# Set the database filename
DATABASE = 'HarmonyVault.db'

# Function to generate song suggestions based on playlist
def get_recommended_songs(playlist_id):
    # Retrieve song data from database
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    playlist_song_data = cur.execute(
        'SELECT song.title FROM song JOIN playlist_songs ON song.song_id = playlist_songs.song_id WHERE playlist_songs.playlist_id = ?', (playlist_id,)).fetchall()

    # Import necessary modules
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    # Load table into dataframe
    conn = sqlite3.connect(DATABASE)
    query = '''SELECT title, popularity, danceability, energy, loudness, speechiness, acousticness,
                instrumentalness, liveness, valence FROM song_data'''
    music_data = pd.read_sql_query(query, conn)

    # List of features to train model on
    features = ['popularity', 'danceability', 'energy', 'loudness', 'speechiness',
                'acousticness', 'instrumentalness', 'liveness', 'valence']
    music_data['combined_features'] = music_data.apply(
        lambda row: ' '.join([str(row[feature]) for feature in features]), axis=1)
    
    # Split data into training and testing sets
    train_data, test_data = train_test_split(
        music_data, test_size=0.2, random_state=42)

    train_data.reset_index(drop=True, inplace=True)

    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(
        train_data['combined_features'])

    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    def get_recommendations(song_names, cosine_sim=cosine_sim):
        song_indices = []

        # Get the indices of all input songs
        for song_name in song_names:
            song_index = train_data[train_data['title'] == song_name].index
            if not song_index.empty:
                song_indices.extend(song_index)

        # Aggregate similarity scores for all input songs
        aggregate_sim_scores = [0] * len(train_data)
        for song_index in song_indices:
            aggregate_sim_scores = [
                x + y for x, y in zip(aggregate_sim_scores, cosine_sim[song_index])]

        # Sort and get recommendations
        sim_scores = list(enumerate(aggregate_sim_scores))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        recommended_indices = [i[0] for i in sim_scores[1:11]]

        return train_data['title'].iloc[recommended_indices]

    playlist_song_data = [song[0] for song in playlist_song_data]

    # Generate suggested songs from playlist data
    recommendations = get_recommendations(playlist_song_data)
    results = str(recommendations).split('\n')
    d = {}
    for line in results:
        parts = list(filter(None, line.split()))

        number = parts[0]
        result = ' '.join(parts[1:])

        d[number] = result

    songs = list(d.values())[:-1]
    cur.execute('SELECT song.*, artist.name, album.title, album.image_url FROM song JOIN artist ON song.artist_id = artist.artist_id JOIN album ON song.album_id = album.album_id WHERE song.title IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', songs)
    recommended_songs = cur.fetchall()
    cur.close()
    conn.close()
    return recommended_songs

# Home route
@views.route('/', methods=['GET', 'POST'])
def home():
    user = session.get('user')
    featured_song = session.get('featured_song', '')
    if not featured_song:
        # Generate random featured song
        random_song_id = random.randint(339253, 345448)
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        featured_song = cur.execute(
            'SELECT song.*, artist.name, album.title, album.image_url FROM song JOIN artist ON song.artist_id = artist.artist_id JOIN album ON song.album_id = album.album_id WHERE song_id = ?', (random_song_id,)).fetchone()
        cur.close()
        conn.close()
        session['featured_song'] = featured_song
    return render_template('home.html', user=user, featured_song=featured_song)

# Route for Music Library
@views.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    user = session.get('user', {})
    if not user:
        return redirect((url_for('auth.login')))
    # Retrieve music data from database
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    if request.method == 'GET':
        playlists = cur.execute(
            'SELECT * FROM playlist WHERE user_id = ?', (user['user_id'],)).fetchall()
        return render_template('dashboard.html', playlists=playlists)
    cur.close()
    conn.close()
    return render_template('dashboard.html', user=user)

# Route for displaying playlist contents
@views.route('/playlist_songs/<playlist_id>', methods=['GET', 'POST'])
def playlist_songs(playlist_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Retrieve playlist content
    playlist = cur.execute(
        'SELECT * FROM playlist WHERE playlist_id = ?', (playlist_id,)).fetchone()
    playlist_songs = cur.execute(
        'SELECT song.*, artist.*, album.*  FROM playlist_songs JOIN song ON playlist_songs.song_id = song.song_id JOIN artist ON song.artist_id = artist.artist_id JOIN album ON song.album_id = album.album_id WHERE playlist_id = ?', (playlist_id,)).fetchall()

    # Generate suggested songs for the playlist
    recommended_songs = get_recommended_songs(playlist_id)

    cur.close()
    conn.close()
    return render_template('playlist_songs.html', playlist=playlist, playlist_songs=playlist_songs, recommendations=recommended_songs)

# Route for search
@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # Process search query
        search_query = request.form.get('search', '')
        order = request.form.get('order', '')
        if not order:
            order = 'song_id DESC'

        search_tokens = search_query.split(' ')

        # Retrieve search results from database
        query = f'''SELECT DISTINCT song.*, album.title, album.image_url, artist.name FROM song
                    JOIN album ON song.album_id = album.album_id
                    JOIN artist ON song.artist_id = artist.artist_id
                    WHERE {' AND '.join(['song.title LIKE ?' for _ in range(len(search_tokens))])}
                        OR {' AND '.join(['album.title LIKE ?' for _ in range(len(search_tokens))])}
                        OR {' AND '.join(['artist.name LIKE ?' for _ in range(len(search_tokens))])}
                    ORDER BY {order}'''

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        params = ['%' + token + '%' for token in search_tokens]

        cur.execute(query, params * 3)
        search_results = cur.fetchall()

        cur.close()
        conn.close()

        flash(f'Retrieved {len(search_results)} result(s) matching your search.', category="success")
        return render_template('search.html', search_results=search_results)
    else:
        search_results = session.get('search_results', '')
        if search_results:
            return render_template('search.html', search_results=search_results)
        return render_template('search.html')

# Route for playlist creation
@views.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    user = session.get('user', '')
    if not user:
        flash("Error. Not logged in.", category="error")
        return redirect(url_for('auth.login'))
    if request.method == "POST":
        # Retrieve new playlist data from form
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        imageURL = request.form.get('imageURL', '')

        user_id = session['user']['user_id']
        attributes = [user_id, title, description, imageURL]
        
        # Insert new playlist data to database
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        try:
            cur.execute(
                'INSERT INTO playlist (user_id, title, description, image_url) VALUES (?, ?, ?, ?)', attributes)
            conn.commit()
        except Exception:
            flash('Error creating new playlist', category="error")
            return redirect(url_for('views.dashboard'))

        cur.close()
        conn.close()
        flash('Playlist created.', category="success")
        return redirect(url_for('views.dashboard'))
    return render_template('create_playlist.html', user=user)

# Route to browse new music
@views.route('/browse')
def browse():
    user = session.get('user', '')
    if not user:
        flash('Error. No user found.', category='error')
        return redirect(url_for('views.home'))
    
    # Retrieve user library content
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    user_id = session['user']['user_id']
    playlist_id = cur.execute(
        'SELECT playlist_id FROM playlist WHERE user_id = ?', (user_id,)).fetchone()[0]

    # Genereate song suggestions based on user library content
    recommended_songs = get_recommended_songs(playlist_id)

    cur.close()
    conn.close()
    return render_template('browse.html', recommended_songs=recommended_songs)

# Route to add a song to specified playlist
@views.route('/add_song/<playlist_id>/<song_id>')
def add_song(playlist_id, song_id):
    # Add song to playlist in database
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    try:
        cur.execute(
            'INSERT INTO playlist_songs (playlist_id, song_id) VALUES (?, ?)', (playlist_id, song_id,))
        conn.commit()
    except Exception:
        flash('Error adding song to playlist.', category="error")
        return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))

    cur.close()
    conn.close()

    flash('Added song to playlist.', category='success')
    return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))

# Route to select playlist to add a specified song to
@views.route('/select_playlist/<song_id>', methods=['GET', 'POST'])
def select_playlist(song_id):
    user = session.get('user', '')
    if not user:
        return redirect(url_for('auth.login'))
    
    # Retrieve playlists options to display
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    user_id = session['user']['user_id']
    playlists = cur.execute(
        'SELECT * FROM playlist WHERE user_id = ?', (user_id,)).fetchall()

    cur.close()
    conn.close()

    return render_template('select_playlist.html', song_id=song_id, playlists=playlists)

# Route for deleting a specified playlist
@views.route('/delete_playlist/<playlist_id>')
def delete_playlist(playlist_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Prevent deletion for user library
    playlist_title = cur.execute(
        'SELECT title FROM playlist WHERE playlist_id = ?', (playlist_id)).fetchone()[0]
    if playlist_title == 'Library':
        flash('Cannot delete liked songs library.', category="error")
        return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))
    
    # Remove playlist from database
    try:
        cur.execute('DELETE FROM playlist WHERE playlist_id = ?',
                    (playlist_id,))
        conn.commit()
    except Exception:
        flash('Error deleting playlist.', category="error")
        return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))

    cur.close()
    conn.close()

    flash('Playlist deleted.', category="success")
    return redirect(url_for('views.dashboard'))

# Route to delete song from a specified playlist
@views.route('/delete_song/<playlist_id>/<song_id>')
def delete_song(playlist_id, song_id):
    # Delete song from playlist in database
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    try:
        cur.execute(
            'DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?', (playlist_id, song_id,))
        conn.commit()
    except Exception:
        flash('Error deleting playlist.', category="error")
        return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))

    cur.close()
    conn.close()

    flash('Song deleted.', category="success")
    return redirect(url_for('views.playlist_songs', playlist_id=playlist_id))

# Route to add/remove/update music data
@views.route('/change', methods=['GET', 'POST'])
def change():
    if request.method == 'POST':
        # Song data to add from form
        song_title = request.form.get('song_title')
        song_artist_id = request.form.get('song_artist_id')
        song_album_id = request.form.get('song_album_id')
        song_track_url = request.form.get('song_track_url')
        song_genre = request.form.get('song_genre')

        # Album data to add from form
        album_title = request.form.get('album_title')
        album_artist_id = request.form.get('album_artist_id')
        album_release_date = request.form.get('album_release_date')
        album_image_url = request.form.get('album_image_url')

        # Artist data to add from form
        artist_name = request.form.get('artist_name')
        artist_genre = request.form.get('artist_genre')

        # Song ID to remove from form
        remove_song_id = request.form.get('remove_song_id')

        # Album ID to remove from form
        remove_album_id = request.form.get('remove_album_id')

        # Artist ID to remove from form
        remove_artist_id = request.form.get('remove_artist_name')

        # Song data to update from form
        update_song_id = request.form.get('update_song_id')
        update_song_column = request.form.get('update_song_column')
        update_song_new_value = request.form.get('update_song_new_value')

        # Album data to update from form
        update_album_id = request.form.get('update_album_id')
        update_album_column = request.form.get('update_album_column')
        update_album_new_value = request.form.get('update_album_new_value')

        # Artist data to update from form
        update_artist_id = request.form.get('update_artist_id')
        update_artist_column = request.form.get('update_artist_column')
        update_artist_new_value = request.form.get('update_artist_new_value')

        conn = sqlite3.connect('Music.db')
        cur = conn.cursor()

        try:
            # Add new music data to database
            if song_title:
                query = f'''INSERT INTO song (album_id, artist_id, title, genre, spotify_url) VALUES (?, ?, ?, ?, ?)'''
                cur.execute(query, (song_album_id, song_artist_id,
                            song_title, song_genre, song_track_url))
                flash("Successfully inserted record.", category="success")
            elif album_title:
                query = f'''INSERT INTO album (artist_id, title, release_date, image_url) VALUES (?, ?, ?, ?)'''
                cur.execute(query, (album_artist_id, album_title,
                            album_release_date, album_image_url))
                flash("Successfully inserted record.", category="success")
            elif artist_name:
                query = f'''INSERT INTO artist (name, genre) VALUES (?, ?)'''
                cur.execute(query, (artist_name, artist_genre))
                flash("Successfully inserted record.", category="success")
            # Remove music data from database
            elif remove_song_id:
                query = f'''DELETE FROM song WHERE song_id = ?'''
                cur.execute(query, (remove_song_id,))
                flash("Successfully deleted record.", category="success")
            elif remove_album_id:
                query = '''DELETE FROM album Where album_id = ?'''
                cur.execute(query, (remove_album_id,))
                flash("Successfully deleted record.", category="success")
            elif remove_artist_id:
                query = f'''DELETE FROM artist WHERE artist_id = ?'''
                cur.execute(query, (remove_artist_id,))
                flash("Successfully deleted record.", category="success")
            # Update music data in database
            elif update_song_id:
                query = f'''UPDATE song SET {update_song_column} = "{
                    update_song_new_value}" WHERE song_id = {update_song_id}'''
                cur.execute(query)
                flash("Successfully updated record.", category="success")
            elif update_album_id:
                query = f'''UPDATE album SET {update_album_column} = "{
                    update_album_new_value}" WHERE album+id = {update_album_id}'''
                cur.execute(query)
                flash("Successfully updated record.", category="success")
            elif update_artist_id:
                query = f'''UPDATE Artist SET {update_artist_column} = "{
                    update_artist_new_value}" WHERE name = "{update_artist_id}"'''
                cur.execute(query)
                flash("Successfully updated record.", category="success")
        except Exception:
            flash(f"Error: Something went wrong.", category="error")
            return render_template('change.html')

        conn.commit()
        cur.close()
        conn.close()

        return render_template("change.html")
    else:
        return render_template("change.html")
