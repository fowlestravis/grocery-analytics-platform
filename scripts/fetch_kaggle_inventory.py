import os
import logging
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAGGLE_API_URL = "https://www.kaggle.com/api/v1/datasets/download/willianoliveiragibin/grocery-inventory"
OUTPUT_DIR = Path("data/kaggle")
ENV_FILE = Path("config/.env")


def load_kaggle_token():
    """Load the Kaggle API token from the environment file."""
    if not ENV_FILE.exists():
        raise FileNotFoundError(f"Environment file not found: {ENV_FILE}")

    load_dotenv(ENV_FILE)
    token = os.getenv("KAGGLE_TOKEN")

    if not token:
        raise ValueError("KAGGLE_TOKEN not found in environment file")

    logger.info("Kaggle token loaded successfully")
    return token


def download_dataset(token):
    """Download the dataset from Kaggle API."""
    logger.info(f"Downloading dataset from {KAGGLE_API_URL}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(KAGGLE_API_URL, headers=headers, stream=True)
    response.raise_for_status()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / "grocery-inventory.zip"

    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0

    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0:
                    progress = (downloaded_size / total_size) * 100
                    logger.info(f"Download progress: {progress:.1f}%")

    logger.info(f"Dataset saved to {zip_path}")
    return zip_path


def extract_csv_files(zip_path):
    """Extract all CSV files from the downloaded ZIP."""
    logger.info(f"Extracting CSV files from {zip_path}")

    extracted_files = []

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.lower().endswith('.csv'):
                zip_ref.extract(file_name, OUTPUT_DIR)
                extracted_path = OUTPUT_DIR / file_name
                extracted_files.append(extracted_path)
                logger.info(f"Extracted: {file_name}")

    if not extracted_files:
        logger.warning("No CSV files found in the ZIP archive")
    else:
        logger.info(f"Extracted {len(extracted_files)} CSV file(s)")

    return extracted_files


def main():
    """Main function to orchestrate the dataset download and extraction."""
    logger.info("Starting Kaggle dataset fetch")

    try:
        token = load_kaggle_token()
        zip_path = download_dataset(token)
        extracted_files = extract_csv_files(zip_path)

        logger.info("=== Fetch Complete ===")
        logger.info(f"ZIP file: {zip_path}")
        for csv_file in extracted_files:
            logger.info(f"CSV file: {csv_file}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        if e.response.status_code == 401:
            logger.error("Authentication failed. Check your KAGGLE_TOKEN.")
        elif e.response.status_code == 403:
            logger.error("Access forbidden. You may need to accept dataset terms on Kaggle.")
        elif e.response.status_code == 404:
            logger.error("Dataset not found. Check the dataset URL.")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid ZIP file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
