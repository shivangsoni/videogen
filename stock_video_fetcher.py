"""
Stock video fetcher - downloads free stock videos from Pexels
"""

import os
import random
import requests
from pathlib import Path
from typing import List, Optional

from config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR


# Pexels API - Free, no API key needed for basic use
# For heavy use, get free key at: https://www.pexels.com/api/
PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"


class StockVideoFetcher:
    """Fetches free stock videos from Pexels"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Get API key from environment or use provided one
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY")
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Keywords for motivational/aesthetic content
        self.default_keywords = [
            "abstract dark",
            "dark gradient",
            "smoke black",
            "particles dark",
            "night city lights",
            "dark clouds",
            "rain window",
            "fire flames dark",
            "water drops dark",
            "neon lights dark",
            "space stars",
            "ocean waves dark",
            "fog mist dark",
            "lightning storm",
            "sunset silhouette",
        ]
    
    def fetch_videos(
        self,
        keywords: List[str] = None,
        count: int = 3,
        orientation: str = "portrait"
    ) -> List[str]:
        """
        Fetch stock videos from Pexels.
        
        Args:
            keywords: Search keywords
            count: Number of videos to fetch
            orientation: 'portrait' for shorts, 'landscape' for regular
            
        Returns:
            List of paths to downloaded videos
        """
        if not self.api_key:
            print("      No Pexels API key found. Get free key at https://www.pexels.com/api/")
            print("      Set PEXELS_API_KEY environment variable or pass to constructor")
            return []
        
        if keywords is None:
            keywords = random.sample(self.default_keywords, min(count, len(self.default_keywords)))
        
        downloaded = []
        
        for i, keyword in enumerate(keywords[:count]):
            print(f"      Searching for: {keyword}")
            video_path = self._search_and_download(keyword, i, orientation)
            if video_path:
                downloaded.append(video_path)
                print(f"      Downloaded: {video_path}")
        
        return downloaded
    
    def _search_and_download(
        self,
        keyword: str,
        index: int,
        orientation: str
    ) -> Optional[str]:
        """Search for a video and download it"""
        try:
            headers = {"Authorization": self.api_key}
            params = {
                "query": keyword,
                "per_page": 10,
                "orientation": orientation,
                "size": "medium"  # medium quality for faster download
            }
            
            response = requests.get(PEXELS_VIDEO_API, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"      API error: {response.status_code}")
                return None
            
            data = response.json()
            videos = data.get("videos", [])
            
            if not videos:
                print(f"      No videos found for: {keyword}")
                return None
            
            # Pick a random video from results
            video = random.choice(videos)
            
            # Find the best quality file (prefer HD, portrait)
            video_files = video.get("video_files", [])
            
            # Sort by quality - prefer HD portrait
            best_file = None
            for vf in video_files:
                if vf.get("quality") == "hd":
                    # Check if portrait orientation
                    if vf.get("height", 0) > vf.get("width", 0):
                        best_file = vf
                        break
                    elif best_file is None:
                        best_file = vf
            
            if best_file is None and video_files:
                best_file = video_files[0]
            
            if best_file is None:
                return None
            
            # Download the video
            video_url = best_file.get("link")
            output_path = self.temp_dir / f"stock_video_{index}.mp4"
            
            return self._download_video(video_url, output_path)
            
        except Exception as e:
            print(f"      Error fetching video: {e}")
            return None
    
    def _download_video(self, url: str, output_path: Path) -> Optional[str]:
        """Download video from URL"""
        try:
            response = requests.get(url, stream=True, timeout=60)
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                
                return str(output_path)
                
        except Exception as e:
            print(f"      Download error: {e}")
        
        return None
    
    def fetch_video_info(
        self,
        keywords: List[str] = None,
        count: int = 3,
        orientation: str = "portrait"
    ) -> List[dict]:
        """
        Fetch video metadata from Pexels (for UI display, no download).
        
        Args:
            keywords: Search keywords
            count: Number of videos to fetch info for
            orientation: 'portrait' for shorts
            
        Returns:
            List of video info dicts with thumbnail, title, etc.
        """
        if not self.api_key:
            return []
        
        if keywords is None:
            keywords = random.sample(self.default_keywords, min(count, len(self.default_keywords)))
        
        video_info = []
        
        for keyword in keywords[:count]:
            try:
                headers = {"Authorization": self.api_key}
                params = {
                    "query": keyword,
                    "per_page": 5,
                    "orientation": orientation,
                    "size": "medium"
                }
                
                response = requests.get(PEXELS_VIDEO_API, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    videos = data.get("videos", [])
                    
                    if videos:
                        video = random.choice(videos)
                        # Get thumbnail/preview image
                        image_url = video.get("image", "")
                        user = video.get("user", {})
                        
                        video_info.append({
                            "keyword": keyword,
                            "thumbnail": image_url,
                            "photographer": user.get("name", "Unknown"),
                            "duration": video.get("duration", 0),
                            "url": video.get("url", "")
                        })
            except Exception as e:
                print(f"      Error fetching video info: {e}")
        
        return video_info
    
    def get_keywords_from_script(self, segments) -> List[str]:
        """Extract relevant video search keywords from script"""
        keywords = []
        
        # Map common words to video search terms
        keyword_map = {
            "sleep": ["night bedroom", "sleeping peaceful", "dark room"],
            "diet": ["healthy food aesthetic", "kitchen dark", "cooking"],
            "room": ["room interior dark", "minimal room", "clean space"],
            "discipline": ["workout gym", "training fitness", "running"],
            "mindset": ["meditation", "thinking person", "focus concentration"],
            "chaos": ["storm clouds", "rain heavy", "chaos abstract"],
            "life": ["lifestyle aesthetic", "city night", "journey road"],
            "motivation": ["success celebration", "achievement", "winner"],
            "truth": ["light rays", "sunrise", "clarity"],
            "fix": ["repair hands", "building", "construction"],
        }
        
        for segment in segments:
            text_lower = segment.text.lower()
            for word, searches in keyword_map.items():
                if word in text_lower:
                    keywords.append(random.choice(searches))
                    break
            else:
                # Default keywords for visual appeal
                keywords.append(random.choice(self.default_keywords))
        
        return keywords[:5]  # Limit to 5 videos


if __name__ == "__main__":
    # Test
    fetcher = StockVideoFetcher()
    videos = fetcher.fetch_videos(count=2)
    print(f"\nDownloaded {len(videos)} videos")
