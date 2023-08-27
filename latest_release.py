import sys

from src.mpyl.cli.meta_info import get_latest_release

latest = get_latest_release()
requested = sys.argv[1]
matching = requested != latest
match_text = "does not match" if matching else "matches"
print(
    f"Latest release: {latest}, {match_text} {requested}. Did you follow the release instructions?"
)
sys.exit(0 if matching else 1)
