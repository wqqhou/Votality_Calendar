import calendar
from colorama import Fore, Style, init
import db
from datetime import datetime
from statistics import mean 
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
    elif total_volatility < 1:
        return color_map["green"]
    elif total_volatility < 2:
        return color_map["yellow"]
    elif total_volatility >= 2:
        return color_map["red"]

def parse_event_date(date_input):
    """
    Parse a date string that is either 5 or 6 digits long.
    - 5 digits: day is 1 digit, month is next two digits, year is last two digits.
      Example: "30325" -> "030325" meaning 03/03/25 (March 3, 2025)
    - 6 digits: assumed to be in DDMMYY format.
    Returns a datetime object.
    """
    date_input = date_input.strip()
    if len(date_input) == 5:
        # Extract parts assuming day is one digit, then month (2 digits), year (2 digits)
        day = date_input[0]      # e.g. "3"
        month = date_input[1:3]  # e.g. "03"
        year = date_input[3:]    # e.g. "25"
        formatted_date = f"0{day}{month}{year}"  # becomes "030325"
        return datetime.strptime(formatted_date, "%d%m%y")
    elif len(date_input) == 6:
        return datetime.strptime(date_input, "%d%m%y")
    else:
        raise ValueError("Date input must be either 5 or 6 digits in DDMMYY format.")


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
    print("Mo  Tu  We  Th  Fr  Sa  Su")
    
    # Print each week of the calendar
    for week in month_matrix:
        week_str = ""
        for day in week:
            if day == 0:
                week_str += "    "  # Blank space for days outside the month.
            else:
                if day in events:
                    total_volatility = mean(score for _, _, score in events[day])
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
            event_desc, event_color, volatility_score = event
            print(f"  {event_color}{event_desc} (Volatility Score: {volatility_score}){Style.RESET_ALL}")

def input_events():
    """
    Prompt the user to input event details.
    Each event is defined by:
      - A date (in DDMMYY format) on which the event occurs.
      - An event description.
      - A list of dates (as integers) that will be used to compute the average z-score.
      - The volatility collar (color) is determined automatically by get_volatility_color.
    
    Returns:
        events (dict): Dictionary mapping event days (as integers) to a list of event tuples.
                        Each tuple is (description, collar, score).
    """
    events = {}
    
    while True:
        date_input = input("Enter event date (in DDMMYY format) or type 'done' to finish: ").strip()
        if date_input.lower() == 'done':
            break
        try:
            event_dt = parse_event_date(date_input)
            calendar_day = event_dt.day  # This is now correctly parsed
        except Exception as e:
            print("Error parsing date:", e)
            continue
        
        description = input("Enter event description: ").strip()
        
        dates_str = input("Enter a list of dates for z-score calculation, separated by commas (e.g., 180924,71124,181224,10225): ").strip()
        try:
            date_list = [int(d.strip()) for d in dates_str.split(',') if d.strip()]
        except ValueError:
            print("Error in parsing the list of dates. Please try again.")
            continue
        
        # Compute the average z-score for the given list of dates using db.get_zscore
        score = db.get_zscore(date_list)
        
        # Determine the volatility collar using the computed score.
        collar = get_volatility_color(score)
        
        # Use the calendar day as key (ensuring it matches the calendar printed later)
        if calendar_day not in events:
            events[calendar_day] = []
        events[calendar_day].append((description, collar, score))
        
        print(f"Added event for day {calendar_day}: {description} with score of {score} and collar {collar}\n")
    
    return events

# Example usage:
events = input_events()

# Example usage:
year = 2025
month = 3
# Each event: (event_description, event_comment_color, volatility_score)

 # Example date in DDMMYY format
print_crypto_volatility_calendar(year, month, events)

