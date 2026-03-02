"""
Trade Genie - Reddit Source
Monitors investing and geopolitical subreddits for sentiment signals.
"""

import logging
from datetime import datetime, timedelta
from typing import List

import praw
from prawcore.exceptions import PrawcoreException

from config.settings import settings
from src.models import RawEvent

logger = logging.getLogger(__name__)


def fetch_reddit_events(lookback_hours: int = 48, limit_per_sub: int = 25) -> List[RawEvent]:
    """Fetch hot/top posts from configured subreddits."""
    if (
        not settings.REDDIT_CLIENT_ID
        or settings.REDDIT_CLIENT_ID.startswith("your_")
    ):
        logger.warning("Reddit credentials not configured, skipping.")
        return []

    try:
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
    except Exception as e:
        logger.error(f"Reddit init failed: {e}")
        return []

    events: List[RawEvent] = []
    cutoff_ts = (datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp()

    for sub_name in settings.REDDIT_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=limit_per_sub):
                if post.created_utc < cutoff_ts:
                    continue
                if post.score < 50:  # Filter noise — only popular posts
                    continue

                content = (post.selftext or "")[:2000]
                published_dt = datetime.utcfromtimestamp(post.created_utc)

                # Include top comments for added context
                top_comments = []
                try:
                    post.comments.replace_more(limit=0)
                    for comment in list(post.comments)[:5]:
                        if hasattr(comment, "body") and len(comment.body) > 20:
                            top_comments.append(comment.body[:300])
                except Exception:
                    pass

                full_content = content
                if top_comments:
                    full_content += "\n\nTop community reactions:\n" + "\n".join(
                        f"- {c}" for c in top_comments
                    )

                events.append(
                    RawEvent(
                        source="reddit",
                        source_name=f"r/{sub_name}",
                        title=post.title,
                        content=full_content.strip(),
                        url=f"https://reddit.com{post.permalink}",
                        published_at=published_dt,
                        tags=[sub_name],
                        raw={
                            "score": post.score,
                            "upvote_ratio": post.upvote_ratio,
                            "num_comments": post.num_comments,
                            "subreddit": sub_name,
                        },
                    )
                )
        except PrawcoreException as e:
            logger.error(f"Reddit error for r/{sub_name}: {e}")

    logger.info(f"Reddit: fetched {len(events)} posts")
    return events
