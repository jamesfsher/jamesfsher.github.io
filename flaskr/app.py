from flask import Flask, redirect, request, session, url_for, render_template
from urllib.parse import urlencode
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import jinja2
import config

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
    return redirect(url_for('getLibrary', _external=True))

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
    if request.method == "POST":
        return "do something"
    else:
        return render_template("getTracks.html")

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




