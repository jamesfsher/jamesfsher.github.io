from flask import Flask, redirect, request, session, url_for, render_template
from urllib.parse import urlencode
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import jinja2
import config
from collections import Counter
import itertools

app = Flask(__name__)

# Client ID and secret from user app
Client_ID = config.Client_ID
Client_Secret = config.Client_Secret

# Set app secret key to random value
app.config['SECRET_KEY'] = os.urandom(64)
# Give a name to the session cookie
app.config['SESSION_COOKIE_NAME'] = "james cookie"
# Global var for access token
TOKEN_INFO = "token_info"   

# TODO: Create a HOME page

# TODO: Create a "Your top tracks" which uses spotify
# based on : https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-top-artists-and-tracks

# TODO: Create a Discover Weekly archiver
# Takes current users current Discover Weekly, and adds a playlist with those tracks


# Homepage
@app.route('/homepage')
def homepage():
    return render_template("homepage.html")

@app.route('/topTracks')
def topTracks():
    return render_template('topTracks.html')

@app.route('/dwArchiver')
def dwArchiver():
    return render_template('dwArchiver.html')

# Initial page for prompting user to authorize the app
@app.route('/')
def index():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# POST only page to get the refresh and access token
@app.route('/authorize')
def authorize():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    # Ensures user hasn't revoked access to app, which revokes refresh token
    # Link below to article exlaining error handling
    # https://developer.spotify.com/community/news/2016/07/25/app-ready-token-revoke/
    try:
        token_info = sp_oauth.get_access_token(code, check_cache=True)
    # If refresh token has been revoked, then new refresh token will be generated
    except:
        token_info = sp_oauth.get_access_token(code, check_cache=False)
        print("Refresh token revoked")
    # Updates global token info var to value obtained above
    session[TOKEN_INFO] = token_info
    return redirect(url_for('homepage', _external=True))

@app.route('/getLibrary')
def getLibrary():
    try:
        token_info = get_token()
    except:
        # If user reaches page via GET and isn't signed in, redirects to index
        print("User Not Logged In")
        redirect(url_for('index', _external=True))
    sp = spotipy.Spotify(auth = token_info['access_token']) 
    results = sp.current_user_playlists()
    playlists = {}
    for entry in results['items']:
        playlists[entry["name"]] = entry["id"]
    return render_template("getLibrary.html", playlists=playlists)

@app.route('/getTracks', methods=['GET', 'POST'])
def getTracks():
    # User reached page via POST
    if request.method == "POST":
        # Get access token
        try:
            token_info = get_token()
        except:
            # If user reaches page via GET and isn't signed in, redirects to index
            print("User Not Logged In")
            redirect(url_for('index', _external=True))
        # Get Spotify API Client using access token
        sp = spotipy.Spotify(auth = token_info['access_token'])
        # Obtain playlist from getLibrary.html form
        playlist = request.form.get("playlist")
        try:
            # Obtain playlist name
            results_playlist = sp.playlist(playlist)
            playlist_name = results_playlist['name']
        except:
            print("Cannot get playlist name")
            return render_template("whoops.html")
        try:
            # Use API Client to obtain playlist items
            results_track = sp.playlist_items(playlist)
        except:
            print("Cannot get playlist items")
            return render_template("whoops.html")
        # Initilize dict for tracks in the playlist
        # Format: [track:'name', artist:'name', album:'name', popularity:'number']
        track_info = []
        # Initialize list for artist ids in the playlist
        artist_id = []
        # Initialize second list in case the number of artists exceeds 50
        artist_id2 = []
        
        # Parse dict converted from json playlist information
        try:
            for entry in results_track['items']:
                if entry['track']:
                    # Gets track  id from json dict
                    track_id = entry['track']['id']
                    # Gets track popularity
                    track_popularity = entry['track']['popularity']
                    # Checks if artist id has reached maximum allowance for api client request
                    if len(artist_id) < 50:
                        # If maximum not reached, add track id to artist id variable
                        if entry['track']['artists'][0]['id']:
                            artist_id.append(entry['track']['artists'][0]['id'])
                    # If max number of artist ids reached, add to second variable (allows for maximum of 100 artist requests instead of 50)
                    elif len(artist_id2) < 50:
                        # Adds artist ids past max allowance to second artist id variable
                        if entry['track']['artists'][0]['id']:
                            artist_id2.append(entry['track']['artists'][0]['id'])
                    # Get current artists name
                    artist_name = entry['track']['artists'][0]['name']
                    # Get current album
                    album_name = entry['track']['album']['name']
                    # Add track information to dict to add to list of track information
                    if entry['track']['name']:
                        track_dict = {'track name':entry['track']['name'], 'artist name':artist_name, 'album name':album_name, 'track popularity':track_popularity}
                    track_info.append(track_dict)
        
        # If error when parsing playlist allow user to return to menu
        except:
            print("Cannot get tracks")
            return render_template("whoops.html")

        # return track_info
        # API request for artist information
        try:
            results_artist = sp.artists(artist_id)
        except:
            print("Cannot get artist info")
            return render_template('whoops.html')
        # List of all genres on the playlist
        genres = []
        # Add genres from API request to genres
        for entry in results_artist['artists']:
            genres.append(entry['genres'])
        # If there are more than 50 artists on the playlist, add genres from next 50
        if len(artist_id2) > 0:
            try:
                results_artist2 = sp.artists(artist_id2)
            except:
                print("Cannot get artist 2 info")
                return render_template('whoops.html')
            for entry in results_artist2['artists']:
                genres.append(entry['genres'])
        # Flattens list of genres
        merge_genres = itertools.chain.from_iterable(genres)
        # Creates dict of genres and their number of occurances
        num_genres = Counter(merge_genres)
        # Stores 5 most common genres as list
        genres_mostcommon = num_genres.most_common(5)
        # Stores 5 least common genres as a list
        genres_leastcommon = num_genres.most_common()[:-5-1:-1]
        return render_template('getTracks.html', track_info=track_info, genres_mostcommon=genres_mostcommon, genres_leastcommon=genres_leastcommon, playlist=playlist_name)
    else: 
        # User reached reached page via GET
        return redirect(url_for('getLibrary', _external=True))

# Function to get the SpotifyOauth url
# See Spotipy documeentation
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = Client_ID,
        client_secret = Client_Secret,
        scope = 'playlist-read-private',
        redirect_uri = 'http://127.0.0.1:5000/authorize')

# Function to obtain current token
def get_token():
    # Check current session for token
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # If no token in current session, raise exception
        raise "exception"
    # Current Unix time
    now = int(time.time())
    # T/F if token is expired
    is_expired = token_info['expires_at'] - now < 0
    if is_expired:
        sp_oauth = create_spotify_oauth()
        # Use refresh token to obtain new access token
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        print("Used refresh token")
    return token_info




