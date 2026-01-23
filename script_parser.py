"""
Script parser for converting text scripts into structured segments
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class ScriptSegment:
    """Represents a segment of the script"""
    segment_type: str  # 'hook', 'core', 'cta'
    text: str
    display_lines: List[str]  # Lines to display on screen


def parse_script(script_text: str) -> List[ScriptSegment]:
    """
    Parse a script file into structured segments.
    
    Expected format:
    Hook (0–2s):
    <hook text>
    
    Core:
    <main content>
    
    End (CTA):
    <call to action>
    """
    segments = []
    
    # Normalize line endings
    script_text = script_text.replace('\r\n', '\n')
    
    # Split into sections
    sections = re.split(r'\n(?=Hook|Core|End)', script_text, flags=re.IGNORECASE)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # Determine section type
        if section.lower().startswith('hook'):
            segment_type = 'hook'
            # Remove the header line
            content = re.sub(r'^Hook.*?:\s*\n?', '', section, flags=re.IGNORECASE).strip()
        elif section.lower().startswith('core'):
            segment_type = 'core'
            content = re.sub(r'^Core.*?:\s*\n?', '', section, flags=re.IGNORECASE).strip()
        elif section.lower().startswith('end'):
            segment_type = 'cta'
            content = re.sub(r'^End.*?:\s*\n?', '', section, flags=re.IGNORECASE).strip()
        else:
            # Default to core content
            segment_type = 'core'
            content = section
        
        if content:
            # Split content into display lines (sentences or short phrases)
            display_lines = split_into_display_lines(content)
            
            segments.append(ScriptSegment(
                segment_type=segment_type,
                text=content,
                display_lines=display_lines
            ))
    
    return segments


def split_into_display_lines(text: str) -> List[str]:
    """
    Split text into lines suitable for display on screen.
    Each line should be short enough to be readable.
    """
    lines = []
    
    # First split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        # Split by single newlines
        para_lines = para.split('\n')
        
        for line in para_lines:
            line = line.strip()
            if not line:
                continue
                
            # If line is too long, split by sentences
            if len(line) > 50:
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        lines.append(sentence)
            else:
                lines.append(line)
    
    return lines


def get_full_narration_text(segments: List[ScriptSegment]) -> str:
    """Get the full text for narration/TTS"""
    full_text = []
    for segment in segments:
        full_text.append(segment.text)
    return " ".join(full_text)


if __name__ == "__main__":
    # Test the parser
    test_script = """Hook (0–2s):
Here's how to unfuck your life—no motivation required.

Core:
Fix your sleep.
Fix your diet.
Fix your room.

You don't need a new mindset.
You need basic discipline.

Chaos outside
creates chaos inside.

End (CTA):
Follow for more raw truth."""

    segments = parse_script(test_script)
    for seg in segments:
        print(f"\n[{seg.segment_type.upper()}]")
        print(f"Text: {seg.text}")
        print(f"Display lines: {seg.display_lines}")
