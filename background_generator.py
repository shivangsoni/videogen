"""
Background generator - creates dynamic backgrounds without external APIs
"""

import random
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
from typing import List, Tuple

from config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR


class BackgroundGenerator:
    """Generates various background styles programmatically"""
    
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
    
    def generate_backgrounds(self, count: int = 5) -> List[str]:
        """Generate multiple unique backgrounds"""
        backgrounds = []
        styles = ['gradient', 'radial', 'particles', 'waves', 'geometric']
        
        for i in range(count):
            style = styles[i % len(styles)]
            path = self._generate_background(style, i)
            backgrounds.append(path)
        
        return backgrounds
    
    def _generate_background(self, style: str, index: int) -> str:
        """Generate a single background of specified style"""
        output_path = self.temp_dir / f"bg_{style}_{index}.jpg"
        
        if style == 'gradient':
            img = self._create_gradient(index)
        elif style == 'radial':
            img = self._create_radial_gradient(index)
        elif style == 'particles':
            img = self._create_particles(index)
        elif style == 'waves':
            img = self._create_waves(index)
        elif style == 'geometric':
            img = self._create_geometric(index)
        else:
            img = self._create_gradient(index)
        
        img.save(output_path, quality=95)
        return str(output_path)
    
    def _get_color_palette(self, index: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Get a dark, moody color palette"""
        palettes = [
            ((15, 15, 35), (45, 25, 80)),       # Deep purple
            ((10, 20, 40), (30, 60, 100)),      # Dark blue
            ((25, 15, 25), (70, 30, 50)),       # Dark magenta
            ((10, 25, 25), (30, 70, 70)),       # Dark teal
            ((20, 10, 30), (60, 30, 90)),       # Purple-violet
            ((15, 15, 15), (50, 50, 70)),       # Dark gray-blue
            ((20, 15, 10), (60, 40, 30)),       # Dark brown-orange
            ((10, 15, 25), (40, 50, 80)),       # Steel blue
        ]
        return palettes[index % len(palettes)]
    
    def _create_gradient(self, index: int) -> Image.Image:
        """Create vertical/diagonal gradient"""
        img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
        draw = ImageDraw.Draw(img)
        
        color1, color2 = self._get_color_palette(index)
        
        # Add slight diagonal variation
        angle = random.uniform(-0.2, 0.2)
        
        for y in range(VIDEO_HEIGHT):
            ratio = y / VIDEO_HEIGHT
            # Add some noise for texture
            noise = random.uniform(-0.02, 0.02)
            ratio = max(0, min(1, ratio + noise))
            
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            
            draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))
        
        # Add subtle vignette
        img = self._add_vignette(img)
        
        return img
    
    def _create_radial_gradient(self, index: int) -> Image.Image:
        """Create radial gradient from center"""
        img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        
        color1, color2 = self._get_color_palette(index)
        
        center_x = VIDEO_WIDTH // 2
        center_y = VIDEO_HEIGHT // 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        for y in range(VIDEO_HEIGHT):
            for x in range(VIDEO_WIDTH):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                ratio = min(1, dist / max_dist)
                
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                
                img[y, x] = [r, g, b]
        
        return Image.fromarray(img)
    
    def _create_particles(self, index: int) -> Image.Image:
        """Create background with floating particles/bokeh effect"""
        color1, color2 = self._get_color_palette(index)
        
        # Start with gradient base
        img = self._create_gradient(index)
        draw = ImageDraw.Draw(img)
        
        # Add glowing particles
        num_particles = random.randint(15, 30)
        
        for _ in range(num_particles):
            x = random.randint(0, VIDEO_WIDTH)
            y = random.randint(0, VIDEO_HEIGHT)
            radius = random.randint(20, 100)
            
            # Create glow color (lighter version of palette)
            glow_color = (
                min(255, color2[0] + 40),
                min(255, color2[1] + 40),
                min(255, color2[2] + 60)
            )
            
            # Draw multiple circles for glow effect
            for r in range(radius, 0, -5):
                alpha = int(20 * (r / radius))
                overlay_color = (
                    glow_color[0],
                    glow_color[1],
                    glow_color[2],
                )
                draw.ellipse(
                    [x - r, y - r, x + r, y + r],
                    fill=(*overlay_color, alpha) if img.mode == 'RGBA' else overlay_color
                )
        
        # Apply blur for soft glow
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
        
        return img
    
    def _create_waves(self, index: int) -> Image.Image:
        """Create abstract wave pattern"""
        img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        
        color1, color2 = self._get_color_palette(index)
        
        # Wave parameters
        num_waves = 5
        
        for y in range(VIDEO_HEIGHT):
            base_ratio = y / VIDEO_HEIGHT
            
            for x in range(VIDEO_WIDTH):
                # Add wave distortion
                wave_offset = 0
                for w in range(num_waves):
                    freq = 0.005 * (w + 1)
                    amp = 0.05 / (w + 1)
                    phase = w * 1.5
                    wave_offset += amp * math.sin(x * freq + phase + y * 0.002)
                
                ratio = base_ratio + wave_offset
                ratio = max(0, min(1, ratio))
                
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                
                img[y, x] = [r, g, b]
        
        result = Image.fromarray(img)
        result = result.filter(ImageFilter.GaussianBlur(radius=2))
        
        return result
    
    def _create_geometric(self, index: int) -> Image.Image:
        """Create geometric pattern with shapes"""
        color1, color2 = self._get_color_palette(index)
        
        # Start with gradient
        img = self._create_gradient(index)
        draw = ImageDraw.Draw(img)
        
        # Add geometric shapes
        num_shapes = random.randint(8, 15)
        
        for _ in range(num_shapes):
            shape_type = random.choice(['line', 'triangle', 'circle'])
            
            # Subtle color variation
            shape_color = (
                min(255, color2[0] + random.randint(10, 30)),
                min(255, color2[1] + random.randint(10, 30)),
                min(255, color2[2] + random.randint(10, 30)),
            )
            
            if shape_type == 'line':
                x1 = random.randint(-100, VIDEO_WIDTH + 100)
                y1 = random.randint(-100, VIDEO_HEIGHT + 100)
                x2 = random.randint(-100, VIDEO_WIDTH + 100)
                y2 = random.randint(-100, VIDEO_HEIGHT + 100)
                draw.line([(x1, y1), (x2, y2)], fill=shape_color, width=random.randint(1, 3))
            
            elif shape_type == 'triangle':
                points = [
                    (random.randint(0, VIDEO_WIDTH), random.randint(0, VIDEO_HEIGHT)),
                    (random.randint(0, VIDEO_WIDTH), random.randint(0, VIDEO_HEIGHT)),
                    (random.randint(0, VIDEO_WIDTH), random.randint(0, VIDEO_HEIGHT)),
                ]
                draw.polygon(points, outline=shape_color)
            
            elif shape_type == 'circle':
                x = random.randint(0, VIDEO_WIDTH)
                y = random.randint(0, VIDEO_HEIGHT)
                r = random.randint(50, 200)
                draw.ellipse([x-r, y-r, x+r, y+r], outline=shape_color)
        
        # Slight blur for softer look
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img
    
    def _add_vignette(self, img: Image.Image) -> Image.Image:
        """Add vignette effect (darker corners)"""
        img_array = np.array(img, dtype=np.float32)
        
        rows, cols = img_array.shape[:2]
        
        # Create vignette mask
        X = np.arange(0, cols)
        Y = np.arange(0, rows)
        X, Y = np.meshgrid(X, Y)
        
        center_x = cols / 2
        center_y = rows / 2
        
        # Distance from center
        dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        max_dist = np.sqrt(center_x**2 + center_y**2)
        
        # Vignette factor
        vignette = 1 - (dist / max_dist) * 0.5
        vignette = np.clip(vignette, 0.5, 1)
        
        # Apply vignette
        for i in range(3):
            img_array[:, :, i] = img_array[:, :, i] * vignette
        
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        
        return Image.fromarray(img_array)
    
    def extract_keywords_from_script(self, segments) -> List[str]:
        """For compatibility - returns empty list as we don't need keywords"""
        return []


# For backwards compatibility
def create_gradient_image(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    color1: tuple = (26, 26, 46),
    color2: tuple = (15, 52, 96)
) -> str:
    """Create a gradient image"""
    generator = BackgroundGenerator()
    return generator._generate_background('gradient', 0)


if __name__ == "__main__":
    # Test the background generator
    generator = BackgroundGenerator()
    backgrounds = generator.generate_backgrounds(count=5)
    
    print(f"Generated {len(backgrounds)} backgrounds:")
    for bg in backgrounds:
        print(f"  - {bg}")
