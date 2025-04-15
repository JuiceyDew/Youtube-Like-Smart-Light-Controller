import subprocess
import os
from flask import Flask, render_template_string, request, jsonify
from googleapiclient.discovery import build

app = Flask(__name__)

# Initialize variables
light_on = False
last_like_count = -1  # for change detection
youtube = None
VIDEO_ID = None
LIGHT_IP = None

def get_video_likes():
    request = youtube.videos().list(
        part='statistics',
        id=VIDEO_ID
    )
    response = request.execute()
    like_count = int(response['items'][0]['statistics']['likeCount'])
    return like_count

@app.route('/', methods=['GET', 'POST'])
def index():
    global youtube, VIDEO_ID, LIGHT_IP

    if request.method == 'POST':
        # Get user inputs
        api_key = request.form['api_key']
        VIDEO_ID = request.form['video_id']
        LIGHT_IP = request.form['light_ip']

        # Initialize YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)

        return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>YouTube Likes Tracker</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 2rem;
                    text-align: center;
                    background-color: #f4f4f4;
                }
                .likes {
                    font-size: 3rem;
                    color: #e91e63;
                }
            </style>
        </head>
        <body>
            <h1>Current YouTube Likes</h1>
            <p class="likes" id="likeCount">Loading...</p>

            <script>
                async function fetchLikes() {
                    try {
                        const response = await fetch('/likes');
                        const data = await response.json();
                        document.getElementById('likeCount').innerText = data.likes;
                    } catch (e) {
                        document.getElementById('likeCount').innerText = "Error";
                    }
                }

                fetchLikes();
                setInterval(fetchLikes, 1000); // Refresh every 1 second
            </script>
        </body>
        </html>
        """)

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Configure YouTube Likes Tracker</title>
    </head>
    <body>
        <h1>Enter Configuration Details</h1>
        <form method="post">
            <label for="api_key">YouTube API Key:</label><br>
            <input type="text" id="api_key" name="api_key" required><br><br>
            <label for="video_id">YouTube Video ID:</label><br>
            <input type="text" id="video_id" name="video_id" required><br><br>
            <label for="light_ip">Smart Light IP Address:</label><br>
            <input type="text" id="light_ip" name="light_ip" required><br><br>
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """)

@app.route('/likes')
def likes_api():
    global light_on, last_like_count

    if not (youtube and VIDEO_ID and LIGHT_IP):
        return jsonify({'error': 'Configuration not set'}), 400

    likes = get_video_likes()

    if likes != last_like_count:
        if likes % 2 == 0:
            subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), LIGHT_IP, '--on'])
            light_on = True
        else:
            subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), LIGHT_IP, '--off'])
            light_on = False
        last_like_count = likes

    return jsonify({'likes': likes, 'light_on': light_on})

if __name__ == '__main__':
    app.run(debug=True)
