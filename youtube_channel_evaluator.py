#!/usr/bin/env python3
"""
YouTube Channel Evaluator
Analyzes YouTube channel performance and provides growth recommendations.

Usage:
    python youtube_channel_evaluator.py --account myaccount
    python youtube_channel_evaluator.py --channel-id UCxxxxxx
    python youtube_channel_evaluator.py --account myaccount --detailed
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ChannelStats:
    """Channel statistics container"""
    channel_id: str
    channel_name: str
    subscriber_count: int
    view_count: int
    video_count: int
    created_at: Optional[str] = None
    description: Optional[str] = None
    custom_url: Optional[str] = None


@dataclass
class VideoStats:
    """Video statistics container"""
    video_id: str
    title: str
    views: int
    likes: int
    comments: int
    published_at: str
    duration: str
    is_short: bool


class YouTubeChannelEvaluator:
    """Evaluates YouTube channel performance and provides recommendations"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',
        'https://www.googleapis.com/auth/yt-analytics.readonly'
    ]
    
    def __init__(self):
        self.youtube = None
        self.youtube_analytics = None
        self.credentials = None
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
            
            creds_file = self.accounts.get(account_name)
            if not creds_file:
                print(f"[ERROR] Account '{account_name}' not found")
                print(f"Available accounts: {', '.join(self.accounts.keys()) or 'None'}")
                return False
            
            # Load credentials
            creds = Credentials.from_authorized_user_file(str(creds_file), self.SCOPES)
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.credentials = creds
            self.youtube = build('youtube', 'v3', credentials=creds)
            
            # Try to build analytics API (may not have permissions)
            try:
                self.youtube_analytics = build('youtubeAnalytics', 'v2', credentials=creds)
            except Exception:
                print("[WARN] YouTube Analytics API not available. Limited metrics.")
            
            print(f"[OK] Authenticated as: {account_name}")
            return True
            
        except ImportError:
            print("[ERROR] Google API libraries not installed.")
            print("Run: pip install google-auth-oauthlib google-api-python-client")
            return False
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False
    
    def setup_analytics_account(self, account_name: str, client_secrets_file: str) -> bool:
        """Set up account with analytics read permissions"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, 
                self.SCOPES
            )
            credentials = flow.run_local_server(port=8080)
            
            # Save credentials
            creds_dir = Path(__file__).parent / ".youtube_creds"
            creds_dir.mkdir(exist_ok=True)
            
            creds_file = creds_dir / f"{account_name}.json"
            creds_file.write_text(credentials.to_json())
            
            self.accounts[account_name] = creds_file
            print(f"[OK] Account '{account_name}' saved with analytics permissions")
            return True
            
        except Exception as e:
            print(f"[ERROR] Setup failed: {e}")
            return False
    
    def get_channel_stats(self, channel_id: str = None) -> Optional[ChannelStats]:
        """Get channel statistics"""
        if not self.youtube:
            print("[ERROR] Not authenticated")
            return None
        
        try:
            if channel_id:
                # Get specific channel
                request = self.youtube.channels().list(
                    part="snippet,statistics",
                    id=channel_id
                )
            else:
                # Get authenticated user's channel
                request = self.youtube.channels().list(
                    part="snippet,statistics",
                    mine=True
                )
            
            response = request.execute()
            
            if not response.get('items'):
                print("[ERROR] No channel found")
                return None
            
            channel = response['items'][0]
            snippet = channel.get('snippet', {})
            stats = channel.get('statistics', {})
            
            return ChannelStats(
                channel_id=channel['id'],
                channel_name=snippet.get('title', 'Unknown'),
                subscriber_count=int(stats.get('subscriberCount', 0)),
                view_count=int(stats.get('viewCount', 0)),
                video_count=int(stats.get('videoCount', 0)),
                created_at=snippet.get('publishedAt'),
                description=snippet.get('description', ''),
                custom_url=snippet.get('customUrl')
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to get channel stats: {e}")
            return None
    
    def get_recent_videos(self, channel_id: str = None, max_results: int = 50) -> List[VideoStats]:
        """Get recent videos from channel"""
        if not self.youtube:
            print("[ERROR] Not authenticated")
            return []
        
        try:
            # First get the uploads playlist
            if channel_id:
                channel_request = self.youtube.channels().list(
                    part="contentDetails",
                    id=channel_id
                )
            else:
                channel_request = self.youtube.channels().list(
                    part="contentDetails",
                    mine=True
                )
            
            channel_response = channel_request.execute()
            
            if not channel_response.get('items'):
                return []
            
            uploads_playlist = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist
            videos_request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist,
                maxResults=max_results
            )
            
            videos_response = videos_request.execute()
            video_ids = [item['contentDetails']['videoId'] for item in videos_response.get('items', [])]
            
            if not video_ids:
                return []
            
            # Get detailed video statistics
            stats_request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=','.join(video_ids)
            )
            
            stats_response = stats_request.execute()
            
            videos = []
            for item in stats_response.get('items', []):
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                content = item.get('contentDetails', {})
                
                # Determine if it's a Short (< 60 seconds vertical video)
                duration = content.get('duration', 'PT0S')
                is_short = self._is_short(duration)
                
                videos.append(VideoStats(
                    video_id=item['id'],
                    title=snippet.get('title', ''),
                    views=int(stats.get('viewCount', 0)),
                    likes=int(stats.get('likeCount', 0)),
                    comments=int(stats.get('commentCount', 0)),
                    published_at=snippet.get('publishedAt', ''),
                    duration=duration,
                    is_short=is_short
                ))
            
            return videos
            
        except Exception as e:
            print(f"[ERROR] Failed to get videos: {e}")
            return []
    
    def _is_short(self, duration: str) -> bool:
        """Check if video duration indicates a Short (< 60 seconds)"""
        import re
        # Parse ISO 8601 duration (PT1M30S = 1 min 30 sec)
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return False
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds <= 60
    
    def evaluate_channel(self, channel_id: str = None, detailed: bool = False) -> Dict:
        """Comprehensive channel evaluation"""
        print("\n" + "=" * 60)
        print("  YOUTUBE CHANNEL EVALUATION")
        print("=" * 60)
        
        # Get channel stats
        stats = self.get_channel_stats(channel_id)
        if not stats:
            return {"error": "Could not fetch channel statistics"}
        
        # Get recent videos
        videos = self.get_recent_videos(channel_id)
        
        # Analysis
        evaluation = {
            "channel": {
                "id": stats.channel_id,
                "name": stats.channel_name,
                "url": f"https://youtube.com/channel/{stats.channel_id}",
                "custom_url": stats.custom_url,
                "created_at": stats.created_at,
            },
            "metrics": {
                "subscribers": stats.subscriber_count,
                "total_views": stats.view_count,
                "video_count": stats.video_count,
            },
            "performance": {},
            "issues": [],
            "recommendations": []
        }
        
        # Print basic info
        print(f"\n📺 Channel: {stats.channel_name}")
        print(f"   ID: {stats.channel_id}")
        if stats.custom_url:
            print(f"   URL: https://youtube.com/{stats.custom_url}")
        if stats.created_at:
            print(f"   Created: {stats.created_at[:10]}")
        
        print(f"\n📊 METRICS:")
        print(f"   Subscribers: {stats.subscriber_count:,}")
        print(f"   Total Views: {stats.view_count:,}")
        print(f"   Videos: {stats.video_count}")
        
        # Analyze subscriber status
        if stats.subscriber_count == 0:
            evaluation["issues"].append("No subscribers")
            evaluation["recommendations"].append("Focus on creating consistent, valuable content")
            evaluation["recommendations"].append("Share videos on social media platforms")
            evaluation["recommendations"].append("Engage with viewers through comments")
        elif stats.subscriber_count < 100:
            evaluation["issues"].append("Very low subscriber count")
            evaluation["recommendations"].append("Create more frequent content (aim for 3-4 videos/week)")
            evaluation["recommendations"].append("Use compelling thumbnails and titles")
        
        # Analyze view count
        if stats.view_count == 0:
            evaluation["issues"].append("No views")
            evaluation["recommendations"].append("Optimize video titles with keywords")
            evaluation["recommendations"].append("Add relevant tags and descriptions")
            evaluation["recommendations"].append("Create eye-catching thumbnails")
        elif stats.video_count > 0:
            avg_views = stats.view_count / stats.video_count
            evaluation["performance"]["avg_views_per_video"] = round(avg_views, 1)
            
            if avg_views < 10:
                evaluation["issues"].append("Very low average views")
                evaluation["recommendations"].append("Research trending topics in your niche")
                evaluation["recommendations"].append("Study successful competitors")
        
        # Analyze videos
        if videos:
            shorts = [v for v in videos if v.is_short]
            long_form = [v for v in videos if not v.is_short]
            
            evaluation["performance"]["total_videos_analyzed"] = len(videos)
            evaluation["performance"]["shorts_count"] = len(shorts)
            evaluation["performance"]["long_form_count"] = len(long_form)
            
            # Shorts analysis
            if shorts:
                shorts_views = sum(v.views for v in shorts)
                shorts_avg = shorts_views / len(shorts) if shorts else 0
                evaluation["performance"]["shorts_total_views"] = shorts_views
                evaluation["performance"]["shorts_avg_views"] = round(shorts_avg, 1)
                
                # Best performing short
                best_short = max(shorts, key=lambda x: x.views)
                evaluation["performance"]["best_short"] = {
                    "title": best_short.title,
                    "views": best_short.views,
                    "url": f"https://youtube.com/shorts/{best_short.video_id}"
                }
            
            # Long-form analysis
            if long_form:
                long_views = sum(v.views for v in long_form)
                long_avg = long_views / len(long_form) if long_form else 0
                evaluation["performance"]["long_form_total_views"] = long_views
                evaluation["performance"]["long_form_avg_views"] = round(long_avg, 1)
            
            # Engagement analysis
            total_likes = sum(v.likes for v in videos)
            total_comments = sum(v.comments for v in videos)
            total_views = sum(v.views for v in videos)
            
            if total_views > 0:
                like_rate = (total_likes / total_views) * 100
                comment_rate = (total_comments / total_views) * 100
                evaluation["performance"]["like_rate"] = round(like_rate, 2)
                evaluation["performance"]["comment_rate"] = round(comment_rate, 3)
                
                if like_rate < 2:
                    evaluation["issues"].append("Low engagement rate")
                    evaluation["recommendations"].append("Ask questions in videos to encourage engagement")
                    evaluation["recommendations"].append("Create content that resonates emotionally")
            
            # Publishing frequency
            if len(videos) >= 2:
                dates = sorted([v.published_at for v in videos if v.published_at])
                if len(dates) >= 2:
                    first = datetime.fromisoformat(dates[0].replace('Z', '+00:00'))
                    last = datetime.fromisoformat(dates[-1].replace('Z', '+00:00'))
                    days_span = (last - first).days or 1
                    videos_per_week = (len(videos) / days_span) * 7
                    evaluation["performance"]["videos_per_week"] = round(videos_per_week, 2)
                    
                    if videos_per_week < 1:
                        evaluation["issues"].append("Infrequent posting")
                        evaluation["recommendations"].append("Increase posting frequency to at least 3 videos/week")
        else:
            evaluation["issues"].append("No videos found")
            evaluation["recommendations"].append("Start creating and uploading content!")
        
        # Print performance analysis
        print(f"\n📈 PERFORMANCE ANALYSIS:")
        for key, value in evaluation["performance"].items():
            if isinstance(value, dict):
                print(f"   {key.replace('_', ' ').title()}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            else:
                print(f"   {key.replace('_', ' ').title()}: {value}")
        
        # Print issues
        if evaluation["issues"]:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in evaluation["issues"]:
                print(f"   • {issue}")
        
        # Print recommendations
        if evaluation["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(evaluation["recommendations"], 1):
                print(f"   {i}. {rec}")
        
        # Growth strategy based on current state
        print(f"\n🎯 GROWTH STRATEGY:")
        if stats.subscriber_count == 0 and stats.view_count == 0:
            print("""
   For a brand new channel with no subscribers/views:
   
   1. CONTENT FOUNDATION
      • Create 10-20 videos before expecting growth
      • Focus on ONE niche/topic
      • Maintain consistent style and quality
   
   2. SHORT-FORM FOCUS
      • YouTube Shorts have higher discovery potential
      • Post 1-2 Shorts daily
      • Hook viewers in first 1-2 seconds
   
   3. SEO OPTIMIZATION
      • Research keywords with TubeBuddy or vidIQ
      • Use keywords in title, description, tags
      • Create searchable content (how-to, tutorials)
   
   4. CROSS-PROMOTION
      • Share on TikTok, Instagram Reels, Twitter
      • Join relevant communities (Reddit, Discord)
      • Collaborate with similar-sized creators
   
   5. ENGAGEMENT
      • Reply to EVERY comment
      • Create community posts
      • Ask viewers to subscribe in videos
   
   6. PATIENCE & CONSISTENCY
      • Growth takes 3-6 months minimum
      • Track progress monthly, not daily
      • Focus on improving with each video
""")
        elif stats.subscriber_count < 1000:
            print("""
   For channels under 1K subscribers:
   
   1. Keep posting consistently (3-5 times/week)
   2. Analyze which videos perform best and make more like them
   3. Optimize thumbnails - test different styles
   4. Collaborate with creators in your niche
   5. Use YouTube Shorts to boost discovery
   6. Build an email list or Discord for loyal viewers
""")
        
        # Detailed video breakdown
        if detailed and videos:
            print(f"\n📹 DETAILED VIDEO ANALYSIS:")
            print("-" * 60)
            
            # Sort by views
            sorted_videos = sorted(videos, key=lambda x: x.views, reverse=True)
            
            for i, video in enumerate(sorted_videos[:10], 1):
                video_type = "📱 Short" if video.is_short else "🎬 Video"
                print(f"\n   {i}. {video_type} {video.title[:50]}{'...' if len(video.title) > 50 else ''}")
                print(f"      Views: {video.views:,} | Likes: {video.likes:,} | Comments: {video.comments:,}")
                print(f"      Published: {video.published_at[:10] if video.published_at else 'Unknown'}")
                if video.views > 0:
                    engagement = ((video.likes + video.comments) / video.views) * 100
                    print(f"      Engagement Rate: {engagement:.2f}%")
        
        print("\n" + "=" * 60)
        
        return evaluation


def main():
    parser = argparse.ArgumentParser(description="YouTube Channel Evaluator")
    parser.add_argument("--account", "-a", help="YouTube account name to use")
    parser.add_argument("--channel-id", "-c", help="Specific channel ID to analyze")
    parser.add_argument("--detailed", "-d", action="store_true", help="Show detailed video analysis")
    parser.add_argument("--setup-account", nargs=2, metavar=("NAME", "CLIENT_SECRETS"),
                        help="Setup new account with analytics permissions")
    parser.add_argument("--list-accounts", "-l", action="store_true", help="List available accounts")
    parser.add_argument("--output", "-o", help="Save evaluation to JSON file")
    
    args = parser.parse_args()
    
    evaluator = YouTubeChannelEvaluator()
    
    if args.list_accounts:
        accounts = evaluator.list_accounts()
        if accounts:
            print("Available accounts:")
            for acc in accounts:
                print(f"  - {acc}")
        else:
            print("No accounts configured.")
            print("Use --setup-account to add one.")
        return
    
    if args.setup_account:
        name, secrets = args.setup_account
        evaluator.setup_analytics_account(name, secrets)
        return
    
    if not args.account:
        print("Usage: python youtube_channel_evaluator.py --account <account_name>")
        print("\nAvailable accounts:")
        for acc in evaluator.list_accounts():
            print(f"  - {acc}")
        if not evaluator.list_accounts():
            print("  (none - use --setup-account to add one)")
        return
    
    # Authenticate
    if not evaluator.authenticate(args.account):
        return
    
    # Run evaluation
    evaluation = evaluator.evaluate_channel(
        channel_id=args.channel_id,
        detailed=args.detailed
    )
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Evaluation saved to: {args.output}")


if __name__ == "__main__":
    main()
