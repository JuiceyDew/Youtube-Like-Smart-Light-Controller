from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import time
import threading
from googleapiclient.discovery import build

app = Flask(__name__)

# Global variables to store configuration
youtube = None
video_id = None
bulb_ip = None
last_view_count = -1  # For detecting changes in view count
light_lock = threading.Lock()  # To prevent concurrent access to the light

def init_youtube(api_key, vid_id):
    """Initialize the YouTube API client."""
    global youtube, video_id
    youtube = build('youtube', 'v3', developerKey=api_key)
    video_id = vid_id

def get_video_views():
    """Fetch the current view count of the video."""
    if youtube and video_id:
        request = youtube.videos().list(part='statistics', id=video_id)
        response = request.execute()
        view_count = int(response['items'][0]['statistics']['viewCount'])
        return view_count
    return 0

def control_light():
    """Turn the light on for 1 second and then off."""
    global bulb_ip
    if bulb_ip:
        with light_lock:
            try:
                subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), bulb_ip, '--on'], check=True)
                time.sleep(1)
                subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), bulb_ip, '--off'], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error controlling the light: {e}")

@app.route('/')
def index():
    """Render the main page with input fields for API key, video ID, and bulb IP."""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>YouTube Views Tracker</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 2rem;
                text-align: center;
                background-color: #f4f4f4;
            }
            .views {
                font-size: 3rem;
                color: #2196f3;
            }
            input {
                padding: 0.5rem;
                margin: 0.5rem;
                width: 300px;
            }
            button {
                padding: 0.5rem 1rem;
                font-size: 1rem;
            }
        </style>
    </head>
    <body>
        <h1>YouTube Views Tracker</h1>
        <form id="configForm">
            <input type="password" id="apiKey" placeholder="Enter YouTube API Key" required>
            <input type="text" id="videoId" placeholder="Enter Video ID" required>
            <input type="text" id="bulbIp" placeholder="Enter Bulb IP Address" required>
            <button type="submit">Set Configuration</button>
        </form>

        <p class="views" id="viewCount">Loading...</p>

        <script>
            document.getElementById('configForm').addEventListener('submit', function(event) {
                event.preventDefault();
                const apiKey = document.getElementById('apiKey').value;
                const videoId = document.getElementById('videoId').value;
                const bulbIp = document.getElementById('bulbIp').value;
                fetch(`/set_config?apiKey=${encodeURIComponent(apiKey)}&videoId=${encodeURIComponent(videoId)}&bulbIp=${encodeURIComponent(bulbIp)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'Configuration set successfully') {
                            fetchViews();
                            setInterval(fetchViews, 1000); // Refresh every 1 second
                        } else {
                            alert('Failed to set configuration.');
                        }
                    });
            });

            async function fetchViews() {
                try {
                    const response = await fetch('/views');
                    const data = await response.json();
                    document.getElementById('viewCount').innerText = data.views;
                } catch (e) {
                    document.getElementById('viewCount').innerText = "Error";
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/set_config')
def set_config():
    """Set the YouTube API key, video ID, and bulb IP address."""
    global bulb_ip
    api_key = request.args.get('apiKey')
    vid_id = request.args.get('videoId')
    bulb_ip = request.args.get('bulbIp')
    if api_key and vid_id and bulb_ip:
        try:
            init_youtube(api_key, vid_id)
            return jsonify({'status': 'Configuration set successfully'})
        except Exception as e:
            return jsonify({'error': f'Failed to initialize YouTube client: {e}'}), 500
    return jsonify({'error': 'API Key, Video ID, or Bulb IP Address missing'}), 400

@app.route('/views')
def views_api():
    """Handle view count and control the light."""
    global last_view_count
    views = get_video_views()

    if views != last_view_count:
        threading.Thread(target=control_light).start()
        last_view_count = views

    return jsonify({'views': views})

if __name__ == '__main__':
    app.run(debug=True)
