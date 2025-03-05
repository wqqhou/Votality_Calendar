import calendar
from colorama import Fore, Style, init

# Initialize colorama so that ANSI colors work on all platforms.
init(autoreset=True)

# Define a mapping for some colors.
color_map = {
    "red": Fore.RED,
    "green": Fore.GREEN,
    "blue": Fore.BLUE,
    "yellow": Fore.YELLOW,
    "magenta": Fore.MAGENTA,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE
}

def get_volatility_color(total_volatility):
    """
    Determine the color for the date based on the aggregated volatility score.
    
    For example:
      - Negative total score (events predict lower-than-baseline volatility): blue
      - Zero: white (neutral)
      - Low positive total score: green (mild volatility)
      - Moderate positive total score: yellow (increased volatility)
      - High positive total score: red (high volatility)
      
    Adjust thresholds as needed.
    """
    if total_volatility < 0:
        return color_map["blue"]
    elif total_volatility == 0:
        return color_map["white"]
    elif total_volatility < 5:
        return color_map["green"]
    elif total_volatility < 10:
        return color_map["yellow"]
    else:
        return color_map["red"]

def print_crypto_volatility_calendar(year, month, events):
    """
    Print a calendar for the specified year and month where each day is colored based on the
    aggregated volatility score from events. The events dictionary keys are day numbers.
    Each value is a list of event tuples of the form:
         (event_description, event_comment_color, volatility_score)
    """
    # Generate the calendar matrix: each week is a list of day numbers (0 for days not in the month)
    month_matrix = calendar.monthcalendar(year, month)
    
    # Print header
    print("Mo Tu We Th Fr Sa Su")
    
    # Print each week of the calendar
    for week in month_matrix:
        week_str = ""
        for day in week:
            if day == 0:
                week_str += "    "  # Blank space for days outside the month.
            else:
                if day in events:
                    total_volatility = sum(score for _, _, score in events[day])
                    day_color = get_volatility_color(total_volatility)
                    day_str = f"{day_color}{day:2d}{Style.RESET_ALL}"
                else:
                    day_str = f"{day:2d}"
                week_str += day_str + "  "
        print(week_str)
    
    # List out event details for each day
    print("\nEvent Details:")
    for day in sorted(events.keys()):
        print(f"Day {day:2d}:")
        for event in events[day]:
            event_desc, event_comment_color, volatility_score = event
            event_color = color_map.get(event_comment_color.lower(), "")
            print(f"  {event_color}{event_desc} (Volatility Score: {volatility_score}){Style.RESET_ALL}")

# Example usage:
year = 2025
month = 3
# Each event: (event_description, event_comment_color, volatility_score)
events = {
    3: [("Regulatory news", "magenta", 4)],
    10: [("Major hack report", "red", 8)],
    15: [("New blockchain launch", "cyan", 6)],
    27: [("Institutional investment", "green", -2), ("Tech conference", "yellow", 3)]
}

print_crypto_volatility_calendar(year, month, events)
