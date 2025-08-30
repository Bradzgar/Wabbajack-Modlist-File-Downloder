# Nexus Mods Downloader (Wabbajack JSON Integrated)

A Python script designed to streamline the download of Nexus Mods files using the Nexus Mods API. This tool supports both manual single file downloads and automated bulk downloads by parsing Wabbajack modlist JSON files, complete with progress bars.

## Features

*   **Nexus Mods API Integration:** Directly fetches temporary download links from Nexus Mods (requires an API key).
*   **Wabbajack JSON Parsing:** Automatically extracts Nexus Mod IDs, File IDs, and Game domains from Wabbajack archive JSON files (e.g., `modlistname_archive.json`).
*   **Interactive Selection:** After parsing a Wabbajack JSON, select individual files by number, or download all detected Nexus mods.
*   **Download Progress Bar:** Visual progress displayed during downloads using `tqdm`.
*   **Flexible Game Domain Handling:** Normalizes various game name inputs to match Nexus Mods API requirements.
*   **Command-Line Arguments:** User-friendly interface with `--help`, `--wabbajack-json`, and `--filter` options.
*   **Filtering Capability:** Filter parsed Wabbajack Nexus mods by keywords in their name or game domain.

## Requirements

*  modlist.json - Extracted from the wabbajack modlist. /Wabbajack Install Directory/downloaded_mod_lists/TargetModlist.wabbajack .wabbajack file is just an archive that can be unzipped. I used 7zip. Go into the extracted folder and find modlist file (sort by size). The modlist file is just a json file. You will need the path to this file. I keep it in root directory for easy access. 
*   **Python 3.x:** Download from [python.org](https://www.python.org/downloads/).
*   **`requests` library:** For making HTTP requests to the Nexus Mods API and downloading files.
*   **`tqdm` library:** For displaying download progress bars.
    *   Install these using pip:
        ```bash
        pip install requests tqdm
        ```
*   **Nexus Mods Premium Membership (Recommended):** While the API *might* provide links without premium, consistent direct download links are largely a premium feature. More importantly, using the Nexus Mods API requires a **Public API Key**.
*   **Nexus Mods Public API Key:** This is mandatory for the script to function.

## Getting Your Nexus Mods API Key

1.  **Log in to Nexus Mods:** Go to [nexusmods.com](https://www.nexusmods.com) and log in to your account.
2.  **Access API Keys:** Navigate to your user profile settings. You can usually find the API key section under "Nexus API" or "My API Keys".
    *   Direct link: [https://www.nexusmods.com/users/myaccount?tab=api](https://www.nexusmods.com/users/myaccount?tab=api)
3.  **Generate a Public Key:** Look for a section to generate a "Public Key" or "API Key". Copy this key.
    *   **Important:** This key grants programmatic access to certain Nexus Mods features tied to your account. Treat it like a password.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    [git clone https://github.com/Bradzgar/Wabbajack-Modlist-File-Downloder.git
    cd Nexus-Mods-Downloader
    ```

2.  **Store Your API Key:** Open `key.txt` and paste your Nexus Mods Public API Key directly into it. Save and close the file.
    *   **CRITICAL SECURITY NOTE:** Never commit your `key.txt` file to a public GitHub repository or share it! It contains sensitive information. We have added `.gitignore` (below) to help prevent this.
      
3. Pip install dependencies.

## EXAMPLE USAGE
<img width="1041" height="269" alt="Screenshot 2025-08-29 230008" src="https://github.com/user-attachments/assets/a620e53d-8d68-4111-9250-b301608bf096" />
<img width="2020" height="217" alt="Screenshot 2025-08-29 230107" src="https://github.com/user-attachments/assets/e101408a-ccca-4b10-9f89-c55ee8169cd2" />



Files will be downloaded into a `downloads` subdirectory created in the same location as the script.

### Manual Download Mode

Run the script without any Wabbajack arguments. You will be prompted to enter the game ID, mod ID, file ID, and desired filename.

```bash
python nexus_api_downloader.py
