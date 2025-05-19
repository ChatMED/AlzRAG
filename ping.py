#!/usr/bin/env python3
import requests
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keep_alive.log"),
        logging.StreamHandler()
    ]
)

# Configuration
URL = "http://jovana.openbrain.io"
PING_INTERVAL = 900  # Ping every 15 minutes (900 seconds)

def ping_website():
    try:
        response = requests.get(URL, timeout=10)
        status_code = response.status_code
        logging.info(f"Ping successful - Status Code: {status_code}")
        return True
    except requests.RequestException as e:
        logging.error(f"Ping failed: {str(e)}")
        return False

def main():
    logging.info(f"Keep-alive service started for {URL}")
    logging.info(f"Ping interval set to {PING_INTERVAL} seconds")
    
    while True:
        ping_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Pinging at {ping_time}")
        
        ping_website()
        
        # Sleep until next ping interval
        time.sleep(PING_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Keep-alive service stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")