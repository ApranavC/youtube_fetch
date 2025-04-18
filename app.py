from flask import Flask, render_template, request, jsonify
import threading
import re
from playlist_downloader import YouTubeDownloader

app = Flask(__name__)
downloader = YouTubeDownloader()
video_statuses = {}  # Global dict to track video statuses

def sanitize_url(url):
    """Replace non-alphanumeric characters with underscores."""
    return re.sub(r'\W+', '_', url)

@app.route('/')
def home():
    """Load the web interface."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Fetch videos from a YouTube playlist and assign safe IDs.
       Also returns log status messages captured during the search."""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    result = downloader.download_playlist(url)
    if isinstance(result, list):
        videos = result
        for video in videos:
            safe_id = sanitize_url(video['url'])
            video['safe_id'] = safe_id
            video_statuses[safe_id] = "Pending"
        response = {
            'videos': videos,
            'total': len(videos),
            'logs': downloader.search_logs  # Return captured log messages
        }
        return jsonify(response)
    else:
        return jsonify({'error': result.get('error', 'Unknown error')}), 500

@app.route('/download', methods=['POST'])
def download():
    """Download selected videos sequentially and update their status."""
    data = request.json
    video_urls = data.get('video_urls')
    if not video_urls:
        return jsonify({'error': 'No videos selected'}), 400

    def download_videos():
        total = len(video_urls)
        for idx, video in enumerate(video_urls):
            safe_id = sanitize_url(video['url'])
            video_statuses[safe_id] = "Downloading..."
            result = downloader.download_video(video['url'], quality="720")
            if result["status"] == "Downloaded":
                video_statuses[safe_id] = "Downloaded"
            elif result["status"] == "Already downloaded":
                video_statuses[safe_id] = "Already Downloaded"
            else:
                video_statuses[safe_id] = "Error"
            # Update overall progress (sequentially)
            overall_progress = int(((idx + 1) / total) * 100)
            downloader.update_progress(overall_progress)

    threading.Thread(target=download_videos).start()
    return jsonify({'message': 'Download started'})

@app.route('/progress')
def get_progress():
    """Return overall progress and per-video status dictionary."""
    return jsonify({
        "progress": downloader.get_progress(),
        "video_statuses": video_statuses
    })

if __name__ == '__main__':
    # For local testing we can use Flask's built-in server
    app.run(debug=True, threaded=True)
