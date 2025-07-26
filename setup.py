import os
import urllib.request

def download_gauge_js():
    """Download the gauge.min.js library."""
    js_dir = os.path.join('static', 'js')
    gauge_path = os.path.join(js_dir, 'gauge.min.js')
    
    # Skip if file already exists
    if os.path.exists(gauge_path):
        print("gauge.min.js already exists, skipping download")
        return
    
    # URL for gauge.js library
    url = "https://bernii.github.io/gauge.js/dist/gauge.min.js"
    
    print(f"Downloading gauge.min.js from {url}")
    try:
        urllib.request.urlretrieve(url, gauge_path)
        print(f"Successfully downloaded to {gauge_path}")
    except Exception as e:
        print(f"Error downloading gauge.min.js: {e}")
        print("Please manually download the file from https://bernii.github.io/gauge.js/dist/gauge.min.js")
        print(f"and place it in {js_dir} directory.")

if __name__ == "__main__":
    download_gauge_js()
    print("Setup complete! Run 'python app.py' to start the application.")
