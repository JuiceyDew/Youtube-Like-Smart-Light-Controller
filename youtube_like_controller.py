from flask import Flask, render_template_string, jsonify
import subprocess
import os
from googleapiclient.discovery import build

app = Flask(__name__)

# YouTube API setup
YOUTUBE_API_KEY = 'PUT API KEY HERE'
VIDEO_ID = 'PUT YOUTUBE VIDEO ID HERE'
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Smart light state
light_on = False
last_like_count = -1  # for change detection

def get_video_likes():
    request = youtube.videos().list(
        part='statistics',
        id=VIDEO_ID
    )
    response = request.execute()
    like_count = int(response['items'][0]['statistics']['likeCount'])
    return like_count

@app.route('/')
def index():
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

@app.route('/likes')
def likes_api():
    global light_on, last_like_count
    likes = get_video_likes()

    if likes != last_like_count:
        if likes % 2 == 0:
            subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), 'IP ADDRESS HERE', '--on'])
            light_on = True
        else:
            subprocess.run([os.path.expanduser('~/.local/bin/flux_led'), 'IP ADDRESS HERE', '--off'])
            light_on = False
        last_like_count = likes

    return jsonify({'likes': likes, 'light_on': light_on})

if __name__ == '__main__':
    app.run(debug=True)
