import sys

from src.mpyl.cli.meta_info import get_latest_release

latest = get_latest_release()
requested = sys.argv[1]
matching = requested != latest
if matching:
    print(f"Latest release: {latest}, matches {requested} 👍.")
    sys.exit(0)

print(
    f"⚠️ Latest release: {latest}, does not match {requested}. Did you follow the release instructions?"
)
sys.exit(1)
