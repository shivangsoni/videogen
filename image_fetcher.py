"""
Image fetcher - downloads free stock images from Pexels API
"""

import os
import random
import requests
import numpy as np
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote
from PIL import Image

from config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR


# Free stock image APIs (no API key required for limited use)
PEXELS_API_URL = "https://api.pexels.com/v1/search"
PIXABAY_API_URL = "https://pixabay.com/api/"

# Fallback: Use Unsplash Source (no API key needed)
UNSPLASH_SOURCE_URL = "https://source.unsplash.com"


class ImageFetcher:
    def __init__(self, pexels_api_key: Optional[str] = None):
        """
        Initialize image fetcher.
        
        Args:
            pexels_api_key: Optional Pexels API key for better rate limits.
                           Get free key at: https://www.pexels.com/api/
        """
        self.pexels_api_key = pexels_api_key or os.environ.get("PEXELS_API_KEY")
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self.downloaded_images: List[str] = []
    
    def search_and_download_images(
        self,
        keywords: List[str],
        count: int = 5
    ) -> List[str]:
        """
        Search and download images based on keywords.
        
        Args:
            keywords: List of search terms
            count: Number of images to download
            
        Returns:
            List of paths to downloaded images
        """
        images = []
        attempted_keywords = set()
        
        for i, keyword in enumerate(keywords[:count]):
            if keyword in attempted_keywords:
                continue
            attempted_keywords.add(keyword)
            
            print(f"  Fetching image for: {keyword}")
            image_path = self._download_image(keyword, i)
            if image_path:
                images.append(image_path)
        
        # If we couldn't get any images, create gradient backgrounds
        if not images:
            print("      Creating gradient backgrounds as fallback...")
            for i in range(min(count, 5)):
                gradient_path = self._create_gradient_fallback(i)
                if gradient_path:
                    images.append(gradient_path)
        
        self.downloaded_images = images
        return images
    
    def _download_image(self, keyword: str, index: int) -> Optional[str]:
        """Download a single image"""
        output_path = self.temp_dir / f"bg_image_{index}.jpg"
        
        # Try Pexels first if we have API key
        if self.pexels_api_key:
            if self._download_from_pexels(keyword, output_path):
                return str(output_path)
        
        # Fallback to Unsplash Source (no API key needed)
        if self._download_from_unsplash(keyword, output_path):
            return str(output_path)
        
        return None
    
    def _download_from_pexels(self, keyword: str, output_path: Path) -> bool:
        """Download from Pexels API"""
        try:
            headers = {"Authorization": self.pexels_api_key}
            params = {
                "query": keyword,
                "per_page": 15,
                "orientation": "portrait",  # Vertical for shorts
                "size": "large"
            }
            
            response = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                
                if photos:
                    # Pick a random photo from results
                    photo = random.choice(photos)
                    image_url = photo["src"]["portrait"]  # Vertical format
                    
                    return self._download_file(image_url, output_path)
            
        except Exception as e:
            print(f"    Pexels error: {e}")
        
        return False
    
    def _download_from_unsplash(self, keyword: str, output_path: Path) -> bool:
        """Download from Unsplash Source (no API key needed)"""
        try:
            # Unsplash Source URL format for specific size
            # Portrait orientation for YouTube Shorts
            url = f"{UNSPLASH_SOURCE_URL}/{VIDEO_WIDTH}x{VIDEO_HEIGHT}/?{quote(keyword)},dark"
            
            return self._download_file(url, output_path)
            
        except Exception as e:
            print(f"    Unsplash error: {e}")
        
        return False
    
    def _download_file(self, url: str, output_path: Path) -> bool:
        """Download file from URL"""
        try:
            response = requests.get(url, timeout=30, stream=True)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
                
        except Exception as e:
            print(f"    Download error: {e}")
        
        return False
    
    def _create_gradient_fallback(self, index: int) -> Optional[str]:
        """Create a gradient image as fallback"""
        # Different color combinations for variety
        gradients = [
            ((26, 26, 46), (15, 52, 96)),      # Dark blue
            ((25, 0, 25), (60, 20, 60)),        # Dark purple
            ((10, 10, 30), (40, 40, 80)),       # Navy
            ((20, 20, 20), (50, 50, 70)),       # Dark gray-blue
            ((30, 15, 30), (70, 30, 50)),       # Dark magenta
        ]
        
        color1, color2 = gradients[index % len(gradients)]
        
        # Create gradient array
        gradient = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        
        for y in range(VIDEO_HEIGHT):
            ratio = y / VIDEO_HEIGHT
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            gradient[y, :] = [r, g, b]
        
        img = Image.fromarray(gradient)
        output_path = self.temp_dir / f"gradient_bg_{index}.jpg"
        img.save(output_path, quality=95)
        
        return str(output_path)
    
    def extract_keywords_from_script(self, segments) -> List[str]:
        """Extract relevant keywords from script segments for image search"""
        keywords = []
        
        # Common keyword mappings for motivational content
        keyword_mappings = {
            "sleep": ["sleep", "bedroom", "night", "rest"],
            "diet": ["healthy food", "nutrition", "vegetables", "kitchen"],
            "room": ["clean room", "minimal room", "organized space"],
            "mindset": ["brain", "thinking", "meditation", "focus"],
            "discipline": ["workout", "training", "dedication", "routine"],
            "chaos": ["storm", "chaos", "confusion", "mess"],
            "life": ["lifestyle", "success", "motivation", "journey"],
            "motivation": ["motivation", "inspiration", "goal", "achievement"],
            "truth": ["truth", "wisdom", "knowledge", "insight"],
            "basic": ["simple", "minimal", "foundation", "basics"],
        }
        
        for segment in segments:
            text_lower = segment.text.lower()
            
            # Check for keyword matches
            for key, search_terms in keyword_mappings.items():
                if key in text_lower:
                    keywords.append(random.choice(search_terms))
                    break
            else:
                # Default keywords based on segment type
                if segment.segment_type == 'hook':
                    keywords.append("motivation dark")
                elif segment.segment_type == 'cta':
                    keywords.append("success inspiration")
                else:
                    keywords.append("abstract dark minimal")
        
        return keywords


def create_gradient_image(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    color1: tuple = (26, 26, 46),
    color2: tuple = (15, 52, 96)
) -> str:
    """Create a gradient image as fallback"""
    from PIL import Image
    import numpy as np
    
    # Create gradient array
    gradient = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        gradient[y, :] = [r, g, b]
    
    img = Image.fromarray(gradient)
    
    temp_dir = Path(TEMP_DIR)
    temp_dir.mkdir(exist_ok=True)
    output_path = temp_dir / "gradient_bg.jpg"
    img.save(output_path, quality=95)
    
    return str(output_path)


if __name__ == "__main__":
    # Test the image fetcher
    fetcher = ImageFetcher()
    
    keywords = ["motivation", "discipline", "success"]
    images = fetcher.search_and_download_images(keywords, count=3)
    
    print(f"\nDownloaded {len(images)} images:")
    for img in images:
        print(f"  - {img}")
