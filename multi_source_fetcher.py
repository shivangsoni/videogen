"""
Multi-source stock media fetcher - supports videos and GIFs from multiple free APIs
Sources: Pexels, Pixabay, GIPHY
"""

import os
import random
import requests
from pathlib import Path
from typing import List, Optional, Literal

# Load environment variables (optional - for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not needed on HF Spaces (uses secrets)

from config import TEMP_DIR


class MultiSourceFetcher:
    """Fetches free stock videos and GIFs from multiple sources"""
    
    def __init__(
        self,
        pexels_key: Optional[str] = None,
        pixabay_key: Optional[str] = None,
        giphy_key: Optional[str] = None
    ):
        self.pexels_key = pexels_key or os.environ.get("PEXELS_API_KEY")
        self.pixabay_key = pixabay_key or os.environ.get("PIXABAY_API_KEY")
        self.giphy_key = giphy_key or os.environ.get("GIPHY_API_KEY")
        
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        
        # API endpoints
        self.PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"
        self.PEXELS_IMAGE_API = "https://api.pexels.com/v1/search"
        self.PIXABAY_API = "https://pixabay.com/api/"
        self.PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"
        self.GIPHY_API = "https://api.giphy.com/v1/gifs/search"
        
        # Hand-drawn/sketch keywords
        self.sketch_keywords = [
            "hand drawn",
            "sketch animation",
            "doodle",
            "whiteboard animation",
            "line art",
            "pencil sketch",
            "hand sketch",
            "illustration animated",
            "cartoon hand drawn",
            "scribble animation"
        ]
    
    def fetch_from_pixabay(
        self,
        query: str,
        media_type: Literal["video", "image", "all"] = "video",
        count: int = 3,
        image_type: str = "all"  # photo, illustration, vector
    ) -> List[str]:
        """
        Fetch videos or images from Pixabay.
        
        Args:
            query: Search query
            media_type: 'video', 'image', or 'all'
            count: Number of items to fetch
            image_type: For images - 'photo', 'illustration', 'vector', 'all'
        """
        if not self.pixabay_key:
            print("      [Pixabay] No API key. Get free key at https://pixabay.com/api/docs/")
            return []
        
        downloaded = []
        
        if media_type in ("video", "all"):
            downloaded.extend(self._fetch_pixabay_videos(query, count))
        
        if media_type in ("image", "all"):
            downloaded.extend(self._fetch_pixabay_images(query, count, image_type))
        
        return downloaded
    
    def _fetch_pixabay_videos(self, query: str, count: int) -> List[str]:
        """Fetch videos from Pixabay"""
        params = {
            "key": self.pixabay_key,
            "q": query,
            "video_type": "all",
            "per_page": min(count * 2, 50),
            "safesearch": "true"
        }
        
        try:
            response = requests.get(self.PIXABAY_VIDEO_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            videos = data.get("hits", [])
            downloaded = []
            
            for i, video in enumerate(videos[:count]):
                # Get the best quality video (large > medium > small)
                video_urls = video.get("videos", {})
                video_url = None
                for quality in ["large", "medium", "small"]:
                    if quality in video_urls and video_urls[quality].get("url"):
                        video_url = video_urls[quality]["url"]
                        break
                
                if video_url:
                    filename = self.temp_dir / f"pixabay_video_{i}.mp4"
                    if self._download_file(video_url, filename):
                        downloaded.append(str(filename))
                        print(f"      [Pixabay] Downloaded video: {filename.name}")
            
            return downloaded
            
        except Exception as e:
            print(f"      [Pixabay] Error fetching videos: {e}")
            return []
    
    def _fetch_pixabay_images(self, query: str, count: int, image_type: str) -> List[str]:
        """Fetch images from Pixabay (including GIFs)"""
        params = {
            "key": self.pixabay_key,
            "q": query,
            "image_type": image_type,
            "per_page": min(count * 2, 50),
            "safesearch": "true"
        }
        
        try:
            response = requests.get(self.PIXABAY_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            images = data.get("hits", [])
            downloaded = []
            
            for i, img in enumerate(images[:count]):
                img_url = img.get("largeImageURL") or img.get("webformatURL")
                if img_url:
                    ext = "gif" if ".gif" in img_url.lower() else "jpg"
                    filename = self.temp_dir / f"pixabay_img_{i}.{ext}"
                    if self._download_file(img_url, filename):
                        downloaded.append(str(filename))
                        print(f"      [Pixabay] Downloaded image: {filename.name}")
            
            return downloaded
            
        except Exception as e:
            print(f"      [Pixabay] Error fetching images: {e}")
            return []
    
    def fetch_from_giphy(
        self,
        query: str,
        count: int = 3,
        rating: str = "g"  # g, pg, pg-13, r
    ) -> List[str]:
        """
        Fetch GIFs from GIPHY.
        
        Args:
            query: Search query (e.g., "hand drawn", "sketch")
            count: Number of GIFs to fetch
            rating: Content rating filter
        """
        if not self.giphy_key:
            print("      [GIPHY] No API key. Get free key at https://developers.giphy.com/")
            return []
        
        params = {
            "api_key": self.giphy_key,
            "q": query,
            "limit": min(count * 2, 50),
            "rating": rating,
            "lang": "en"
        }
        
        try:
            response = requests.get(self.GIPHY_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            gifs = data.get("data", [])
            downloaded = []
            
            for i, gif in enumerate(gifs[:count]):
                # Get original or downsized GIF
                images = gif.get("images", {})
                gif_url = None
                
                # Prefer original, then downsized
                for quality in ["original", "downsized", "fixed_height"]:
                    if quality in images and images[quality].get("url"):
                        gif_url = images[quality]["url"]
                        break
                
                if gif_url:
                    filename = self.temp_dir / f"giphy_{i}.gif"
                    if self._download_file(gif_url, filename):
                        downloaded.append(str(filename))
                        print(f"      [GIPHY] Downloaded: {filename.name}")
            
            return downloaded
            
        except Exception as e:
            print(f"      [GIPHY] Error: {e}")
            return []
    
    def fetch_hand_drawn_gifs(self, query: str = None, count: int = 3) -> List[str]:
        """
        Fetch hand-drawn/sketch style GIFs from available sources.
        Tries GIPHY first, then Pixabay.
        
        Args:
            query: Optional custom query, defaults to sketch-style keywords
            count: Number of GIFs to fetch
        """
        if query is None:
            query = random.choice(self.sketch_keywords)
        
        print(f"      Searching for hand-drawn GIFs: {query}")
        
        downloaded = []
        
        # Try GIPHY first (best for GIFs)
        if self.giphy_key:
            downloaded.extend(self.fetch_from_giphy(query, count))
        
        # Supplement with Pixabay if needed
        if len(downloaded) < count and self.pixabay_key:
            remaining = count - len(downloaded)
            downloaded.extend(self.fetch_from_pixabay(
                query + " animation", 
                media_type="image",
                count=remaining,
                image_type="illustration"
            ))
        
        return downloaded[:count]
    
    def fetch_sketch_videos(self, query: str = None, count: int = 3) -> List[str]:
        """
        Fetch sketch/hand-drawn style videos.
        
        Args:
            query: Custom query or uses default sketch keywords
            count: Number of videos to fetch
        """
        if query is None:
            query = random.choice([
                "whiteboard animation",
                "hand drawing",
                "sketch animation",
                "doodle video",
                "line drawing animation"
            ])
        
        print(f"      Searching for sketch videos: {query}")
        
        downloaded = []
        
        # Try Pixabay for videos
        if self.pixabay_key:
            downloaded.extend(self.fetch_from_pixabay(query, "video", count))
        
        return downloaded[:count]
    
    def _download_file(self, url: str, filepath: Path) -> bool:
        """Download a file from URL to filepath"""
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"      Download error: {e}")
            return False
    
    def list_available_sources(self) -> dict:
        """List which APIs are configured"""
        return {
            "Pexels": bool(self.pexels_key),
            "Pixabay": bool(self.pixabay_key),
            "GIPHY": bool(self.giphy_key)
        }


# Quick test
if __name__ == "__main__":
    fetcher = MultiSourceFetcher()
    
    print("Available sources:")
    for source, available in fetcher.list_available_sources().items():
        status = "[OK]" if available else "[NO KEY]"
        print(f"  {source}: {status}")
    
    print("\nTo enable sources, set environment variables:")
    print("  PEXELS_API_KEY=your_key    (https://www.pexels.com/api/)")
    print("  PIXABAY_API_KEY=your_key   (https://pixabay.com/api/docs/)")
    print("  GIPHY_API_KEY=your_key     (https://developers.giphy.com/)")
