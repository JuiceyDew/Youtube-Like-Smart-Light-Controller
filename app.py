from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import time
import threading
from threading import Timer
from googleapiclient.discovery import build

app = Flask(__name__)

# Global state
youtube = None
video_id = None
bulb_ip = None
last_likes = -1
last_views = -1
track_likes = True
track_views = False
light_lock = threading.Lock()
light_timer = None
light_on = False

def init_youtube(api_key, vid_id):
    global youtube, video_id
    youtube = build('youtube', 'v3', developerKey=api_key)
    video_id = vid_id

def get_video_stats():
    if youtube and video_id:
        try:
            request = youtube.videos().list(part='statistics', id=video_id)
            response = request.execute()
            stats = response['items'][0]['statistics']
            return int(stats.get('likeCount', 0)), int(stats.get('viewCount', 0))
        except Exception as e:
            print(f"Error fetching stats: {e}")
    return 0, 0

def control_light(duration=1):
    global bulb_ip, light_timer, light_on

    if not bulb_ip:
        return

    with light_lock:
        try:
            if not light_on:
                subprocess.run([os.path.expanduser('flux_led'), bulb_ip, '--on'], check=True)
                light_on = True

            if light_timer:
                light_timer.cancel()

            def turn_off():
                global light_on
                with light_lock:
                    try:
                        subprocess.run([os.path.expanduser('flux_led'), bulb_ip, '--off'], check=True)
                        light_on = False
                    except subprocess.CalledProcessError as e:
                        print(f"Error turning light off: {e}")

            light_timer = Timer(duration, turn_off)
            light_timer.start()

        except subprocess.CalledProcessError as e:
            print(f"Error controlling the light: {e}")

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Tracker</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background-color: #1e1e2f;
                color: #ffffff;
            }
            .container {
                max-width: 600px;
                width: 90%;
                background-color: #2c2c3e;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
                text-align: center;
            }
            h1 {
                font-size: 2rem;
                color: #ff6f61;
                margin-bottom: 1rem;
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            input, label, button {
                font-size: 1rem;
                padding: 0.8rem;
                border-radius: 5px;
                border: none;
                outline: none;
            }
            input {
                background-color: #3a3a4f;
                color: #ffffff;
                border: 1px solid #ff6f61;
            }
            input:focus {
                border-color: #ff8a75;
            }
            label {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: #ffffff;
            }
            button {
                background-color: #ff6f61;
                color: #ffffff;
                cursor: pointer;
                transition: background-color 0.3s ease;
            }
            button:hover {
                background-color: #ff8a75;
            }
            .stats {
                margin-top: 2rem;
                font-size: 1.5rem;
                color: #ff6f61;
            }
            .stats span {
                font-weight: bold;
                color: #ffffff;
            }
            .test-buttons {
                margin-top: 1rem;
                display: flex;
                gap: 1rem;
                justify-content: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>YouTube Likes/Views Tracker</h1>
            <form id="configForm">
                <input type="password" id="apiKey" placeholder="Enter YouTube API Key" required>
                <input type="text" id="videoId" placeholder="Enter Video ID" required>
                <input type="text" id="bulbIp" placeholder="Enter Bulb IP Address" required>
                <label>
                    <input type="checkbox" id="trackLikes" checked> Track Likes
                </label>
                <label>
                    <input type="checkbox" id="trackViews"> Track Views
                </label>
                <button type="submit">Set Configuration</button>
            </form>
            <div class="stats">
                <p>Likes: <span id="likes">-</span></p>
                <p>Views: <span id="views">-</span></p>
            </div>
            <div class="test-buttons">
                <button onclick="testLike()">Test Like</button>
                <button onclick="testView()">Test View</button>
            </div>
        </div>
        <script>
            document.getElementById('configForm').addEventListener('submit', function(event) {
                event.preventDefault();
                const apiKey = document.getElementById('apiKey').value;
                const videoId = document.getElementById('videoId').value;
                const bulbIp = document.getElementById('bulbIp').value;
                const trackLikes = document.getElementById('trackLikes').checked;
                const trackViews = document.getElementById('trackViews').checked;

                fetch(`/set_config?apiKey=${encodeURIComponent(apiKey)}&videoId=${encodeURIComponent(videoId)}&bulbIp=${encodeURIComponent(bulbIp)}&trackLikes=${trackLikes}&trackViews=${trackViews}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'Configuration set successfully') {
                            fetchStats();
                            setInterval(fetchStats, 1000);
                        } else {
                            alert('Failed to set configuration.');
                        }
                    });
            });

            async function fetchStats() {
                try {
                    const response = await fetch('/stats');
                    const data = await response.json();
                    document.getElementById('likes').innerText = data.likes;
                    document.getElementById('views').innerText = data.views;
                } catch (e) {
                    document.getElementById('likes').innerText = "Error";
                    document.getElementById('views').innerText = "Error";
                }
            }

            function testLike() {
                fetch('/test_like');
            }

            function testView() {
                fetch('/test_view');
            }
        </script>
    </body>
    </html>
    """)

@app.route('/set_config')
def set_config():
    global bulb_ip, track_likes, track_views
    api_key = request.args.get('apiKey')
    vid_id = request.args.get('videoId')
    bulb_ip = request.args.get('bulbIp')
    track_likes = request.args.get('trackLikes') == 'true'
    track_views = request.args.get('trackViews') == 'true'

    if api_key and vid_id and bulb_ip:
        try:
            init_youtube(api_key, vid_id)
            return jsonify({'status': 'Configuration set successfully'})
        except Exception as e:
            return jsonify({'error': f'Failed to initialize YouTube client: {e}'}), 500
    return jsonify({'error': 'Missing configuration parameters'}), 400

@app.route('/stats')
def stats_api():
    global last_likes, last_views
    likes, views = get_video_stats()

    if track_likes and likes != last_likes:
        last_likes = likes
        threading.Thread(target=control_light, args=(1,)).start()

    if track_views and views != last_views:
        last_views = views
        threading.Thread(target=control_light, args=(0.5,)).start()

    return jsonify({'likes': likes, 'views': views})

@app.route('/test_like')
def test_like():
    threading.Thread(target=control_light, args=(1,)).start()
    return jsonify({'status': 'Test like triggered'})

@app.route('/test_view')
def test_view():
    threading.Thread(target=control_light, args=(0.5,)).start()
    return jsonify({'status': 'Test view triggered'})

if __name__ == '__main__':
    app.run(debug=True)

