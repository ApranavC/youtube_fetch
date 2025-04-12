import yt_dlp
import os

class YouTubeDownloader:
    def __init__(self):
        """Initialize the downloader."""
        self.playlist_name = None
        self.progress = 0  # Store overall download progress

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

            # Return descending order (e.g., 1080, 720, 480, etc.)
            return sorted(quality_options.items(), key=lambda x: int(x[0]), reverse=True)
        except Exception:
            return []

    def check_if_video_exists(self, video_title):
        """Check if a video file already exists in the download folder."""
        folder_output = self.playlist_name if self.playlist_name else 'Downloads'
        file_path_mp4 = os.path.join(folder_output, f"{video_title}.mp4")
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
                # This hook updates progress for the current video (0-99)
                self.update_progress(int(percent))
            elif d['status'] == 'finished':
                # Merging/conversion is complete; mark 100%
                self.update_progress(100)

        try:
            # Get video info (without downloading)
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)

            video_title = info.get('title', 'Unknown Video')

            # If already exists, no need to download again
            if self.check_if_video_exists(video_title):
                return {"status": "Already downloaded", "video": video_title}

            # Get available qualities and choose one
            quality_options = self.get_video_qualities(video_url)
            selected_format_id = next((q[1] for q in quality_options if q[0] == quality), None)

            folder_output = self.playlist_name if self.playlist_name else 'Downloads'

            ydl_opts = {
                'format': f"{selected_format_id}+bestaudio/best" if selected_format_id else 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': f'{folder_output}/%(title)s.%(ext)s',
                'noplaylist': True,
                'progress_hooks': [progress_hook],
                'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
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
        Returns a list of dictionaries with 'title', 'url'.
        """
        ydl_opts = {'ignoreerrors': True, 'no_warnings': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)

            if 'entries' not in info or info.get('_type') == 'video':
                self.playlist_name = "Downloads"
                return [{"title": info.get('title', 'Unknown Video'), "url": playlist_url}]

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
        Avoid overriding partial progress updates from the progress_hook.
        """
        results = []
        total_videos = len(videos)
        for index, video in enumerate(videos):
            result = self.download_video(video['url'], "720")
            results.append(result)
        return results
