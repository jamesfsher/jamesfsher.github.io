from flask import Flask, redirect, request, session, url_for, render_template
import requests
import urllib.parse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import jinja2
import config
from collections import Counter
import itertools
from datetime import datetime
import base64
import json
import random
import string


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

# Homepage
@app.route('/homepage')
def homepage():
    # Get access token
    try:
        token_info = get_token()
    except:
        # If user reaches page via GET and isn't signed in, redirects to index
        print("User Not Logged In")
        redirect(url_for('index', _external=True))
    # Get Spotify API Client using access token
    sp = spotipy.Spotify(auth = token_info['access_token'])
    # Get current user info
    results = sp.current_user()
    # Current user's name
    name = results["id"]
    # Current user profile picture
    pfp = results["images"][0]['url']
    # Render homepage using users name and profile picture
    return render_template("homepage.html", name=name, pfp=pfp)

@app.route('/topTracks')
def topTracks():
    # Get access token
    try:
        token_info = get_token()
    except:
        # If user reaches page via GET and isn't signed in, redirects to index
        print("User Not Logged In")
        redirect(url_for('index', _external=True))
    # Get Spotify API Client using access token
    sp = spotipy.Spotify(auth = token_info['access_token']) 

    # Initalize lists for top tracks and artists
    top_track_st = []
    top_track_mt = []    
    top_track_lt = []
    top_artist_lt = []
    
    # Top songs short term
    user_top_songs_st = sp.current_user_top_tracks(time_range="short_term")
    for entry in user_top_songs_st['items']:
        # Get current artists name
        artist_name = entry['artists'][0]['name']
        # Get current album
        album_name = entry['album']['name']
        # Add track information to dict to add to list of track information
        if entry['name']:
            track_dict = {'track name':entry['name'], 'artist name':artist_name, 'album name':album_name}
        top_track_st.append(track_dict)
    
    # Top songs medium term (6 months)
    user_top_songs_mt = sp.current_user_top_tracks(time_range="medium_term")
    for entry in user_top_songs_mt['items']:
        # Get current artists name
        artist_name = entry['artists'][0]['name']
        # Get current album
        album_name = entry['album']['name']
        # Add track information to dict to add to list of track information
        if entry['name']:
            track_dict = {'track name':entry['name'], 'artist name':artist_name, 'album name':album_name}
        top_track_mt.append(track_dict)

    # Top songs long term (all time)
    user_top_songs_lt = sp.current_user_top_tracks(time_range="long_term")
    for entry in user_top_songs_lt['items']:
        # Get current artists name
        artist_name = entry['artists'][0]['name']
        # Get current album
        album_name = entry['album']['name']
        # Add track information to dict to add to list of track information
        if entry['name']:
            track_dict = {'track name':entry['name'], 'artist name':artist_name, 'album name':album_name}
        top_track_lt.append(track_dict)

    # Top artists long term (all time)
    user_top_artists = sp.current_user_top_artists(time_range="long_term")
    for entry in user_top_artists['items']:
        artist_name = entry['name']
        top_artist_lt.append(artist_name)

    return render_template('topTracks.html', top_track_st=top_track_st, top_track_lt=top_track_lt, top_track_mt=top_track_mt, top_artist_lt=top_artist_lt)

# Discover Weekly Archiver
@app.route('/dwArchiver', methods=["GET", "POST"])
def dwArchiver():
    # If user reaches route via POST
    if request.method == "POST":
        try:
            # Get access token
            try:
                token_info = get_token()
            except:
                # If user reaches page via GET and isn't signed in, redirects to index
                print("User Not Logged In")
                redirect(url_for('index', _external=True))
            # Get Spotify API Client using access token
            sp = spotipy.Spotify(auth = token_info['access_token'])
            # Get current user information
            user_info = sp.current_user()
            # Get current user Spotify ID
            id = user_info["id"] 
            # Creates name of DW Archive playlist using current date
            name = "Discover Weekly Archive " + datetime.today().strftime('%Y-%m-%d')
            # Creates playlist using name variable on user's account
            sp.user_playlist_create(name=name, user=id, description="Archived tracks from the Discover Weekly Playlist")
            # Get JSON obj of current user's playlists
            playlists = sp.current_user_playlists()
            for entry in playlists['items']:
                # If current playlist in loop is the discvoer weekly playlist, store the playlist id
                if entry['name'] == "Discover Weekly":
                    dw_id = entry['id']
                # IF current playlist in loop the DW archive created via this request, store the playlist id
                if entry['name'] == name:
                    archive_id = entry['id']
            # Use Discover Weekly playlist id to obtain tracks on playlist
            dw_tracks = sp.playlist_items(playlist_id=dw_id)
            # Initialize list of dw track ids
            dw_id_list = []
            for entry in dw_tracks['items']:
                # Add dw tracks to list
                dw_id_list.append(entry['track']['id'])
            # Add tracks to DW archive created using its playlist id and the tracks obtained from current dw playlist
            sp.playlist_add_items(playlist_id=archive_id,items=dw_id_list) 
            # If all stages completed, return success page
            return render_template('success.html')
        # If error, handle by rendering failure page
        except:
            return render_template('whoops.html')
    else:
        return render_template('dwArchiver.html')

# Initial page for prompting user to authorize the app
@app.route('/')
def index():
    session.clear()
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# POST only page to get the refresh and access token
@app.route('/authorize')
def authorize():
    session.clear()
    sp_oauth = create_spotify_oauth()
    code = request.args.get('code')
    # Ensures user hasn't revoked access to app, which revokes refresh token
    # Link below to article exlaining error handling
    # https://developer.spotify.com/community/news/2016/07/25/app-ready-token-revoke/
    try:
        token_info = sp_oauth.get_access_token(code, check_cache=True)
    # If refresh token has been revoked, then new refresh token will be generated
    except:
        token_info = sp_oauth.get_access_token(code, check_cache=False)
        print("Refresh token revoked")    # Updates global token info var to value obtained above
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
# See Spotipy documentation
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = Client_ID,
        client_secret = Client_Secret,
        scope = 'playlist-read-private user-top-read playlist-modify-public',
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


# # Below is Oauth2 authorization workflow without the use of spotipy
# authorization_base_url = "https://accounts.spotify.com/authorize?"
# client_id2 = config.Client_ID
# redirect_uri = "http://127.0.0.1:5000/authorize"
# scope = "playlist-read-private"
# state = str(''.join(random.choices(string.ascii_uppercase +
#                              string.digits, k=16)))
# params = {
#     "client_id": client_id2,
#     "response_type": "code",
#     "redirect_uri": redirect_uri,
#     "scope": scope,
#     "state": state    
# }
# authorization_url = authorization_base_url + "&".join([f"{key}={value}" for key,value in params.items()])
# print(authorization_url)
# # here below should be in a callback route
# parsed_response = urllib.parse.urlparse(authorization_url)

# print(parsed_response)
# authorization_code = urllib.parse.parse_qs(parsed_response.query)["code"][0]

# print("authorization code: " + authorization_code)

# token_url = "https://accounts.spotify.com/api/token"
# client_secret2 = config.Client_Secret
# headers = {
#     "Authorization": "Basic" + base64.b64encode(f"{client_id2}:{client_secret2}".encode()).decode(),
#     "Content-Type": "application/x-www-form-urlencoded"
# }

# data = {
#     "grant_type": "authorization_code",
#     "code": authorization_code,
#     "redirect_uri": redirect_uri
# }

# response = requests.post(token_url, headers=headers, data=data)
# print("response: " + response)
