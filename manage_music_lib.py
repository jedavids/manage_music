import argparse
import pandas as pd
import re
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from IPython.display import display

class MusicManager:
    def __init__(self):
        # Initialize DataFrames and collections for artist and album data
        self.artist_data = pd.DataFrame()
        self.album_data = pd.DataFrame()
        self.seated_artist_data = []
        self.cleanup_review = pd.DataFrame()
        self.artist_name_mapping = {}
        self.exclude_artists = set()  

    # ---------- File Loading Methods ----------

    def load_artist_mapping(self, csv_file):
        """Load artist cleanup mapping from a CSV file (colon-separated)."""
        try:
            mapping_df = pd.read_csv(csv_file, sep=':')
            self.artist_name_mapping = dict(zip(mapping_df['Original Name'], mapping_df['Cleaned Name']))
            print(f"Artist cleanup mapping loaded from {csv_file}")
        except Exception as e:
            print(f"Error loading artist cleanup mapping: {e}")

    def load_artists(self, csv_file):
        """Load and clean artist data from a CSV file into a DataFrame."""
        try:
            self.artist_data = pd.read_csv(csv_file)
            self.artist_data['name'] = self.artist_data['name'].apply(self._clean_artist_name)
            print(f"Artist data loaded and cleaned from {csv_file}")
        except Exception as e:
            print(f"Error loading artist data: {e}")

    def load_albums(self, csv_file):
        """Load and clean album data, rename columns, apply cleanup rules, and track title changes."""
        try:
            album_data = pd.read_csv(csv_file)
            
            # Standardize column names for consistency
            album_data.rename(columns={'title': 'Album Title', 'artist': 'Artist', 'releasedDate': 'Release Date'}, inplace=True)
            
            # Preserve original album titles for comparison after cleaning
            album_data['Original Album Title'] = album_data['Album Title']
            
            # Format release dates and extract the year
            album_data['Release Date'] = pd.to_datetime(album_data['Release Date'], errors='coerce')
            album_data['Release Year'] = album_data['Release Date'].dt.year
            
            # Clean album titles and apply artist name cleanup
            album_data['Album Title'] = album_data['Album Title'].apply(self._clean_album_title)
            album_data['Artist'] = album_data['Artist'].apply(self._clean_artist_name)
            
            # Track changes by storing rows with modified album titles
            self.cleanup_review = album_data[album_data['Original Album Title'] != album_data['Album Title']][['Original Album Title', 'Album Title']]
            
            # Store final album data without the 'Original Album Title' column
            self.album_data = album_data.drop(columns=['Original Album Title'])
            print(f"Album data loaded and cleaned from {csv_file}")
            
        except Exception as e:
            print(f"Error loading album data: {e}")
    

    def load_exclude_artists(self, exclude_file):
        """Load, sort, and save a list of artists to exclude from a text file."""
        try:
            # Read each line, strip whitespace, and sort the artist names
            with open(exclude_file, 'r') as file:
                self.exclude_artists = sorted({line.strip() for line in file if line.strip()})

            # Write the sorted data back to the original file
            with open(exclude_file, 'w') as file:
                for artist in self.exclude_artists:
                    file.write(f"{artist}\n")
            
            print(f"Exclude list loaded and sorted from {exclude_file}")
        
        except Exception as e:
            print(f"Error loading exclude list: {e}")


    def load_seated_artists(self, filename, fetch=False, login_id=None):
        """
        Load artist data from a specified text file, or fetch from Seated if fetch=True.
        When fetching, the login_id is required.
        """
        if fetch and not login_id:
            raise ValueError("login_id is required when fetch=True")

        if fetch:
            try:
                driver = webdriver.Chrome()
                driver.get('https://go.seated.com/notifications/login')

                # Wait for the phone number field to be interactable
                phone_number_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Phone Number"]'))
                )
                phone_number_input.send_keys(login_id)

                # Tick the 'Verify you are human' checkbox if present
                try:
                    human_checkbox = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                '//span[contains(text(), "Verify you are human")]/preceding::input[@type="checkbox"][1]',
                            )
                        )
                    )
                    human_checkbox.click()
                except Exception:
                    pass

                verify_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[text()="Verify"]'))
                )
                verify_button.click()
                input("Press Enter to continue...")

                driver.get('https://go.seated.com/notifications')
                input("Press Enter to continue...")
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                remaining_text = re.split(r'Following \(\d+\)', page_text, maxsplit=1)[-1]
                remaining_text = re.sub(r'\nFollowing', '', remaining_text).strip()

                with open(filename, 'w') as file:
                    file.write(remaining_text)
                self.seated_artist_data = [line.strip() for line in remaining_text.splitlines() if line.strip()]
                print(f"Data fetched and saved to {filename}")
            except Exception as e:
                print(f"Error fetching data: {e}")
            finally:
                driver.quit()
        else:
            try:
                with open(filename, 'r') as file:
                    self.seated_artist_data = [line.strip() for line in file if line.strip()]
                print(f"Seated artist data loaded from {filename}")
            except Exception as e:
                print(f"Error loading seated artist data: {e}")

    # ---------- Data Processing and Cleanup Methods ----------

    def _clean_artist_name(self, name):
        """Apply the artist cleanup mapping to a given name."""
        return self.artist_name_mapping.get(name, name)

    def _clean_album_title(self, title):
        """Remove specific keywords within parentheses or brackets from album titles."""
        keywords = ["remaster", "deluxe", "bonus", "mix", "edition"]
        pattern = rf"\s*[\(\[][^()\[\]]*({'|'.join(keywords)})[^()\[\]]*[\)\]]"
        return re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

    def get_all_artists(self):
        """Return a DataFrame of unique cleaned artists with album counts, sorted alphabetically."""
        if self.artist_data.empty and self.album_data.empty:
            print("No artist or album data loaded.")
            return pd.DataFrame(columns=['Artist', 'Album Count'])

        try:
            artist_names = self.artist_data['name'].unique() if not self.artist_data.empty else np.array([])
            album_counts = self.album_data['Artist'].value_counts().to_frame('Album Count')
            album_counts.index.name = 'Artist'
            album_counts.reset_index(inplace=True)
            all_artists = pd.DataFrame(pd.unique(np.concatenate([artist_names, album_counts['Artist'].values])), columns=['Artist'])
            all_artists = all_artists.merge(album_counts, on='Artist', how='left').fillna(0).sort_values(by='Artist').reset_index(drop=True)
            all_artists['Album Count'] = all_artists['Album Count'].astype(int)
            return all_artists
        except KeyError as e:
            print(f"Error: Missing expected column(s) - {e}")
            return pd.DataFrame(columns=['Artist', 'Album Count'])

    def formatted_top_artists(self, num_albums=3):
        """Return a DataFrame of artists with at least 'num_albums' albums, sorted by album count."""
        all_artists = self.get_all_artists()
        if all_artists.empty:
            return pd.DataFrame(columns=['Artist', 'Album Count'])
        top_artists = all_artists[all_artists['Album Count'] >= num_albums].sort_values(by='Album Count', ascending=False)
        return top_artists.reset_index(drop=True)

    
    def formatted_album_info(self):
        """Return a DataFrame of cleaned album information, sorted by Artist and Release Date."""
        # Sort by Artist and Release Date before selecting columns
        sorted_album_data = self.album_data.sort_values(by=['Artist', 'Release Date'])
        
        # Select only the relevant columns after sorting
        return sorted_album_data[['Album Title', 'Artist', 'Release Year']].reset_index(drop=True)

    # def formatted_missing_seated_artists(self):
    #     """Return a DataFrame of artists missing from the seated list and not in the exclude list."""
    #     all_artists_df = self.get_all_artists()
    #     if all_artists_df.empty:
    #         print("No artist data available for comparison.")
    #         return pd.DataFrame(columns=['Missing Artist'])
    #     missing_artists = set(all_artists_df['Artist']) - set(self.seated_artist_data) - self.exclude_artists
    #     return pd.DataFrame(sorted(missing_artists), columns=['Missing Artist']).reset_index(drop=True)
    
    def formatted_missing_seated_artists(self):
        """Return a DataFrame of artists missing from the seated list and not in the exclude list."""
        all_artists_df = self.get_all_artists()
        if all_artists_df.empty:
            print("No artist data available for comparison.")
            return pd.DataFrame(columns=['Missing Artist'])
        
        # Ensure all components are sets
        missing_artists = set(all_artists_df['Artist']) - set(self.seated_artist_data) - set(self.exclude_artists)
        
        return pd.DataFrame(sorted(missing_artists), columns=['Missing Artist']).reset_index(drop=True)

    
    def formatted_missing_library_artists(self):
        """
        Return a DataFrame of artists that are in the seated data but not in the library.
        """
        # Ensure both seated artist data and library artist data are loaded
        all_artists_df = self.get_all_artists()
        if all_artists_df.empty:
            print("No artist data available in the library for comparison.")
            return pd.DataFrame(columns=['Missing Library Artist'])

        # Convert the seated artists and library artists to sets for easy comparison
        seated_artist_set = set(self.seated_artist_data)
        library_artist_set = set(all_artists_df['Artist'])
        
        # Find artists in seated but not in the library
        missing_library_artists = seated_artist_set - library_artist_set

        # Convert the result to a sorted DataFrame
        return pd.DataFrame(sorted(missing_library_artists), columns=['Missing Library Artist']).reset_index(drop=True)

    
    def formatted_cleanup_review(self):
        """Return a DataFrame showing the original and cleaned album names for review."""
        if self.cleanup_review.empty:
            return pd.DataFrame(columns=['Original Album Title', 'Album Title'])
        
        # Return the DataFrame with original and cleaned album titles
        return self.cleanup_review.reset_index(drop=True)
    
    def formatted_all_artists(self):
        """Return a DataFrame of all unique cleaned artists with album count, sorted alphabetically by artist name."""
        all_artists = self.get_all_artists()
        if all_artists.empty:
            return pd.DataFrame(columns=['Artist', 'Album Count'])
        
        # Sort by Artist for display
        return all_artists.sort_values(by='Artist').reset_index(drop=True)
    
    def formatted_exclude_artists(self):
        """Return the exclude artist list as a formatted DataFrame."""
        if not self.exclude_artists:
            return pd.DataFrame(columns=['Excluded Artist'])
        
        # Convert the exclude_artists set to a DataFrame
        exclude_artists_df = pd.DataFrame(sorted(self.exclude_artists), columns=['Excluded Artist'])
        return exclude_artists_df.reset_index(drop=True)
    
    def formatted_seated_artists(self):
        """Return a sorted DataFrame of seated artist data with a numeric index."""
        if not self.seated_artist_data:
            return pd.DataFrame(columns=['Seated Artist'])
        
        # Convert the seated_artist_data list to a sorted DataFrame
        sorted_seated_artists = sorted(self.seated_artist_data)
        return pd.DataFrame(sorted_seated_artists, columns=['Seated Artist']).reset_index(drop=True)



    # ---------- Export Methods ----------

    def export_missing_seated_artists(self, filename):
        """Export the list of missing seated artists to a text file, with each artist on a new line."""
        missing_artists_df = self.formatted_missing_seated_artists()
        if missing_artists_df.empty:
            print("No missing artists to export.")
            return
        try:
            with open(filename, 'w') as file:
                for artist in missing_artists_df['Missing Artist']:
                    file.write(f"{artist}\n")
            print(f"Missing artists exported to {filename}")
        except Exception as e:
            print(f"Error exporting missing artists: {e}")

# Example initialization and usage
if __name__ == "__main__":
    music_library = MusicManager()
    music_library.load_artist_mapping('artist_mapping.csv')
    music_library.load_artists('spotify_artists.csv')
    music_library.load_albums('spotify_albums.csv')
    music_library.load_exclude_artists('artist_exclude_list.txt')
    music_library.load_seated_artists('seated_artists.txt')

    
