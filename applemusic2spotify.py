import json
import os
import mechanicalsoup
from dataclasses import dataclass
import tekore as tk

try:
    from config_dev import applemusic_playlist_urls
except ImportError:
    from config import applemusic_playlist_urls

# --- Spotify authentication ---------------------------
# generate token if tekore.cfg does not exist
if not os.path.isfile('tekore.cfg'):
    print('tecore.cfg could not be found. This file is used to store the user authentication details for later use. Please input your API credentials to create the tecore.cfg file.')
    client_id = input('Spotify app client ID: ')
    client_secret = input('Spotify app client secret: ')
    redirect_uri = input('Spotify app redirect URI: ')
    user_token = tk.prompt_for_user_token(client_id, client_secret, redirect_uri, scope=tk.scope.every)
    conf = (client_id, client_secret, redirect_uri, user_token.refresh_token)
    tk.config_to_file('tekore.cfg', conf)

# load token from tekore.cfg
conf = tk.config_from_file('tekore.cfg', return_refresh=True)
user_token = tk.refresh_user_token(*conf[:2], conf[3])

spotify = tk.Spotify(user_token)


# --- Apple Music objects ------------------------------

@dataclass
class AppleMusicTrack:
    title: str
    artist: str

    @classmethod
    def from_dict(cls, track_dict):
        return cls(
            title=track_dict['title'],
            artist=track_dict['artistName'],
        )


@dataclass
class AppleMusicPlaylist:
    id: str
    url: str
    name: str
    author: str
    tracks: list[AppleMusicTrack]

    @classmethod
    def from_dict(cls, playlist_dict):
        tracks = []
        for track_dict in playlist_dict[0]['data']['sections'][1]['items']:
            tracks.append(AppleMusicTrack.from_dict(track_dict))

        return cls(
            id=playlist_dict[0]['data']['seoData']['appleContentId'],
            url=playlist_dict[0]['data']['canonicalURL'],
            name=playlist_dict[0]['data']['seoData']['schemaContent']['name'],
            author=playlist_dict[0]['data']['seoData']['schemaContent']['author']['name'],
            tracks=tracks,
        )


# --- Apple Music --------------------------------------


print('Loading Apple Music playlists')

# Create a MechanicalSoup browser object
browser = mechanicalsoup.StatefulBrowser()

applemusic_playlists = {}
for applemusic_playlist_url in applemusic_playlist_urls:
    # Navigate to the webpage
    print(f'  {applemusic_playlist_url}', end='')
    browser.open(applemusic_playlist_url)

    # Find the script tag with id 'serialized-server-data'
    script_element = browser.page.select_one('#serialized-server-data')

    # Extract the innerHTML if the script tag is found
    assert script_element
    inner_html = script_element.decode_contents()

    data = json.loads(inner_html)
    applemusic_playlist = AppleMusicPlaylist.from_dict(data)
    applemusic_playlists[applemusic_playlist.id] = applemusic_playlist
    print(f" → '{applemusic_playlists[applemusic_playlist.id].name}' with {len(applemusic_playlists[applemusic_playlist.id].tracks)} tracks")

browser.close()
print('All Apple Music playlists loaded.')

print('\n--------------\n')

# --- Spotify ------------------------------------------

# --- search for matching spotify playlists and create playlists as needed

# get all playlists
user_playlists: list[tk.model.SimplePlaylist] = list(spotify.all_items(spotify.followed_playlists()))

# filter playlists
applemusic_spotify_matches = {
    # applemusic_playlist.id: spotify_playlist_object
}

# --- match existing spotify playlist to their applemusic counterparts
for playlist in user_playlists:
    # skip any playlists owned by spotify directly
    if playlist.owner.id == 'spotify':
        continue

    # match the first playlist that contains the apple music playlist id in its description
    for applemusic_playlist in applemusic_playlists.values():
        if f'ID: {applemusic_playlist.id}' in playlist.description:
            applemusic_spotify_matches[applemusic_playlist.id] = playlist
            break

# --- create spotify playlists for unmatched applemusic playlists
matched_applemusic_playlist_ids = applemusic_spotify_matches.keys()
for applemusic_playlist in applemusic_playlists.values():
    if applemusic_playlist.id not in matched_applemusic_playlist_ids:
        print(f"Creating new playlist for '{applemusic_playlist.name}'...")
        playlist_description = f'AppleMusic mirror playlist. ID: {applemusic_playlist.id}'
        created_spotify_playlist = spotify.playlist_create(
            user_id=spotify.current_user().id,
            name=applemusic_playlist.name,
            public=False,
            description=playlist_description
        )

        # sometimes, the description cannot be set. the only thing that seems to help is to re-create the playlist.
        attempts = 1
        while created_spotify_playlist.description != playlist_description:
            print(f'  attempt {attempts} failed.')
            print('  removing bugged playlist...')
            spotify.playlist_unfollow(created_spotify_playlist.id)

            print('  creating playlist again...', end='')
            created_spotify_playlist = spotify.playlist_create(
                user_id=spotify.current_user().id,
                name=applemusic_playlist.name,
                public=False,
                description=playlist_description
            )
            print(f' → {created_spotify_playlist.uri}')
            attempts += 1
            if attempts > 10:
                raise Exception(f'Playlist description could not be set after {attempts} attempts')

        # add to dict of matched playlists
        applemusic_spotify_matches[applemusic_playlist.id] = created_spotify_playlist
        print(f'  → New Spotify playlist for {created_spotify_playlist.name} created: {created_spotify_playlist.uri}')

    else:
        print(f"Spotify playlist for '{applemusic_playlist.name}' already exists: {applemusic_spotify_matches[applemusic_playlist.id].uri}")

print('Matched all playlists.')

# --- find and add tracks to each playlist
print('Adding tracks to all playlists')
for applemusic_playlist in applemusic_playlists.values():
    spotify_playlist = applemusic_spotify_matches[applemusic_playlist.id]

    print(f"\ncollecting tracks for '{applemusic_playlist.name}':")
    track_uris = []
    for applemusic_track in applemusic_playlist.tracks:
        track_found = False

        # find track by searching for each of the queries if the previus did not yield a result
        track_search_queries = [
            f'track:{applemusic_track.title} artist:{applemusic_track.artist}',
            f'{applemusic_track.title} - {applemusic_track.artist}',
            f'{applemusic_track.artist} track:{applemusic_track.title}',
        ]
        for track_search_query in track_search_queries:
            if track_found: break

            found_tracks = spotify.search(query=track_search_query, types=('track',), limit=5)[0].items
            if len(found_tracks) != 0:
                for found_track in found_tracks:
                    if found_track.name == applemusic_track.title:
                        print(f"  ✅ search for '{track_search_query}' found exact match: {found_track.name} by {found_track.artists[0].name} ({found_track.uri})")
                        track_uris.append(found_track.uri)
                        track_found = True
                        break
                else:
                    print(f"  ⚠️search for '{track_search_query}' found similar match: {found_tracks[0].name} by {found_tracks[0].artists[0].name} ({found_tracks[0].uri})")
                    track_uris.append(found_tracks[0].uri)
                    track_found = True
                    break

        else:
            print(f"  ❌ track could not be found using any of the queries. ({track_search_queries})")

    # add tracks to the playlist (max 100 per API call)
    print(f'  → adding {len(track_uris)} tracks...')
    spotify.playlist_clear(spotify_playlist.id)
    for i in range(0, len(track_uris), 100):
        spotify.playlist_add(spotify_playlist.id, track_uris[i:i + 100])

print('DONE')
