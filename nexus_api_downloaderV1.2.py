import requests
import hashlib # No longer strictly needed for calculation, but often imported with hash.
import os
import json
import re
import argparse
import tqdm

# --- Configuration ---
API_KEY_FILE = "key.txt"
DOWNLOAD_DIRECTORY = "downloads" # Subfolder to save downloaded files
# --- End Configuration ---

def load_api_key(filename):
    """Loads the API key from a specified text file."""
    try:
        with open(filename, 'r') as f:
            api_key = f.read().strip()
            if not api_key:
                raise ValueError("API key file is empty.")
            return api_key
    except FileNotFoundError:
        print(f"Error: API key file '{filename}' not found. Please create it and paste your key inside.")
        return None
    except ValueError as e:
        print(f"Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading API key: {e}")
        return None

def normalize_game_domain(game_name_from_wabbajack):
    """
    Normalizes game names from Wabbajack JSONs or user input to Nexus Mods API 'game_domain' slugs.
    Handles common variations and case insensitivity.
    """
    game_name_lower = game_name_from_wabbajack.lower()

    # Define mappings for variations
    mappings = {
        ("skyrimse", "skyrimspecialedition"): "skyrimspecialedition",
        ("skyrim", "skyrimlegendaryedition"): "skyrim", # For Oldrim
        ("fallout4",): "fallout4",
        ("falloutnewvegas", "falloutnv"): "falloutnv",
        # Add more if you encounter other variations in Wabbajack JSONs
    }

    for aliases, canonical_name in mappings.items():
        if game_name_lower in aliases:
            return canonical_name
    
    # Fallback: if not explicitly mapped, use the lowercased name as is.
    # This assumes that the input might already be a correct Nexus API domain name.
    return game_name_lower


def get_nexus_download_url(game_id, mod_id, file_id, api_key):
    """Fetches the temporary download link from Nexus Mods API."""
    
    # Normalize the game ID for the API
    game_domain_for_api = normalize_game_domain(game_id)

    url = f"https://api.nexusmods.com/v1/games/{game_domain_for_api}/mods/{mod_id}/files/{file_id}/download_link.json" # Added .json for explicit request
    headers = {"apikey": api_key}

    print(f"Requesting download link for {game_domain_for_api}/{mod_id}/{file_id}...")
    try:
        response = requests.get(url, headers=headers)
        
        if not response.ok: # Equivalent to response.status_code >= 400
            error_message = f"Nexus API error ({response.status_code}): "
            try:
                error_json = response.json()
                if "message" in error_json:
                    error_message += error_json["message"]
                else:
                    error_message += f"Unknown error format: {error_json}"
            except json.JSONDecodeError:
                error_message += f"Raw response: {response.text[:200]}..."
            print(f"Error getting download URL from Nexus API: {error_message}")
            return None

        if 'application/json' not in response.headers.get('Content-Type', '').lower():
            print(f"Error: Nexus API did not return JSON for success. Content-Type: {response.headers.get('Content-Type')}")
            print(f"Raw response: {response.text[:200]}...")
            return None

        download_link_data = response.json()

        if not isinstance(download_link_data, list) or not download_link_data:
            print(f"No valid download links found from Nexus API (empty or malformed list for Mod ID: {mod_id}, File ID: {file_id}). Response: {download_link_data}")
            return None
        
        # Prioritize "Direct Download" or "Primary Download" if available
        for link in download_link_data:
            if not isinstance(link, dict) or 'URI' not in link or 'name' not in link:
                print(f"  Warning: Invalid link object found in API response: {link}. Skipping.")
                continue 

            if "filedelivery.nexusmods.com" in link['URI']:
                 print(f"  Found direct download URI (filedelivery): {link['URI']}")
                 return link["URI"]
            elif link.get("short_name") == "Direct Download" or link.get("name") == "Primary Download":
                 print(f"  Found direct download URI (by name): {link['URI']}")
                 return link["URI"]

        # If no preferred link is found, try to use the first valid one
        first_valid_link = next((link['URI'] for link in download_link_data if isinstance(link, dict) and 'URI' in link), None)
        if first_valid_link:
            print(f"  Falling back to first available URI: {first_valid_link}")
            return first_valid_link
        
        print("No usable download URI found in the API response.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"A network/request error occurred while getting download URL: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from Nexus API (after successful request): {e}. Raw response: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_nexus_download_url: {e}")
        return None


def download_file(download_url, local_filename):
    """Downloads a file from a given URL with a progress bar."""
    os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
    local_filepath = os.path.join(DOWNLOAD_DIRECTORY, local_filename)

    print(f"Attempting to download '{local_filename}' from '{download_url}'...")
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            total_size_bytes = int(r.headers.get('content-length', 0))
            
            # Initialize tqdm progress bar
            with tqdm.tqdm(
                total=total_size_bytes, unit='B', unit_scale=True, desc=f"Downloading {local_filename}",
                ncols=100,  # Limits bar width for cleaner output
                miniters=1, # Update bar at least once per chunk
                ascii=True  # Use ASCII characters for compatibility
            ) as pbar:
                with open(local_filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: # Filter out keep-alive new chunks
                            f.write(chunk)
                            pbar.update(len(chunk)) # Update the progress bar

        print(f"\nSuccessfully downloaded '{local_filename}' to '{local_filepath}'")
        return True # Download success

    except requests.exceptions.RequestException as e:
        print(f"Error downloading file '{local_filename}': {e}")
        if os.path.exists(local_filepath):
            os.remove(local_filepath) # Clean up partially downloaded file
            print(f"  Removed partial file: {local_filepath}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        return False

# The calculate_file_hash function is no longer needed and has been removed.

def parse_wabbajack_json(filepath, filter_string=None):
    """
    Parses a Wabbajack modlist JSON file (specifically the 'Archives' structure)
    to extract Nexus download details.

    Args:
        filepath (str): The path to the .wabbajack.json file.
        filter_string (str, optional): A substring to filter results by (case-insensitive)
                                       in filename or game_domain.

    Returns:
        list: A list of dictionaries, where each dictionary contains
              extracted info for a Nexus archive, conforming to the
              'downloadables' format expected by the main script.
    """
    downloadable_files = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Wabbajack JSON file '{filepath}' not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{filepath}': {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while reading '{filepath}': {e}")
        return []

    archives = data.get('Archives')

    if archives is None:
        print("Could not find 'Archives' key at the root of the JSON. "
              "The JSON structure might be different than expected.")
        return []

    print(f"Found {len(archives)} archive entries in the JSON. Extracting Nexus details...")

    filter_lower = filter_string.lower() if filter_string else None # Prepare filter string for case-insensitive comparison

    for archive in archives:
        state = archive.get('State', {})
        state_type = state.get('$type', '')

        if "NexusDownloader" in state_type:
            mod_id = state.get('ModID')
            file_id = state.get('FileID')
            game_name = state.get('GameName') # This is the game_domain for Nexus
            filename = archive.get('Name') # Use 'Name' from the archive entry for filename
            
            # Basic validation for Nexus entries before processing them further
            if not (mod_id and file_id and game_name and filename):
                continue # Skip to next archive if essential data is missing

            # --- APPLY FILTER HERE ---
            # Only process (and print) files that pass the filter
            if filter_lower:
                if filter_lower not in filename.lower() and \
                   filter_lower not in game_name.lower():
                    continue # Skip this item if it doesn't match the filter
            
            downloadable_files.append({
                "game_domain": game_name,
                "mod_id": mod_id,
                "file_id": file_id,
                "filename": filename,
                # No expected_hash or hash_algo needed
            })

    return downloadable_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download mods from Nexus Mods using your API key. "
                    "Can operate in manual input mode or parse a Wabbajack JSON for bulk selection and filtering."
    )
    parser.add_argument(
        "--key",
        default=API_KEY_FILE,
        help=f"Path to your Nexus Mods API key file (default: {API_KEY_FILE})"
    )
    parser.add_argument(
        "--wabbajack-json",
        help="Path to a Wabbajack modlist JSON file for bulk download selection. "
             "If provided, manual input mode is skipped."
    )
    parser.add_argument(
        "--filter",
        help="Filter the Wabbajack JSON Nexus mod results by a substring in the filename or game name (case-insensitive). "
             "Only applies when --wabbajack-json is used."
    )
    args = parser.parse_args()

    api_key = load_api_key(args.key)
    if not api_key:
        exit("Exiting. Please ensure your API key is correctly set up.")

    print("\n--- Nexus Mods Downloader ---")
    print(f"Files will be saved to: {os.path.abspath(DOWNLOAD_DIRECTORY)}")

    if args.wabbajack_json:
        # --- Wabbajack JSON Parsing Mode ---
        print(f"\nParsing Wabbajack JSON: {args.wabbajack_json}")
        downloadables = parse_wabbajack_json(args.wabbajack_json, args.filter)

        if not downloadables:
            print("No downloadable Nexus files found in the Wabbajack JSON matching the criteria. Exiting.")
            exit(0)

        print("\nFound the following downloadable Nexus files:")
        for i, item in enumerate(downloadables):
            print(f"  {i+1}. {item['filename']} (Game: {item['game_domain']}, Mod ID: {item['mod_id']})")

        while True:
            try:
                selection = input("\nEnter the number of the file to download (or 'all', 'q' to quit): ").strip().lower()
                if selection == 'q':
                    print("Exiting.")
                    break
                elif selection == 'all':
                    selected_items = downloadables
                    print("Downloading all detected files...")
                else:
                    selected_index = int(selection) - 1
                    if 0 <= selected_index < len(downloadables):
                        selected_items = [downloadables[selected_index]]
                    else:
                        print(f"Invalid selection. Please enter a number between 1 and {len(downloadables)}, 'all', or 'q'.")
                        continue

                for item_to_download in selected_items:
                    game_id = item_to_download["game_domain"]
                    mod_id = item_to_download["mod_id"]
                    file_id = item_to_download["file_id"]
                    filename = item_to_download["filename"]

                    print(f"\n--- Initiating Download for: {filename} ---")
                    nexus_download_uri = get_nexus_download_url(game_id, mod_id, file_id, api_key)

                    if nexus_download_uri:
                        download_success = download_file(
                            nexus_download_uri,
                            filename
                        )
                        if download_success:
                            print(f"\nDownload complete for '{filename}'.")
                        else:
                            print(f"\nFailed to download '{filename}'.")
                    else:
                        print(f"\nCould not obtain Nexus download link for {filename}. Download aborted.")
                
                if selection != 'all':
                    break # Exit after a single selected download is complete
                # If 'all' was selected, the loop will complete and then break outside

            except ValueError:
                print("Invalid input. Please enter a number, 'all', or 'q'.")
            except Exception as e:
                print(f"An unexpected error occurred during selection: {e}")
                continue
        
    else:
        # --- Manual Input Mode (Original behavior) ---
        print("\n--- Manual Download Mode ---")
        game_id = input("Enter Nexus Games ID (e.g., 'skyrimse'): ").strip()
        mod_id_str = input("Enter Nexus Mod ID (e.g., '12345'): ").strip()
        file_id_str = input("Enter Nexus File ID (e.g., '67890'): ").strip()
        filename = input("Enter desired local filename (e.g., 'MyAwesomeMod.zip'): ").strip()
        # Hash input prompts removed


        try:
            mod_id = int(mod_id_str)
            file_id = int(file_id_str)
        except ValueError:
            print("Error: Mod ID and File ID must be integers.")
            exit(1)

        print("\n--- Initiating Download ---")

        nexus_download_uri = get_nexus_download_url(game_id, mod_id, file_id, api_key)

        if nexus_download_uri:
            download_success = download_file(
                nexus_download_uri,
                filename
            )
            if download_success:
                print(f"\nDownload complete for '{filename}'.")
            else:
                print(f"\nFailed to download '{filename}'.")
        else:
            print("\nCould not obtain Nexus download link. Download aborted.")