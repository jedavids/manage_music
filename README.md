# MusicManager Script Overview

The `MusicManager` class is a Python script designed to manage and clean up data from Spotify and the Seated platform. It loads artist and album information from CSV files, applies custom mappings and cleanup rules, and tracks changes for easy review. The class also supports exporting data and working with an exclude list for artists.

### Key Features
- Load and clean artist and album data.
- Apply custom artist name mappings and track cleaned titles.
- Fetch, display, and compare artist data with the Seated platform.
- Export missing or cleaned artist data to text files for external use.

---

### API Reference

#### Initialization
- `MusicManager()`: Initializes an instance of the `MusicManager` class with empty data attributes.

#### Data Loading Methods
- `load_artist_mapping(csv_file)`: Loads an artist cleanup mapping from a colon-separated CSV file.
- `load_artists(csv_file)`: Loads and cleans artist data from a CSV file.
- `load_albums(csv_file)`: Loads and cleans album data, applying cleanup rules and tracking title changes.
- `load_exclude_artists(exclude_file)`: Loads a list of excluded artists from a text file (one artist per line).
- `load_seated_artists(filename, fetch=False, login_id=None)`: Loads artist data from a specified text file. If `fetch=True`, fetches fresh data from Seated using the provided `login_id`.

#### Data Processing Methods
- `formatted_all_artists()`: Returns a DataFrame of unique cleaned artists with album counts, sorted alphabetically.
- `formatted_top_artists(num_albums=3)`: Returns a DataFrame of artists with at least `num_albums` albums, sorted by album count.
- `formatted_album_info()`: Returns a DataFrame of cleaned album information, sorted by Artist and Release Date.
- `formatted_cleanup_review()`: Returns a DataFrame showing the original and cleaned album names for review.
- `formatted_exclude_artists()`: Returns a DataFrame of artists in the exclude list.
- `formatted_seated_artists()`: Returns a DataFrame of artists loaded from the Seated platform.
- `formatted_missing_seated_artists()`: Returns a DataFrame of artists missing from the Seated list, excluding any artists in the exclude list.

#### Export Methods
- `export_missing_seated_artists(filename)`: Exports the list of missing seated artists to a text file, with each artist on a new line.
