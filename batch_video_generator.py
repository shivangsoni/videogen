#!/usr/bin/env python3
"""
Batch Video Generator for YouTube Shorts
Generates videos in multiple languages from youtubeshorts folder structure
and publishes them to YouTube.

Folder structure expected:
    youtubeshorts/
        Video Name/
            script.txt          - The video script
            metadata.txt        - Keywords for stock videos
            youtube_publish.txt - Title and description
            
Usage:
    python batch_video_generator.py                    # Process all folders
    python batch_video_generator.py --folder "Early Dating Truth"  # Specific folder
    python batch_video_generator.py --languages en,hi,es  # Specific languages
    python batch_video_generator.py --no-publish       # Generate only, don't publish
"""

import os
import sys
import json
import argparse
import shutil
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Ignore SIGINT (Ctrl+C) during video processing to prevent interruptions
def signal_handler(sig, frame):
    print("\n[!] Interrupt received but ignored during processing. Use Ctrl+Break to force exit.")
    
signal.signal(signal.SIGINT, signal_handler)

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from script_parser import parse_script
from video_generator import VideoGenerator
from audio_generator import AudioGenerator

# ============================================================================
# CONFIGURATION
# ============================================================================

YOUTUBESHORTS_DIR = Path(__file__).parent / "youtubeshorts"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# All supported languages with their default voice settings
LANGUAGES = {
    "English": {"voice_type": "Female", "voice_id": "en-US-JennyNeural", "code": "en"},
    "Hindi": {"voice_type": "Female", "voice_id": "hi-IN-SwaraNeural", "code": "hi"},
    "Kannada": {"voice_type": "Female", "voice_id": "kn-IN-SapnaNeural", "code": "kn"},
    "Spanish": {"voice_type": "Female", "voice_id": "es-ES-ElviraNeural", "code": "es"},
    "French": {"voice_type": "Female", "voice_id": "fr-FR-DeniseNeural", "code": "fr"},
    "German": {"voice_type": "Female", "voice_id": "de-DE-KatjaNeural", "code": "de"},
    "Portuguese": {"voice_type": "Female", "voice_id": "pt-BR-FranciscaNeural", "code": "pt"},
    "Italian": {"voice_type": "Female", "voice_id": "it-IT-ElsaNeural", "code": "it"},
    "Japanese": {"voice_type": "Female", "voice_id": "ja-JP-NanamiNeural", "code": "ja"},
    "Korean": {"voice_type": "Female", "voice_id": "ko-KR-SunHiNeural", "code": "ko"},
    "Chinese": {"voice_type": "Female", "voice_id": "zh-CN-XiaoxiaoNeural", "code": "zh"},
    "Arabic": {"voice_type": "Female", "voice_id": "ar-SA-ZariyahNeural", "code": "ar"},
    "Russian": {"voice_type": "Female", "voice_id": "ru-RU-SvetlanaNeural", "code": "ru"},
    "Dutch": {"voice_type": "Female", "voice_id": "nl-NL-ColetteNeural", "code": "nl"},
    "Turkish": {"voice_type": "Female", "voice_id": "tr-TR-EmelNeural", "code": "tr"},
    "Polish": {"voice_type": "Female", "voice_id": "pl-PL-ZofiaNeural", "code": "pl"},
    "Swedish": {"voice_type": "Female", "voice_id": "sv-SE-SofieNeural", "code": "sv"},
    "Norwegian": {"voice_type": "Female", "voice_id": "nb-NO-PernilleNeural", "code": "nb"},
    "Danish": {"voice_type": "Female", "voice_id": "da-DK-ChristelNeural", "code": "da"},
}

# Language code to full name mapping
LANG_CODE_TO_NAME = {v["code"]: k for k, v in LANGUAGES.items()}

# YouTube category IDs based on language/region
# https://developers.google.com/youtube/v3/docs/videoCategories/list
LANGUAGE_CATEGORIES = {
    "English": "22",      # People & Blogs
    "Hindi": "24",        # Entertainment
    "Kannada": "24",      # Entertainment
    "Spanish": "24",      # Entertainment
    "French": "22",       # People & Blogs
    "German": "22",       # People & Blogs
    "Portuguese": "24",   # Entertainment
    "Italian": "22",      # People & Blogs
    "Japanese": "24",     # Entertainment
    "Korean": "24",       # Entertainment
    "Chinese": "24",      # Entertainment
    "Arabic": "24",       # Entertainment
    "Russian": "24",      # Entertainment
    "Dutch": "22",        # People & Blogs
    "Turkish": "24",      # Entertainment
    "Polish": "22",       # People & Blogs
    "Swedish": "22",      # People & Blogs
    "Norwegian": "22",    # People & Blogs
    "Danish": "22",       # People & Blogs
}
# Category IDs: 1=Film, 2=Autos, 10=Music, 15=Pets, 17=Sports, 
# 19=Travel, 20=Gaming, 22=People&Blogs, 23=Comedy, 24=Entertainment, 
# 25=News, 26=Howto, 27=Education, 28=Science

# ============================================================================
# FILE PARSING
# ============================================================================

def parse_metadata(filepath: Path) -> Dict:
    """Parse metadata.txt for keywords and other settings"""
    metadata = {"keywords": []}
    
    if not filepath.exists():
        return metadata
    
    content = filepath.read_text(encoding="utf-8")
    for line in content.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == "keywords":
                metadata["keywords"] = [k.strip() for k in value.split(",") if k.strip()]
            else:
                metadata[key] = value
    
    return metadata


def parse_youtube_publish(filepath: Path) -> Dict:
    """Parse youtube_publish.txt for title and description"""
    result = {"title": "", "description": ""}
    
    if not filepath.exists():
        return result
    
    content = filepath.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    current_field = None
    description_lines = []
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if line_lower.startswith("title:"):
            result["title"] = line.split(":", 1)[1].strip()
            current_field = "title"
        elif line_lower.startswith("description:"):
            desc_part = line.split(":", 1)[1].strip()
            if desc_part:
                description_lines.append(desc_part)
            current_field = "description"
        elif current_field == "description":
            description_lines.append(line.strip())
    
    result["description"] = "\n".join(description_lines).strip()
    return result


def parse_script_file(filepath: Path) -> str:
    """Read script.txt content"""
    if not filepath.exists():
        return ""
    return filepath.read_text(encoding="utf-8")


# ============================================================================
# VIDEO GENERATION
# ============================================================================

def generate_video_for_language(
    script_text: str,
    keywords: List[str],
    language: str,
    output_path: Path,
    use_anime_clips: bool = False
) -> Optional[Path]:
    """Generate a video for a specific language"""
    
    if language not in LANGUAGES:
        print(f"  [ERROR] Unsupported language: {language}")
        return None
    
    lang_config = LANGUAGES[language]
    voice = f"{language} - {lang_config['voice_type']}"
    voice_id = lang_config["voice_id"]
    
    print(f"  Generating {language} video...")
    print(f"    Voice: {voice_id}")
    print(f"    Keywords: {', '.join(keywords) if keywords else 'none'}")
    
    try:
        # Parse script
        segments = parse_script(script_text)
        if not segments:
            print(f"  [ERROR] Could not parse script")
            return None
        
        # Create video generator
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        generator.audio_generator.voice = voice
        generator.audio_generator.voice_id = voice_id
        
        # Generate video
        output_filename = output_path.name
        
        def progress_callback(pct, msg):
            print(f"    [{pct:.0%}] {msg}")
        
        result_path = generator.generate_video(
            segments=segments,
            output_filename=output_filename,
            stock_keywords=keywords if keywords else None,
            target_language=voice,
            progress_callback=progress_callback,
            use_anime_clips=use_anime_clips,
        )
        
        # Move to desired location
        if result_path and Path(result_path).exists():
            shutil.move(result_path, output_path)
            print(f"    ✓ Saved to: {output_path}")
            generator.cleanup_temp_files()
            return output_path
        
        return None
        
    except Exception as e:
        print(f"  [ERROR] Failed to generate {language} video: {e}")
        return None


# ============================================================================
# YOUTUBE PUBLISHING
# ============================================================================

class YouTubePublisher:
    """YouTube API wrapper for publishing videos"""
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self.accounts = self._load_accounts()
    
    def _load_accounts(self) -> Dict:
        """Load saved YouTube account credentials"""
        creds_dir = Path(__file__).parent / ".youtube_creds"
        accounts = {}
        
        if creds_dir.exists():
            for cred_file in creds_dir.glob("*.json"):
                account_name = cred_file.stem
                accounts[account_name] = cred_file
        
        return accounts
    
    def list_accounts(self) -> List[str]:
        """List available YouTube accounts"""
        return list(self.accounts.keys())
    
    def authenticate(self, account_name: str) -> bool:
        """Authenticate with a specific YouTube account"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
            
            creds_file = self.accounts.get(account_name)
            if not creds_file:
                print(f"[ERROR] Account '{account_name}' not found")
                return False
            
            # Load credentials
            creds = Credentials.from_authorized_user_file(str(creds_file), SCOPES)
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.credentials = creds
            self.youtube = build('youtube', 'v3', credentials=creds)
            print(f"✓ Authenticated as: {account_name}")
            return True
            
        except ImportError:
            print("[ERROR] Google API libraries not installed.")
            print("Run: pip install google-auth-oauthlib google-api-python-client")
            return False
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False
    
    def setup_new_account(self, account_name: str, client_secrets_file: str) -> bool:
        """Set up a new YouTube account with OAuth"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
            
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            credentials = flow.run_local_server(port=8080)
            
            # Save credentials
            creds_dir = Path(__file__).parent / ".youtube_creds"
            creds_dir.mkdir(exist_ok=True)
            
            creds_file = creds_dir / f"{account_name}.json"
            creds_file.write_text(credentials.to_json())
            
            self.accounts[account_name] = creds_file
            print(f"✓ Account '{account_name}' saved successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Setup failed: {e}")
            return False
    
    def publish_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str] = None,
        privacy: str = "private",  # private, unlisted, public
        category_id: str = "22",   # 22 = People & Blogs
        made_for_kids: bool = False
    ) -> Optional[str]:
        """Publish a video to YouTube"""
        
        if not self.youtube:
            print("[ERROR] Not authenticated. Call authenticate() first.")
            return None
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title[:100],  # Max 100 chars
                    'description': description[:5000],  # Max 5000 chars
                    'tags': tags[:500] if tags else [],  # Max 500 tags
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': made_for_kids,
                    'shorts': {
                        'shortsVideoMetadata': {}  # Mark as Short
                    }
                }
            }
            
            # Upload video
            media = MediaFileUpload(
                str(video_path),
                mimetype='video/mp4',
                resumable=True
            )
            
            print(f"  Uploading: {video_path.name}")
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"    Upload progress: {int(status.progress() * 100)}%")
            
            video_id = response.get('id')
            video_url = f"https://youtube.com/shorts/{video_id}"
            print(f"  ✓ Published: {video_url}")
            
            return video_id
            
        except Exception as e:
            print(f"  [ERROR] Upload failed: {e}")
            return None


# ============================================================================
# MAIN BATCH PROCESSOR
# ============================================================================

def process_folder(
    folder_path: Path,
    languages: List[str],
    publish: bool = False,
    youtube_account: str = None,
    use_anime_clips: bool = False
) -> Dict:
    """Process a single shorts folder and generate videos"""
    
    folder_name = folder_path.name
    print(f"\n{'='*60}")
    print(f"Processing: {folder_name}")
    print(f"{'='*60}")
    
    # Parse input files
    script_file = folder_path / "script.txt"
    metadata_file = folder_path / "metadata.txt"
    publish_file = folder_path / "youtube_publish.txt"
    
    if not script_file.exists():
        print(f"[ERROR] script.txt not found in {folder_path}")
        return {"folder": folder_name, "status": "error", "videos": []}
    
    script_text = parse_script_file(script_file)
    metadata = parse_metadata(metadata_file)
    youtube_info = parse_youtube_publish(publish_file)
    
    print(f"Title: {youtube_info['title']}")
    print(f"Keywords: {', '.join(metadata['keywords'])}")
    print(f"Languages: {', '.join(languages)}")
    
    # Generate videos for each language
    results = {"folder": folder_name, "status": "success", "videos": []}
    
    for language in languages:
        lang_code = LANGUAGES.get(language, {}).get("code", language.lower()[:2])
        output_filename = f"{folder_name}_{lang_code}.mp4"
        output_path = folder_path / output_filename
        
        # Skip if already exists (unless force regenerate)
        if output_path.exists():
            print(f"\n  [{language}] Already exists: {output_filename}")
            results["videos"].append({
                "language": language,
                "path": str(output_path),
                "status": "exists"
            })
            continue
        
        print(f"\n  [{language}] Generating...")
        video_path = generate_video_for_language(
            script_text=script_text,
            keywords=metadata["keywords"],
            language=language,
            output_path=output_path,
            use_anime_clips=use_anime_clips
        )
        
        if video_path:
            results["videos"].append({
                "language": language,
                "path": str(video_path),
                "status": "generated"
            })
        else:
            results["videos"].append({
                "language": language,
                "path": None,
                "status": "failed"
            })
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate YouTube Shorts videos in multiple languages"
    )
    parser.add_argument(
        "--folder", "-f",
        help="Process only a specific folder name"
    )
    parser.add_argument(
        "--languages", "-l",
        help="Comma-separated list of languages (default: all)",
        default=None
    )
    parser.add_argument(
        "--publish", "-p",
        action="store_true",
        help="Publish videos to YouTube after generation"
    )
    parser.add_argument(
        "--account", "-a",
        help="YouTube account name to use for publishing"
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List available YouTube accounts"
    )
    parser.add_argument(
        "--setup-account",
        nargs=2,
        metavar=("NAME", "CLIENT_SECRETS"),
        help="Set up a new YouTube account: --setup-account myaccount client_secrets.json"
    )
    parser.add_argument(
        "--anime",
        action="store_true",
        help="Use anime clips instead of stock videos"
    )
    parser.add_argument(
        "--english-only",
        action="store_true",
        help="Generate only English version"
    )
    
    args = parser.parse_args()
    
    # Handle account setup
    if args.setup_account:
        publisher = YouTubePublisher()
        publisher.setup_new_account(args.setup_account[0], args.setup_account[1])
        return
    
    # List accounts
    if args.list_accounts:
        publisher = YouTubePublisher()
        accounts = publisher.list_accounts()
        if accounts:
            print("Available YouTube accounts:")
            for acc in accounts:
                print(f"  - {acc}")
        else:
            print("No YouTube accounts configured.")
            print("Use --setup-account NAME CLIENT_SECRETS to add one.")
        return
    
    # Determine languages to process
    if args.english_only:
        languages = ["English"]
    elif args.languages:
        # Parse language codes or names
        lang_list = [l.strip() for l in args.languages.split(",")]
        languages = []
        for l in lang_list:
            if l in LANGUAGES:
                languages.append(l)
            elif l in LANG_CODE_TO_NAME:
                languages.append(LANG_CODE_TO_NAME[l])
            else:
                print(f"Warning: Unknown language '{l}', skipping")
        if not languages:
            print("No valid languages specified")
            return
    else:
        languages = list(LANGUAGES.keys())
    
    # Find folders to process
    if not YOUTUBESHORTS_DIR.exists():
        print(f"[ERROR] Shorts directory not found: {YOUTUBESHORTS_DIR}")
        print("Create the 'youtubeshorts' folder and add your video folders.")
        return
    
    folders = []
    if args.folder:
        specific_folder = YOUTUBESHORTS_DIR / args.folder
        if specific_folder.exists():
            folders = [specific_folder]
        else:
            print(f"[ERROR] Folder not found: {args.folder}")
            return
    else:
        folders = [f for f in YOUTUBESHORTS_DIR.iterdir() if f.is_dir()]
    
    if not folders:
        print("No folders found to process")
        return
    
    print(f"\n{'#'*60}")
    print(f"BATCH VIDEO GENERATOR")
    print(f"{'#'*60}")
    print(f"Folders to process: {len(folders)}")
    print(f"Languages: {len(languages)}")
    print(f"Publish to YouTube: {args.publish}")
    if args.account:
        print(f"YouTube account: {args.account}")
    
    # Initialize YouTube publisher if needed
    publisher = None
    if args.publish:
        publisher = YouTubePublisher()
        if args.account:
            if not publisher.authenticate(args.account):
                print("Failed to authenticate. Continuing without publishing.")
                args.publish = False
        else:
            accounts = publisher.list_accounts()
            if accounts:
                print(f"\nAvailable accounts: {', '.join(accounts)}")
                print("Use --account NAME to specify which account to use")
            args.publish = False
    
    # Process each folder
    all_results = []
    for folder in folders:
        results = process_folder(
            folder_path=folder,
            languages=languages,
            publish=args.publish,
            youtube_account=args.account,
            use_anime_clips=args.anime
        )
        all_results.append(results)
        
        # Publish videos if requested
        if args.publish and publisher and publisher.youtube:
            youtube_info = parse_youtube_publish(folder / "youtube_publish.txt")
            metadata = parse_metadata(folder / "metadata.txt")
            
            for video in results["videos"]:
                # Publish generated OR existing videos
                if video["status"] in ("generated", "exists") and video["path"]:
                    lang = video["language"]
                    title = f"{youtube_info['title']} ({lang})"
                    category_id = LANGUAGE_CATEGORIES.get(lang, "22")
                    
                    # Build tags from metadata keywords + language
                    tags = metadata.get("keywords", []) + ["shorts", "viral", lang.lower()]
                    
                    print(f"\n  Publishing {lang} video (Category: {category_id})...")
                    publisher.publish_video(
                        video_path=Path(video["path"]),
                        title=title,
                        description=youtube_info["description"],
                        tags=tags,
                        category_id=category_id,
                        privacy="private"  # Start as private for review
                    )
    
    # Summary
    print(f"\n{'#'*60}")
    print("SUMMARY")
    print(f"{'#'*60}")
    
    for result in all_results:
        print(f"\n{result['folder']}:")
        for video in result["videos"]:
            status_icon = "✓" if video["status"] in ("generated", "exists") else "⊘" if video["status"] == "skipped" else "✗"
            print(f"  {status_icon} {video['language']}: {video['status']}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
