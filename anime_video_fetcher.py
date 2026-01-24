"""
Anime video fetcher - downloads anime clips using Trace Moe API
Supports keyword-based search for relevant anime clips
"""

import os
import random
import requests
from pathlib import Path
from typing import List, Optional
import time
import urllib.parse

from config import TEMP_DIR


class AnimeVideoFetcher:
    """Fetches anime video clips using Trace Moe API with keyword support"""
    
    # Trace Moe API endpoint
    TRACE_MOE_API = "https://api.trace.moe/search"
    
    # Jikan API (MyAnimeList) for anime search
    JIKAN_API = "https://api.jikan.moe/v4"
    
    # Waifu.pics categories mapped to common keywords
    WAIFU_CATEGORIES = {
        # Action/Fighting
        "action": ["waifu", "kick", "punch"],
        "fight": ["waifu", "kick", "punch"],
        "battle": ["waifu", "kick", "punch"],
        
        # Cute/Kawaii
        "cute": ["waifu", "neko", "smile", "happy"],
        "kawaii": ["waifu", "neko", "smile", "happy"],
        "happy": ["waifu", "smile", "happy", "dance"],
        
        # Dark/Serious
        "dark": ["waifu", "cry"],
        "sad": ["waifu", "cry"],
        "serious": ["waifu"],
        
        # Nature/Aesthetic
        "nature": ["waifu", "neko"],
        "aesthetic": ["waifu", "neko"],
        "beautiful": ["waifu", "neko"],
        
        # Characters
        "cat": ["neko", "awoo"],
        "neko": ["neko"],
        "wolf": ["awoo"],
        
        # Specific characters from waifu.pics
        "megumin": ["megumin"],
        "shinobu": ["shinobu"],
    }
    
    # Default waifu.pics endpoints
    DEFAULT_ENDPOINTS = ["waifu", "neko", "shinobu", "megumin", "awoo"]
    
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _search_anime_by_keyword(self, keyword: str) -> List[str]:
        """Search for anime images using Jikan API (MyAnimeList)"""
        anime_images = []
        
        try:
            # Search anime by keyword
            search_url = f"{self.JIKAN_API}/anime"
            params = {
                'q': keyword,
                'limit': 5,
                'sfw': 'true'
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("data", [])
                
                for anime in results:
                    # Get main image
                    images = anime.get("images", {})
                    jpg = images.get("jpg", {})
                    if jpg.get("large_image_url"):
                        anime_images.append(jpg["large_image_url"])
                    elif jpg.get("image_url"):
                        anime_images.append(jpg["image_url"])
                        
            time.sleep(0.5)  # Jikan rate limiting
            
        except Exception as e:
            print(f"      Jikan search failed for '{keyword}': {e}")
        
        return anime_images
    
    def _get_waifu_image(self, category: str = "waifu") -> Optional[str]:
        """Get anime image from waifu.pics API"""
        try:
            url = f"https://api.waifu.pics/sfw/{category}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("url")
        except Exception as e:
            print(f"      waifu.pics failed for {category}: {e}")
        return None
    
    def _get_anime_images_for_keywords(self, keywords: List[str]) -> List[str]:
        """Get anime images relevant to the provided keywords"""
        images = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # Try Jikan API first for specific anime searches
            jikan_images = self._search_anime_by_keyword(keyword_lower)
            images.extend(jikan_images[:2])  # Limit per keyword
            
            # Also try waifu.pics with mapped categories
            if keyword_lower in self.WAIFU_CATEGORIES:
                categories = self.WAIFU_CATEGORIES[keyword_lower]
                for cat in categories[:2]:
                    img = self._get_waifu_image(cat)
                    if img:
                        images.append(img)
        
        # If no keyword matches, use default categories
        if not images:
            for cat in random.sample(self.DEFAULT_ENDPOINTS, min(3, len(self.DEFAULT_ENDPOINTS))):
                img = self._get_waifu_image(cat)
                if img:
                    images.append(img)
        
        return images
    
    def _get_random_anime_image(self) -> Optional[str]:
        """Get a random anime image URL for Trace Moe search"""
        categories = random.sample(self.DEFAULT_ENDPOINTS, len(self.DEFAULT_ENDPOINTS))
        for category in categories:
            img = self._get_waifu_image(category)
            if img:
                return img
        return None
    
    def _search_trace_moe(self, image_url: str) -> Optional[dict]:
        """Search Trace Moe with an image URL"""
        try:
            params = {
                'url': image_url,
                'cutBorders': 'true'
            }
            
            response = self.session.get(
                self.TRACE_MOE_API,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("result", [])
                
                # Filter results with video previews
                valid_results = [
                    r for r in results 
                    if r.get("video") and r.get("similarity", 0) > 0.5
                ]
                
                if valid_results:
                    return random.choice(valid_results[:5])  # Pick from top 5
            
        except Exception as e:
            print(f"      Trace Moe search failed: {e}")
        
        return None
    
    def _download_video(self, video_url: str, output_path: Path) -> Optional[str]:
        """Download video from URL"""
        try:
            # Add size parameter for better quality
            if "?" in video_url:
                video_url += "&size=l"
            else:
                video_url += "?size=l"
            
            response = self.session.get(video_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return str(output_path)
                
        except Exception as e:
            print(f"      Download error: {e}")
        
        return None
    
    def fetch_anime_clips(self, count: int = 3, keywords: List[str] = None) -> List[str]:
        """
        Fetch anime video clips using Trace Moe.
        
        Args:
            count: Number of clips to fetch
            keywords: Optional keywords to search for relevant anime
            
        Returns:
            List of paths to downloaded video clips
        """
        downloaded = []
        attempts = 0
        max_attempts = count * 4  # Allow some failures
        used_images = set()
        
        # Get anime images based on keywords
        if keywords:
            print(f"      Searching for anime clips related to: {', '.join(keywords)}")
            anime_images = self._get_anime_images_for_keywords(keywords)
            random.shuffle(anime_images)
            print(f"      Found {len(anime_images)} anime images to search")
        else:
            anime_images = []
        
        print(f"      Fetching {count} anime clips from Trace Moe...")
        
        while len(downloaded) < count and attempts < max_attempts:
            attempts += 1
            
            # Try keyword-based images first, then random
            if anime_images:
                image_url = anime_images.pop(0) if anime_images else None
            else:
                image_url = self._get_random_anime_image()
            
            if not image_url or image_url in used_images:
                # Get a new random image if we've used this one
                image_url = self._get_random_anime_image()
                if not image_url:
                    print(f"      Attempt {attempts}: No image found")
                    continue
            
            used_images.add(image_url)
            print(f"      Attempt {attempts}: Searching Trace Moe...")
            
            # Search Trace Moe
            result = self._search_trace_moe(image_url)
            if not result:
                print(f"      Attempt {attempts}: No match found")
                time.sleep(0.5)  # Rate limiting
                continue
            
            # Get video preview URL
            video_url = result.get("video")
            if not video_url:
                continue
            
            anime_name = result.get("filename", "unknown")[:40]
            print(f"      Found: {anime_name}")
            
            # Download the clip
            output_path = self.temp_dir / f"anime_clip_{len(downloaded)}.mp4"
            video_path = self._download_video(video_url, output_path)
            
            if video_path:
                downloaded.append(video_path)
                print(f"      Downloaded anime clip {len(downloaded)}/{count}")
            
            time.sleep(1)  # Rate limiting between requests
        
        if not downloaded:
            print("      Warning: Could not fetch any anime clips")
        
        return downloaded
    
    def fetch_clip_info(self, count: int = 3, keywords: List[str] = None) -> List[dict]:
        """
        Fetch anime clip metadata without downloading (for UI preview).
        
        Returns:
            List of dicts with clip info
        """
        clips_info = []
        attempts = 0
        max_attempts = count * 3
        
        # Get anime images based on keywords
        if keywords:
            anime_images = self._get_anime_images_for_keywords(keywords)
            random.shuffle(anime_images)
        else:
            anime_images = []
        
        while len(clips_info) < count and attempts < max_attempts:
            attempts += 1
            
            if anime_images:
                image_url = anime_images.pop(0)
            else:
                image_url = self._get_random_anime_image()
            
            if not image_url:
                continue
            
            result = self._search_trace_moe(image_url)
            if result:
                clips_info.append({
                    "title": result.get("filename", "Unknown Anime"),
                    "episode": result.get("episode", "?"),
                    "similarity": f"{result.get('similarity', 0) * 100:.1f}%",
                    "preview": result.get("image", ""),
                })
            
            time.sleep(0.5)
        
        return clips_info
