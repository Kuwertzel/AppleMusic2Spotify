# AppleMusic2Spotify
This script can read public Apple Music playlists and create a mirrored playlists on Spotify. 

Personal playlists can be used too, as long as they are made publicly visible.

## Setup
1. Install a recent version of Python.
0. Install the python modules tekore and mechanicalsoup.
0. Follow [this guide](https://developer.spotify.com/documentation/web-api/concepts/apps) to register a new Spotify application using your Spotify account. Take note of the client ID, client secret and redirect URI.
0. Download both `applemusic2spotify.py` and `config.py` or clone this repo.
0. Put the Apple Music playlist URLs into the list in `config.py`.
0. Run `applemusic2spotify.py` put your Spotify app credentials into the cli.
0. A new tab in your default browser should open, displaying a Spotify authentication dialog. Click accept and copy the long URL you got redirected to.
0. Paste the URL into the cli and hit return.
0. The script should now create a file called `tekore.cfg` in the working directory. This file will from now on be used for automatic authentication.
0. The script should now the HTML of the Apple Music playlists, 

If you want to keep changes in the `config.py` when updating using `git pull`, rename the file to `config_dev.py`. This file is added to `.gitignore` so that changes to it will not be overridden/synced.
If `config_dev.py` is present, `config.py` will be ignored by the script.

## Note
I tested the script on Windows 11, however I don't think I used any platform-specific code. So Linux and Mac likely work fine, too!

The code is very basic and quite unfinished. I have not put much -if any- time into optimization (e.g. async execution).

Use at your own risk and feel free to adjust to your own preference.

This is my first project to be published on GitHub and I take it as an opportunity to learn about Git and GitHub :D
I'm happy about any and all recommendations on how I can improve this repo!
