import json
import os
import re
from collections import Counter

import click
import praw
from praw.models import Comment, Submission

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDDIT_USERNAME = os.environ["REDDIT_USERNAME"]
REDDIT_PASSWORD = os.environ["REDDIT_PASSWORD"]

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=f"comment scrapper by /u/{REDDIT_USERNAME}",
)


@click.command()
@click.argument("url", type=str)
@click.option("--only-top-level", type=bool, default=False, is_flag=True)
@click.option("--weigh-comments", type=bool, default=False, is_flag=True)
@click.option("--max-candidate", default=25)
def cli(url: str, only_top_level: bool, weigh_comments: bool, max_candidate: int):
    if url.startswith("https://www.reddit.com/r"):
        submission: Submission = reddit.submission(url=url)
    else:
        submission: Submission = reddit.submission(url)

    replace_comment_limit = 0 if only_top_level else None
    submission.comments.replace_more(limit=replace_comment_limit)

    total_votes = Counter()
    previous_voters: set[str] = set()

    manifest: list[dict] = []

    comment: Comment
    for comment in submission.comments.list():
        if (
            (comment.author is None)
            or (comment.author.name in previous_voters)
            or (isinstance(comment.parent(), Comment) and only_top_level)
        ):
            continue

        candidates: set[int] = {
            int(s)
            for s in re.findall(r"\b\d+\b", comment.body)
            if int(s) < max_candidate  # filter out reddit emojis
        }
        vote_weight = comment.score if weigh_comments else 1
        total_votes += Counter({candidate: vote_weight for candidate in candidates})
        previous_voters.add(comment.author.name)

        for candidate in candidates:
            manifest.append(
                {
                    "author": comment.author.name,
                    "body": comment.body,
                    "candidate": candidate,
                    "score": comment.score,
                }
            )

    for candidate, votes in sorted(
        total_votes.items(), key=lambda n: n[1], reverse=True
    ):
        print(f"{candidate}:\t{votes}")

    with open("votes.json", "w") as output:
        json.dump(manifest, output, indent=2)


if __name__ == "__main__":
    cli()
