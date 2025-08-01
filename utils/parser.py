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
