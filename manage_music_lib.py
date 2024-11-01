import argparse
import pandas as pd
import re
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from IPython.display import display

class MusicManager:
    def __init__(self):
        self.artist_data = pd.DataFrame()
        self.album_data = pd.DataFrame()
        self.seated_artist_data = []
        self.cleanup_review = pd.DataFrame()
        self.artist_name_mapping = {}
        self.exclude_artists = set()  # Set to store artists to exclude from comparison

    def load_artist_mapping(self, csv_file):
        """Load artist cleanup mapping from a CSV file."""
        try:
            mapping_df = pd.read_csv(csv_file, sep=':')
            self.artist_name_mapping = dict(zip(mapping_df['Original Name'], mapping_df['Cleaned Name']))
            print(f"Artist cleanup mapping loaded successfully from {csv_file}")
        except Exception as e:
            print(f"Error loading artist cleanup mapping: {e}")

    def load_artists(self, csv_file):
        """Load and clean artist data from a CSV file into a DataFrame."""
        try:
            self.artist_data = pd.read_csv(csv_file)
            # Clean artist names using the loaded mapping
            self.artist_data['name'] = self.artist_data['name'].apply(self._clean_artist_name)
            print(f"Artist data loaded and cleaned successfully from {csv_file}")
        except Exception as e:
            print(f"Error loading artist data: {e}")

    def load_albums(self, csv_file):
        """Load and clean album data, and apply artist name cleanup."""
        try:
            album_data = pd.read_csv(csv_file)
            # Rename columns
            album_data.rename(columns={'title': 'Album Title', 'artist': 'Artist', 'releasedDate': 'Release Date'}, inplace=True)
            # Keep a copy of original album names for review
            album_data['Original Album Title'] = album_data['Album Title']
            # Convert 'Release Date' to datetime format and extract year for display purposes
            album_data['Release Date'] = pd.to_datetime(album_data['Release Date'], errors='coerce')
            album_data['Release Year'] = album_data['Release Date'].dt.year
            # Clean up album titles
            album_data['Album Title'] = album_data['Album Title'].apply(self._clean_album_title)
            # Apply artist name cleanup
            album_data['Artist'] = album_data['Artist'].apply(self._clean_artist_name)
            # Store only rows where the album title was changed
            self.cleanup_review = album_data[album_data['Original Album Title'] != album_data['Album Title']][['Original Album Title', 'Album Title']].copy()
            # Update album data without the 'Original Album Title' column
            self.album_data = album_data.drop(columns=['Original Album Title'])
            print(f"Album data loaded and cleaned successfully from {csv_file}")
        except Exception as e:
            print(f"Error loading album data: {e}")

    def load_exclude_artists(self, exclude_file):
        """Load a list of artists to exclude from comparison from a text file."""
        try:
            with open(exclude_file, 'r') as file:
                # Read each line, strip whitespace, and add to exclude_artists set
                self.exclude_artists = {line.strip() for line in file if line.strip()}
            print(f"Exclude list loaded successfully from {exclude_file}")
        except Exception as e:
            print(f"Error loading exclude list: {e}")


    def load_seated_artists(self, filename, fetch=False, login_id=None):
        """
        Load artist data from a specified text file by default.
        If fetch=True, fetch fresh data from the Seated platform using login_id, update the text file,
        and store the data in the seated_artist_data attribute.
        
        Parameters:
        - filename (str): The name of the file to read from or write to.
        - fetch (bool): Whether to fetch fresh data from Seated (default: False).
        - login_id (str): The login ID for Seated (required if fetch=True).
        """
        
        # Check if login_id is provided when fetch is True
        if fetch and not login_id:
            raise ValueError("login_id is required when fetch=True")

        if fetch:
            # Fetch fresh data from Seated
            try:
                driver = webdriver.Chrome()
                driver.get('https://go.seated.com/notifications/login')

                # Enter login ID dynamically
                phone_number_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Phone Number"]')
                phone_number_input.send_keys(login_id)
                verify_button = driver.find_element(By.XPATH, '//button[text()="Verify"]')
                verify_button.click()
                input("Press Enter to continue...")

                driver.get('https://go.seated.com/notifications')
                input("Press Enter to continue...")

                page_text = driver.find_element(By.TAG_NAME, 'body').text
                remaining_text = re.split(r'Following \(\d+\)', page_text, maxsplit=1)[-1]
                remaining_text = re.sub(r'\nFollowing', '', remaining_text).strip()

                # Write fetched data to the specified text file
                with open(filename, 'w') as file:
                    file.write(remaining_text)
                print(f"Text written successfully to {filename}")

                # Store data in the object
                self.seated_artist_data = [line.strip() for line in remaining_text.splitlines() if line.strip()]
            except Exception as e:
                print(f"An error occurred while fetching data: {e}")
            finally:
                driver.quit()
        else:
            # Read artist data from the specified text file
            try:
                with open(filename, 'r') as file:
                    self.seated_artist_data = [line.strip() for line in file if line.strip()]
                print(f"Seated artist data loaded successfully from {filename}")
            except Exception as e:
                print(f"Error loading seated artist data: {e}")


    def _clean_artist_name(self, name):
        """Clean artist name using the loaded mapping table."""
        return self.artist_name_mapping.get(name, name)

    def _clean_album_title(self, title):
        """Remove specified variations from album titles within parentheses or brackets."""
        # Define keywords to be removed
        keywords = ["remaster", "deluxe", 'bonus', 'mix', 'mix', 'edition']
        # Dynamically create the regex pattern with the keywords
        pattern = rf"\s*[\(\[][^()\[\]]*({'|'.join(keywords)})[^()\[\]]*[\)\]]"
        # Apply the regex substitution
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        return title.strip()

    def get_all_artists(self):
        """Return a DataFrame of all unique cleaned artists with album count, sorted alphabetically."""
        if self.artist_data.empty and self.album_data.empty:
            print("No artist or album data loaded.")
            return pd.DataFrame(columns=['Artist', 'Album Count'])
        
        try:
            artist_names = self.artist_data['name'].unique() if not self.artist_data.empty else np.array([])
            album_counts = self.album_data['Artist'].value_counts().to_frame('Album Count')
            album_counts.index.name = 'Artist'
            album_counts.reset_index(inplace=True)
            all_artists_array = np.concatenate([artist_names, album_counts['Artist'].values])
            all_artists = pd.DataFrame(pd.unique(all_artists_array), columns=['Artist'])
            all_artists = all_artists.merge(album_counts, on='Artist', how='left').fillna(0)
            all_artists['Album Count'] = all_artists['Album Count'].astype(int)
            all_artists = all_artists.sort_values(by='Artist').reset_index(drop=True)
            return all_artists
        except KeyError as e:
            print(f"Error: Missing expected column(s) - {e}")
            return pd.DataFrame(columns=['Artist', 'Album Count'])

    def formatted_top_artists(self, num_albums=3):
        """Return a DataFrame of artists with at least 'num_albums' albums, sorted by album count in descending order."""
        all_artists = self.get_all_artists()
        if all_artists.empty:
            return pd.DataFrame(columns=['Artist', 'Album Count'])

        # Filter and sort artists based on the album count threshold
        top_artists = all_artists[all_artists['Album Count'] >= num_albums]
        top_artists = top_artists.sort_values(by='Album Count', ascending=False).reset_index(drop=True)
        return top_artists

    def formatted_album_info(self):
        """Return a DataFrame of cleaned album information, sorted by Artist and Release Date."""
        if self.album_data.empty:
            return pd.DataFrame(columns=['Album Title', 'Artist', 'Release Year'])

        # Sort by Artist and Release Date and select columns for display
        sorted_album_data = self.album_data.sort_values(by=['Artist', 'Release Date'])
        display_columns = ['Album Title', 'Artist', 'Release Year']
        return sorted_album_data[display_columns].reset_index(drop=True)

    def formatted_all_artists(self):
        """Return a DataFrame of all unique cleaned artists with album count, sorted alphabetically by artist name."""
        all_artists = self.get_all_artists()
        if all_artists.empty:
            return pd.DataFrame(columns=['Artist', 'Album Count'])
        
        # Sort by Artist for display
        return all_artists.sort_values(by='Artist').reset_index(drop=True)

    def formatted_cleanup_review(self):
        """Return a DataFrame showing the original and cleaned album names for review."""
        if self.cleanup_review.empty:
            return pd.DataFrame(columns=['Original Album Title', 'Album Title'])
        
        return self.cleanup_review.reset_index(drop=True)

    def formatted_seated_artists(self):
        """Return a sorted DataFrame of seated artist data with a numeric index."""
        if not self.seated_artist_data:
            return pd.DataFrame(columns=['Seated Artist'])
        
        sorted_seated_artists = sorted(self.seated_artist_data)
        # Create DataFrame without setting an index
        return pd.DataFrame(sorted_seated_artists, columns=['Seated Artist']).reset_index(drop=True)
    
    def formatted_exclude_artists(self):
        """Return the exclude artist list as a formatted DataFrame."""
        if not self.exclude_artists:
            print("Exclude list is empty.")
            return pd.DataFrame(columns=['Excluded Artist'])
        
        # Convert the exclude_artists set to a DataFrame
        exclude_artists_df = pd.DataFrame(sorted(self.exclude_artists), columns=['Excluded Artist'])
        return exclude_artists_df.reset_index(drop=True)
    
    def formatted_missing_seated_artists(self):
        """
        Compare the all artists list to the seated artist list, 
        excluding artists found in the exclude list, and return 
        a DataFrame of artists missing from the seated list.
        """
        all_artists_df = self.get_all_artists()
        if all_artists_df.empty:
            print("No artist data available for comparison.")
            return pd.DataFrame(columns=['Missing Artist'])

        # Convert seated artists and exclude artists to sets for comparison
        seated_artist_set = set(self.seated_artist_data)
        all_artists_set = set(all_artists_df['Artist'])
        
        # Calculate the missing artists by excluding both seated and exclude lists
        missing_artists = all_artists_set - seated_artist_set - self.exclude_artists

        # Convert the result to a sorted DataFrame
        missing_artists_df = pd.DataFrame(sorted(missing_artists), columns=['Missing Artist'])
        return missing_artists_df.reset_index(drop=True)


    def load_seated_artist_data(self, fetch=False):
        """
        Retrieve artist data from a stored text file by default.
        If fetch=True, fetch fresh data from the Seated platform, update the text file, 
        and store the data in the seated_artist_data attribute.
        """
        filename = 'seated_artists.txt'
        
        if fetch:
            # Fetch fresh data from Seated
            try:
                driver = webdriver.Chrome()
                driver.get('https://go.seated.com/notifications/login')

                phone_number_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Phone Number"]')
                phone_number_input.send_keys('5088783947')  # Replace with actual phone number
                verify_button = driver.find_element(By.XPATH, '//button[text()="Verify"]')
                verify_button.click()
                input("Press Enter to continue...")

                driver.get('https://go.seated.com/notifications')
                input("Press Enter to continue...")

                page_text = driver.find_element(By.TAG_NAME, 'body').text
                remaining_text = re.split(r'Following \(\d+\)', page_text, maxsplit=1)[-1]
                remaining_text = re.sub(r'\nFollowing', '', remaining_text).strip()

                # Write fetched data to the text file
                with open(filename, 'w') as file:
                    file.write(remaining_text)
                print(f"Text written successfully to {filename}")

                # Store data in the object
                self.seated_artist_data = [line.strip() for line in remaining_text.splitlines() if line.strip()]
            except Exception as e:
                print(f"An error occurred while fetching data: {e}")
            finally:
                driver.quit()
        else:
            # Read artist data from the text file
            try:
                with open(filename, 'r') as file:
                    self.seated_artist_data = [line.strip() for line in file if line.strip()]
                print(f"Seated artist data loaded successfully from {filename}")
            except Exception as e:
                print(f"Error loading seated artist data: {e}")

        return self.seated_artist_data
    
    def export_missing_seated_artists(self, filename):
        """
        Export the list of missing seated artists to a text file, with each artist on a new line.
        
        Parameters:
        - filename (str): The name of the file to export the missing artists to.
        """
        # Get the missing seated artists as a DataFrame
        missing_artists_df = self.formatted_missing_seated_artists()
        
        if missing_artists_df.empty:
            print("No missing artists to export.")
            return

        # Export the list to a text file
        try:
            with open(filename, 'w') as file:
                for artist in missing_artists_df['Missing Artist']:
                    file.write(f"{artist}\n")
            print(f"Missing artists exported successfully to {filename}")
        except Exception as e:
            print(f"An error occurred while exporting missing artists: {e}")

# Example usage
def main():
    parser = argparse.ArgumentParser(description="Manage your Spotify music data.")
    parser.add_argument('-a', '--artists', type=str, metavar="CSV_FILE", help="Import Spotify artist data.")
    parser.add_argument('-l', '--albums', type=str, metavar="CSV_FILE", help="Import Spotify album data.")
    parser.add_argument('-m', '--mapping', type=str, metavar="CSV_FILE", help="Load artist cleanup mapping from a CSV file.")
    parser.add_argument('-s', '--seated', type=str, metavar="TXT_FILE", help="Import Seated artist data.")
    args = parser.parse_args()
    
    music_library = MusicManager()
    
    if args.mapping:
        music_library.load_artist_mapping(args.mapping)
    if args.artists:
        music_library.load_artists(args.artists)
    if args.albums:
        music_library.load_albums(args.albums)
    if args.seated:
        music_library.load_seated_artists(args.seated)
    
    # Display data as needed
    if args.albums:
        music_library.display_album_info()
        music_library.display_all_artists()
        music_library.review_cleanup()
    if args.seated:
        music_library.display_seated_artists()

if __name__ == "__main__":
    main()
