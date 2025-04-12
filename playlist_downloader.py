import yt_dlp
import os
import re

def sanitize_filename(filename):
    """Sanitize a filename by removing problematic characters."""
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    return filename

class MyLogger:
    """Custom logger to capture yt-dlp log messages."""
    def __init__(self, downloader_instance):
        self.downloader = downloader_instance

    def debug(self, msg):
        if msg:
            self.downloader.search_logs.append(msg)

    def warning(self, msg):
        if msg:
            self.downloader.search_logs.append("WARNING: " + msg)

    def error(self, msg):
        if msg:
            self.downloader.search_logs.append("ERROR: " + msg)

class YouTubeDownloader:
    def __init__(self):
        """Initialize the downloader."""
        self.playlist_name = None
        self.progress = 0  # Overall download progress
        self.search_logs = []  # Captured log messages during search

    def update_progress(self, percent):
        """Update the overall progress value (0–100)."""
        self.progress = percent

    def get_progress(self):
        """Get current overall download progress."""
        return self.progress

    def get_video_qualities(self, video_url):
        """Fetch available video qualities from YouTube."""
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
            formats = info.get('formats', [])
            quality_options = {}
            for fmt in formats:
                height = fmt.get('height')
                if height and fmt.get('ext') == 'mp4':  # Only select MP4 formats
                    quality_options[str(height)] = fmt['format_id']
            # Return options in descending order (e.g., 1080, 720, 480...)
            return sorted(quality_options.items(), key=lambda x: int(x[0]), reverse=True)
        except Exception:
            return []

    def check_if_video_exists(self, video_title):
        """Check if a video file already exists in the download folder."""
        folder_output = self.playlist_name if self.playlist_name else 'Downloads'
        # Sanitize the video title for a valid filename
        safe_title = sanitize_filename(video_title)
        file_path_mp4 = os.path.join(folder_output, f"{safe_title}.mp4")
        return os.path.exists(file_path_mp4)

    def download_video(self, video_url, quality="720"):
        """
        Download a single video from YouTube and return its status.
        Real-time progress is updated via the progress_hook.
        """
        def progress_hook(d):
            """Track progress and update the overall progress."""
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 1)
                percent = (downloaded / total) * 100 if total else 0
                self.update_progress(int(percent))
            elif d['status'] == 'finished':
                self.update_progress(100)

        try:
            # Extract video info (without downloading)
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'Unknown Video')

            # If file already exists, skip downloading
            if self.check_if_video_exists(video_title):
                return {"status": "Already downloaded", "video": video_title}

            # Get available qualities and choose the selected one if available
            quality_options = self.get_video_qualities(video_url)
            selected_format_id = next((q[1] for q in quality_options if q[0] == quality), None)

            folder_output = self.playlist_name if self.playlist_name else 'Downloads'
            os.makedirs(folder_output, exist_ok=True)

            ydl_opts = {
                'format': f"{selected_format_id}+bestaudio/best" if selected_format_id else 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': f'{folder_output}/%(title)s.%(ext)s',
                'noplaylist': True,
                'progress_hooks': [progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }],
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            return {"status": "Downloaded", "video": video_title}

        except Exception as e:
            return {"status": "Error", "message": str(e)}

    def download_playlist(self, playlist_url):
        """
        Determine if the URL is a single video or a playlist and return metadata.
        Returns a list of dictionaries with 'title' and 'url'. Also captures log messages.
        """
        # Clear previous search logs
        self.search_logs = []
        ydl_opts = {
            'ignoreerrors': True,
            'no_warnings': True,
            'logger': MyLogger(self)
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
            # Single video case
            if 'entries' not in info or info.get('_type') == 'video':
                self.playlist_name = "Downloads"
                return [{"title": info.get('title', 'Unknown Video'), "url": playlist_url}]
            # Playlist case
            self.playlist_name = info.get('title', 'Unknown_Playlist')
            videos = [
                {'title': vid.get('title'), 'url': vid.get('webpage_url')}
                for vid in info.get('entries', []) if vid and vid.get('webpage_url')
            ]
            return videos
        except Exception as e:
            return {"error": str(e)}

    def start_playlist_download(self, videos):
        """
        (Optional) Sequentially download all videos in a playlist.
        """
        results = []
        for video in videos:
            result = self.download_video(video['url'], quality="720")
            results.append(result)
        return results
