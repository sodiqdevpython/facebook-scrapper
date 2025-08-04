from datetime import datetime, timedelta
import re
from dateutil import parser


def parse_count_to_int(count_str: str) -> int:
    if not count_str:
        return 0

    count_str = count_str.strip().upper().replace(",", "").replace(" ", "")

    multipliers = {
        'K': 1000,
        'M': 1000000,
        'B': 1000000000,
        'T': 1000000000000,
    }

    if count_str[-1] in multipliers:
        try:
            number = float(count_str[:-1])
            return int(number * multipliers[count_str[-1]])
        except ValueError:
            return 0
    else:
        try:
            return int(float(count_str))
        except ValueError:
            return 0

def parse_facebook_date(fb_date_str: str):
    now = datetime.now()
    fb_date_str = fb_date_str.strip().lower()
    match = re.match(r"(\d+)(y|mo|w|d|h|m)", fb_date_str)
    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if unit == 'y':
            return now - timedelta(days=365 * num)
        elif unit == 'mo':
            return now - timedelta(days=30 * num)
        elif unit == 'w':
            return now - timedelta(weeks=num)
        elif unit == 'd':
            return now - timedelta(days=num)
        elif unit == 'h':
            return now - timedelta(hours=num)
        elif unit == 'm':
            return now - timedelta(minutes=num)
    if fb_date_str.startswith("yesterday at"):
        try:
            time_str = fb_date_str.split("at")[-1].strip()
            parsed_time = datetime.strptime(time_str, "%I:%M %p").time()
            yesterday = now - timedelta(days=1)
            return datetime.combine(yesterday.date(), parsed_time)
        except Exception:
            pass
    try:
        return parser.parse(fb_date_str)
    except Exception:
        pass

    return fb_date_str