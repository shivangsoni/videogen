"""
Multi-source media fetcher - downloads videos/GIFs from multiple free sources
Supports: Pixabay, GIPHY, Tenor, and more
"""

import os
import random
import requests
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR


class MultiSourceFetcher:
    """Fetches media from multiple free sources"""
    
    # API endpoints
    PIXABAY_API = "https://pixabay.com/api/"
    PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"
    GIPHY_API = "https://api.giphy.com/v1/gifs/search"
    TENOR_API = "https://tenor.googleapis.com/v2/search"
    
    # Default search terms by mood
    MOOD_KEYWORDS = {
        "motivation": ["success", "winner", "achievement", "goal", "hustle"],
        "calm": ["nature", "peaceful", "relax", "zen", "meditation"],
        "energy": ["action", "sports", "workout", "dance", "move"],
        "dark": ["abstract", "smoke", "particles", "neon", "night"],
        "happy": ["smile", "celebration", "party", "joy", "fun"],
    }
    
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # API keys from environment
        self.pixabay_key = os.environ.get("PIXABAY_API_KEY", "")
        self.giphy_key = os.environ.get("GIPHY_API_KEY", "")
        self.tenor_key = os.environ.get("TENOR_API_KEY", "")
        
        # Track downloaded files to avoid duplicates
        self.downloaded_urls = set()
    
    def fetch_from_pixabay(
        self,
        query: str = "motivation",
        media_type: str = "video",  # "video" or "image"
        count: int = 3,
        orientation: str = "vertical"
    ) -> List[str]:
        """
        Fetch media from Pixabay API
        
        Args:
            query: Search term
            media_type: "video" or "image"
            count: Number of items to fetch
            orientation: "vertical", "horizontal", or "all"
        """
        if not self.pixabay_key:
            print("      [Pixabay] No API key found. Get free key at: https://pixabay.com/api/docs/")
            return []
        
        downloaded = []
        
        try:
            api_url = self.PIXABAY_VIDEO_API if media_type == "video" else self.PIXABAY_API
            
            params = {
                "key": self.pixabay_key,
                "q": query,
                "per_page": min(count * 3, 50),  # Get more results for variety
                "safesearch": "true",
            }
            
            if media_type == "video":
                params["video_type"] = "all"
            else:
                params["image_type"] = "photo"
                params["orientation"] = orientation
            
            print(f"      [Pixabay] Searching for: {query}")
            response = self.session.get(api_url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"      [Pixabay] API error: {response.status_code}")
                return []
            
            data = response.json()
            hits = data.get("hits", [])
            
            if not hits:
                print(f"      [Pixabay] No results for: {query}")
                return []
            
            # Shuffle to get variety
            random.shuffle(hits)
            
            for i, item in enumerate(hits[:count * 2]):  # Try more to account for failures
                if len(downloaded) >= count:
                    break
                
                if media_type == "video":
                    # Get video URL (prefer medium quality for speed)
                    videos = item.get("videos", {})
                    video_url = (
                        videos.get("medium", {}).get("url") or
                        videos.get("small", {}).get("url") or
                        videos.get("large", {}).get("url")
                    )
                    
                    if video_url and video_url not in self.downloaded_urls:
                        output_path = self.temp_dir / f"pixabay_video_{i}_{random.randint(1000,9999)}.mp4"
                        if self._download_file(video_url, output_path):
                            downloaded.append(str(output_path))
                            self.downloaded_urls.add(video_url)
                            print(f"      [Pixabay] Downloaded video {len(downloaded)}/{count}")
                else:
                    # Get image URL
                    image_url = item.get("largeImageURL") or item.get("webformatURL")
                    
                    if image_url and image_url not in self.downloaded_urls:
                        output_path = self.temp_dir / f"pixabay_image_{i}_{random.randint(1000,9999)}.jpg"
                        if self._download_file(image_url, output_path):
                            downloaded.append(str(output_path))
                            self.downloaded_urls.add(image_url)
                            print(f"      [Pixabay] Downloaded image {len(downloaded)}/{count}")
            
        except Exception as e:
            print(f"      [Pixabay] Error: {e}")
        
        return downloaded
    
    def fetch_hand_drawn_gifs(
        self,
        query: str = None,
        count: int = 3
    ) -> List[str]:
        """
        Fetch animated GIFs from GIPHY
        
        Args:
            query: Search term (uses random mood keyword if None)
            count: Number of GIFs to fetch
        """
        # Use GIPHY public beta key if no key provided
        api_key = self.giphy_key or "dc6zaTOxFJmzC"  # Public beta key
        
        if not query:
            mood = random.choice(list(self.MOOD_KEYWORDS.keys()))
            query = random.choice(self.MOOD_KEYWORDS[mood])
        
        downloaded = []
        
        try:
            params = {
                "api_key": api_key,
                "q": query,
                "limit": min(count * 3, 25),
                "rating": "g",
                "lang": "en"
            }
            
            print(f"      [GIPHY] Searching for: {query}")
            response = self.session.get(self.GIPHY_API, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"      [GIPHY] API error: {response.status_code}")
                return []
            
            data = response.json()
            gifs = data.get("data", [])
            
            if not gifs:
                print(f"      [GIPHY] No results for: {query}")
                return []
            
            # Shuffle for variety
            random.shuffle(gifs)
            
            for i, gif in enumerate(gifs[:count * 2]):
                if len(downloaded) >= count:
                    break
                
                # Get MP4 version (better for video editing)
                images = gif.get("images", {})
                
                # Prefer original_mp4 or downsized for quality
                mp4_url = (
                    images.get("original_mp4", {}).get("mp4") or
                    images.get("downsized", {}).get("url") or
                    images.get("original", {}).get("url")
                )
                
                if mp4_url and mp4_url not in self.downloaded_urls:
                    ext = ".mp4" if ".mp4" in mp4_url else ".gif"
                    output_path = self.temp_dir / f"giphy_{i}_{random.randint(1000,9999)}{ext}"
                    
                    if self._download_file(mp4_url, output_path):
                        # Convert GIF to video if needed
                        if ext == ".gif":
                            video_path = self._convert_gif_to_video(output_path)
                            if video_path:
                                downloaded.append(video_path)
                                self.downloaded_urls.add(mp4_url)
                                print(f"      [GIPHY] Downloaded & converted GIF {len(downloaded)}/{count}")
                        else:
                            downloaded.append(str(output_path))
                            self.downloaded_urls.add(mp4_url)
                            print(f"      [GIPHY] Downloaded MP4 {len(downloaded)}/{count}")
            
        except Exception as e:
            print(f"      [GIPHY] Error: {e}")
        
        return downloaded
    
    def fetch_from_tenor(
        self,
        query: str = "motivation",
        count: int = 3
    ) -> List[str]:
        """
        Fetch GIFs from Tenor API
        
        Args:
            query: Search term
            count: Number of GIFs to fetch
        """
        if not self.tenor_key:
            print("      [Tenor] No API key found")
            return []
        
        downloaded = []
        
        try:
            params = {
                "key": self.tenor_key,
                "q": query,
                "limit": min(count * 3, 20),
                "contentfilter": "medium",
                "media_filter": "mp4,gif"
            }
            
            print(f"      [Tenor] Searching for: {query}")
            response = self.session.get(self.TENOR_API, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"      [Tenor] API error: {response.status_code}")
                return []
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                print(f"      [Tenor] No results for: {query}")
                return []
            
            random.shuffle(results)
            
            for i, item in enumerate(results[:count * 2]):
                if len(downloaded) >= count:
                    break
                
                media_formats = item.get("media_formats", {})
                
                # Prefer MP4
                mp4_data = media_formats.get("mp4", {})
                url = mp4_data.get("url")
                
                if not url:
                    gif_data = media_formats.get("gif", {})
                    url = gif_data.get("url")
                
                if url and url not in self.downloaded_urls:
                    ext = ".mp4" if ".mp4" in url else ".gif"
                    output_path = self.temp_dir / f"tenor_{i}_{random.randint(1000,9999)}{ext}"
                    
                    if self._download_file(url, output_path):
                        if ext == ".gif":
                            video_path = self._convert_gif_to_video(output_path)
                            if video_path:
                                downloaded.append(video_path)
                                self.downloaded_urls.add(url)
                        else:
                            downloaded.append(str(output_path))
                            self.downloaded_urls.add(url)
                        print(f"      [Tenor] Downloaded {len(downloaded)}/{count}")
            
        except Exception as e:
            print(f"      [Tenor] Error: {e}")
        
        return downloaded
    
    def _download_file(self, url: str, output_path: Path) -> bool:
        """Download file from URL"""
        try:
            response = self.session.get(url, timeout=30, stream=True)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            
        except Exception as e:
            print(f"      Download error: {e}")
        
        return False
    
    def _convert_gif_to_video(self, gif_path: Path) -> Optional[str]:
        """Convert GIF to MP4 video using moviepy"""
        try:
            from moviepy.editor import VideoFileClip
            
            video_path = str(gif_path).replace('.gif', '.mp4')
            
            clip = VideoFileClip(str(gif_path))
            clip.write_videofile(
                video_path,
                fps=24,
                codec='libx264',
                audio=False,
                verbose=False,
                logger=None
            )
            clip.close()
            
            # Remove original GIF
            gif_path.unlink()
            
            return video_path
            
        except Exception as e:
            print(f"      GIF conversion error: {e}")
            return str(gif_path)  # Return GIF path as fallback
    
    def fetch_mixed_media(
        self,
        keywords: List[str],
        count: int = 5
    ) -> List[str]:
        """
        Fetch media from multiple sources for variety
        
        Args:
            keywords: List of search terms
            count: Total number of media items to fetch
        """
        all_media = []
        
        # Distribute requests across sources
        per_source = max(1, count // 3)
        
        # Try each source
        for i, keyword in enumerate(keywords[:3]):
            if i == 0 and self.pixabay_key:
                media = self.fetch_from_pixabay(keyword, "video", per_source)
                all_media.extend(media)
            elif i == 1:
                media = self.fetch_hand_drawn_gifs(keyword, per_source)
                all_media.extend(media)
            elif i == 2 and self.tenor_key:
                media = self.fetch_from_tenor(keyword, per_source)
                all_media.extend(media)
        
        # Fill remaining with GIPHY (most accessible)
        remaining = count - len(all_media)
        if remaining > 0 and len(keywords) > 0:
            extra = self.fetch_hand_drawn_gifs(keywords[-1], remaining)
            all_media.extend(extra)
        
        return all_media[:count]


if __name__ == "__main__":
    # Test the fetcher
    fetcher = MultiSourceFetcher()
    
    print("Testing Pixabay...")
    videos = fetcher.fetch_from_pixabay("motivation", "video", 2)
    print(f"Downloaded {len(videos)} videos")
    
    print("\nTesting GIPHY...")
    gifs = fetcher.fetch_hand_drawn_gifs("success", 2)
    print(f"Downloaded {len(gifs)} GIFs")
