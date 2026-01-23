"""
Animated background generator - creates dynamic motion backgrounds
"""

import random
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
from typing import List, Tuple, Callable
from moviepy.editor import VideoClip, ColorClip, CompositeVideoClip

from config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR, FPS


class AnimatedBackgroundGenerator:
    """Generates animated video backgrounds programmatically"""
    
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
    
    def generate_animated_background(
        self, 
        duration: float, 
        style: str = None
    ) -> VideoClip:
        """
        Generate an animated background clip.
        
        Args:
            duration: Length of the clip in seconds
            style: Animation style (gradient_flow, particles, pulse, aurora, etc.)
        """
        styles = ['gradient_flow', 'particles', 'pulse', 'aurora', 'geometric_float']
        if style is None:
            style = random.choice(styles)
        
        if style == 'gradient_flow':
            return self._create_flowing_gradient(duration)
        elif style == 'particles':
            return self._create_particle_animation(duration)
        elif style == 'pulse':
            return self._create_pulsing_gradient(duration)
        elif style == 'aurora':
            return self._create_aurora_effect(duration)
        elif style == 'geometric_float':
            return self._create_floating_shapes(duration)
        else:
            return self._create_flowing_gradient(duration)
    
    def _get_color_palette(self, index: int = None) -> Tuple[Tuple, Tuple, Tuple]:
        """Get a dark, moody color palette with 3 colors"""
        palettes = [
            ((15, 15, 35), (45, 25, 80), (80, 40, 120)),      # Purple
            ((10, 20, 40), (30, 60, 100), (50, 100, 150)),    # Blue
            ((25, 15, 25), (70, 30, 50), (120, 50, 80)),      # Magenta
            ((10, 25, 25), (30, 70, 70), (50, 120, 120)),     # Teal
            ((20, 10, 30), (60, 30, 90), (100, 50, 140)),     # Violet
            ((15, 20, 25), (40, 55, 70), (70, 90, 110)),      # Steel
        ]
        if index is None:
            index = random.randint(0, len(palettes) - 1)
        return palettes[index % len(palettes)]
    
    def _create_flowing_gradient(self, duration: float) -> VideoClip:
        """Create a smoothly flowing gradient animation"""
        color1, color2, color3 = self._get_color_palette()
        
        def make_frame(t):
            # Create flowing gradient
            img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
            
            # Animated wave offset
            wave_speed = 0.5
            wave_offset = t * wave_speed
            
            for y in range(VIDEO_HEIGHT):
                # Base gradient ratio
                base_ratio = y / VIDEO_HEIGHT
                
                # Add flowing wave effect
                wave = 0.1 * math.sin(base_ratio * 4 + wave_offset * 2)
                wave += 0.05 * math.sin(base_ratio * 8 + wave_offset * 3)
                
                ratio = base_ratio + wave
                ratio = max(0, min(1, ratio))
                
                # Interpolate between colors
                if ratio < 0.5:
                    r = ratio * 2
                    c = (
                        int(color1[0] * (1 - r) + color2[0] * r),
                        int(color1[1] * (1 - r) + color2[1] * r),
                        int(color1[2] * (1 - r) + color2[2] * r),
                    )
                else:
                    r = (ratio - 0.5) * 2
                    c = (
                        int(color2[0] * (1 - r) + color3[0] * r),
                        int(color2[1] * (1 - r) + color3[1] * r),
                        int(color2[2] * (1 - r) + color3[2] * r),
                    )
                
                img[y, :] = c
            
            return img
        
        return VideoClip(make_frame, duration=duration).set_fps(FPS)
    
    def _create_pulsing_gradient(self, duration: float) -> VideoClip:
        """Create a pulsing/breathing gradient effect"""
        color1, color2, color3 = self._get_color_palette()
        
        def make_frame(t):
            img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
            
            # Pulsing intensity
            pulse = 0.7 + 0.3 * math.sin(t * 2)
            
            center_y = VIDEO_HEIGHT // 2
            center_x = VIDEO_WIDTH // 2
            max_dist = math.sqrt(center_x**2 + center_y**2)
            
            for y in range(VIDEO_HEIGHT):
                for x in range(VIDEO_WIDTH):
                    dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    ratio = (dist / max_dist) * pulse
                    ratio = min(1, ratio)
                    
                    if ratio < 0.5:
                        r = ratio * 2
                        c = (
                            int(color1[0] * (1 - r) + color2[0] * r),
                            int(color1[1] * (1 - r) + color2[1] * r),
                            int(color1[2] * (1 - r) + color2[2] * r),
                        )
                    else:
                        r = (ratio - 0.5) * 2
                        c = (
                            int(color2[0] * (1 - r) + color3[0] * r),
                            int(color2[1] * (1 - r) + color3[1] * r),
                            int(color2[2] * (1 - r) + color3[2] * r),
                        )
                    
                    img[y, x] = c
            
            return img
        
        return VideoClip(make_frame, duration=duration).set_fps(FPS // 2)  # Lower FPS for performance
    
    def _create_particle_animation(self, duration: float) -> VideoClip:
        """Create floating particles animation"""
        color1, color2, _ = self._get_color_palette()
        
        # Pre-generate particle positions
        num_particles = 40
        particles = []
        for _ in range(num_particles):
            particles.append({
                'x': random.randint(0, VIDEO_WIDTH),
                'y': random.randint(0, VIDEO_HEIGHT),
                'speed_x': random.uniform(-30, 30),
                'speed_y': random.uniform(-50, -10),  # Float upward
                'size': random.randint(3, 12),
                'alpha': random.uniform(0.3, 0.8),
            })
        
        def make_frame(t):
            # Create gradient base
            img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.float32)
            
            for y in range(VIDEO_HEIGHT):
                ratio = y / VIDEO_HEIGHT
                img[y, :] = [
                    color1[0] * (1 - ratio) + color2[0] * ratio,
                    color1[1] * (1 - ratio) + color2[1] * ratio,
                    color1[2] * (1 - ratio) + color2[2] * ratio,
                ]
            
            # Draw particles
            for p in particles:
                # Calculate current position (with wrapping)
                px = (p['x'] + p['speed_x'] * t) % VIDEO_WIDTH
                py = (p['y'] + p['speed_y'] * t) % VIDEO_HEIGHT
                
                # Draw glowing particle
                size = p['size']
                alpha = p['alpha'] * (0.7 + 0.3 * math.sin(t * 3 + p['x']))
                
                for dy in range(-size*2, size*2+1):
                    for dx in range(-size*2, size*2+1):
                        dist = math.sqrt(dx*dx + dy*dy)
                        if dist < size * 2:
                            ix = int(px + dx) % VIDEO_WIDTH
                            iy = int(py + dy) % VIDEO_HEIGHT
                            
                            # Glow falloff
                            glow = max(0, 1 - dist / (size * 2))
                            glow = glow * glow * alpha
                            
                            # Brighten the pixel
                            img[iy, ix] = [
                                min(255, img[iy, ix, 0] + 80 * glow),
                                min(255, img[iy, ix, 1] + 80 * glow),
                                min(255, img[iy, ix, 2] + 120 * glow),
                            ]
            
            return img.astype(np.uint8)
        
        return VideoClip(make_frame, duration=duration).set_fps(FPS)
    
    def _create_aurora_effect(self, duration: float) -> VideoClip:
        """Create aurora borealis-like effect"""
        colors = [
            (20, 80, 60),   # Teal
            (40, 60, 100),  # Blue
            (80, 40, 100),  # Purple
            (30, 90, 70),   # Green-teal
        ]
        
        def make_frame(t):
            img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.float32)
            
            # Dark base
            img[:, :] = [10, 15, 25]
            
            # Multiple aurora bands
            for band in range(4):
                color = colors[band % len(colors)]
                band_offset = band * 0.5
                
                for x in range(VIDEO_WIDTH):
                    # Wave pattern
                    wave1 = math.sin(x * 0.01 + t * 0.5 + band_offset) * 100
                    wave2 = math.sin(x * 0.02 + t * 0.3 + band_offset) * 50
                    wave3 = math.sin(x * 0.005 + t * 0.7 + band_offset) * 150
                    
                    center_y = int(VIDEO_HEIGHT * 0.3 + wave1 + wave2 + wave3 + band * 80)
                    
                    # Draw vertical glow
                    for y in range(VIDEO_HEIGHT):
                        dist = abs(y - center_y)
                        if dist < 200:
                            intensity = (1 - dist / 200) ** 2
                            intensity *= 0.3 + 0.2 * math.sin(t * 2 + x * 0.01)
                            
                            img[y, x, 0] = min(255, img[y, x, 0] + color[0] * intensity)
                            img[y, x, 1] = min(255, img[y, x, 1] + color[1] * intensity)
                            img[y, x, 2] = min(255, img[y, x, 2] + color[2] * intensity)
            
            return img.astype(np.uint8)
        
        return VideoClip(make_frame, duration=duration).set_fps(FPS // 2)
    
    def _create_floating_shapes(self, duration: float) -> VideoClip:
        """Create floating geometric shapes"""
        color1, color2, color3 = self._get_color_palette()
        
        # Pre-generate shapes
        shapes = []
        for _ in range(15):
            shapes.append({
                'x': random.randint(0, VIDEO_WIDTH),
                'y': random.randint(0, VIDEO_HEIGHT),
                'size': random.randint(50, 200),
                'speed_x': random.uniform(-20, 20),
                'speed_y': random.uniform(-20, 20),
                'rotation_speed': random.uniform(-0.5, 0.5),
                'shape_type': random.choice(['circle', 'triangle', 'square']),
                'color_idx': random.randint(0, 2),
            })
        
        shape_colors = [color1, color2, color3]
        
        def make_frame(t):
            # Gradient base
            img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
            draw = ImageDraw.Draw(img)
            
            for y in range(VIDEO_HEIGHT):
                ratio = y / VIDEO_HEIGHT
                c = (
                    int(color1[0] * (1 - ratio) + color2[0] * ratio),
                    int(color1[1] * (1 - ratio) + color2[1] * ratio),
                    int(color1[2] * (1 - ratio) + color2[2] * ratio),
                )
                draw.line([(0, y), (VIDEO_WIDTH, y)], fill=c)
            
            # Draw shapes
            for s in shapes:
                px = (s['x'] + s['speed_x'] * t) % VIDEO_WIDTH
                py = (s['y'] + s['speed_y'] * t) % VIDEO_HEIGHT
                size = s['size']
                color = shape_colors[s['color_idx']]
                
                # Lighter outline color
                outline_color = (
                    min(255, color[0] + 40),
                    min(255, color[1] + 40),
                    min(255, color[2] + 40),
                )
                
                if s['shape_type'] == 'circle':
                    draw.ellipse(
                        [px - size//2, py - size//2, px + size//2, py + size//2],
                        outline=outline_color,
                        width=2
                    )
                elif s['shape_type'] == 'square':
                    draw.rectangle(
                        [px - size//2, py - size//2, px + size//2, py + size//2],
                        outline=outline_color,
                        width=2
                    )
                elif s['shape_type'] == 'triangle':
                    angle = t * s['rotation_speed']
                    points = []
                    for i in range(3):
                        a = angle + i * (2 * math.pi / 3)
                        points.append((
                            px + size//2 * math.cos(a),
                            py + size//2 * math.sin(a)
                        ))
                    draw.polygon(points, outline=outline_color)
            
            return np.array(img)
        
        return VideoClip(make_frame, duration=duration).set_fps(FPS)


if __name__ == "__main__":
    # Test
    generator = AnimatedBackgroundGenerator()
    clip = generator.generate_animated_background(5, style='particles')
    clip.write_videofile("temp/test_animation.mp4", fps=30)
