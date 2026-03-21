# scraper.py - Scrape UVA incident logs
import requests
from bs4 import BeautifulSoup

def scrape_uva_logs():
    """
    Scrape UVA Daily Aviation/Crime Logs or RSS feed.
    Returns list of incident dicts.
    """
    url = "https://example-uva-log-url.com"  # Replace with real URL
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Parse incidents (simplified)
    incidents = [{"title": "Sample Incident", "description": "Details", "location": "UVA"}]
    return incidents