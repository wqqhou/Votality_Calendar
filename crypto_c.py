import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime
import db  # your module with get_zscore and any other functions
from statistics import mean

# For tkinter we use standard color names.
color_map = {
    "red": "red",
    "green": "green",
    "blue": "blue",
    "yellow": "yellow",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "black": "black"  # default
}

class VolatilityCalendarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("2025 Volatility Calendar")
        self.geometry("900x700")
        
        # Store events as a list of dictionaries.
        # Each event dictionary contains: date (datetime object), description, score, color.
        self.events = []
        
        self.year = 2025
        self.current_month = 1  # default to January
        
        # Create three frames: sidebar, main area, and bottom input area.
        self.sidebar_frame = tk.Frame(self, width=150, bg="lightgray")
        self.sidebar_frame.pack(side="left", fill="y")
        
        # Set main frame with a black background.
        self.main_frame = tk.Frame(self, bg="black")
        self.main_frame.pack(side="top", fill="both", expand=True)
        
        self.input_frame = tk.Frame(self, height=100, bg="lightblue")
        self.input_frame.pack(side="bottom", fill="x")
        
        # Sidebar: title and month buttons.
        tk.Label(self.sidebar_frame, text="2025 Volatility Calendar", bg="lightgray", font=("Helvetica", 12, "bold")).pack(pady=10)
        for m in range(1, 13):
            btn = tk.Button(self.sidebar_frame, text=calendar.month_name[m], command=lambda m=m: self.update_calendar(m))
            btn.pack(fill="x", pady=2, padx=5)
        
        # Input area: fields for event input.
        tk.Label(self.input_frame, text="Event Date (DDMMYY):", bg="lightblue").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.event_date_entry = tk.Entry(self.input_frame)
        self.event_date_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.input_frame, text="Event Description:", bg="lightblue").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.event_desc_entry = tk.Entry(self.input_frame, width=40)
        self.event_desc_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(self.input_frame, text="Z-Score Dates (comma separated):", bg="lightblue").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.zscore_dates_entry = tk.Entry(self.input_frame, width=40)
        self.zscore_dates_entry.grid(row=2, column=1, padx=5, pady=5)
        
        self.add_event_button = tk.Button(self.input_frame, text="Add Event", command=self.add_event)
        self.add_event_button.grid(row=3, column=1, padx=5, pady=5, sticky="e")
        
        # Error box to show any errors in red.
        self.error_label = tk.Label(self.input_frame, text="", bg="lightblue", fg="red")
        self.error_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        
        self.update_calendar(self.current_month)
    
    def update_calendar(self, month):
        self.current_month = month
        
        # Clear the main frame entirely.
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create an event details frame at the top of main_frame with black background.
        event_details_frame = tk.Frame(self.main_frame, bg="black")
        event_details_frame.pack(fill="x", padx=10, pady=10)
        
        # Filter events for the selected month and year.
        events_in_month = [e for e in self.events if e["date"].month == self.current_month and e["date"].year == self.year]
        
        if events_in_month:
            tk.Label(event_details_frame, text="Events for " + calendar.month_name[self.current_month], 
                     font=("Helvetica", 10, "bold"), bg="black", fg="white").pack(anchor="w")
            for ev in events_in_month:
                # Display event date, description, score and use its color.
                ev_date_str = ev["date"].strftime("%d/%m/%Y")
                event_text = f"{ev_date_str}: {ev['description']} (Score: {ev['score']})"
                tk.Label(event_details_frame, text=event_text, fg=ev["color"], bg="black").pack(anchor="w")
        else:
            tk.Label(event_details_frame, text="No events for " + calendar.month_name[self.current_month],
                     bg="black", fg="white").pack(anchor="w")
        
        # Create a calendar frame below the event details, with black background.
        calendar_frame = tk.Frame(self.main_frame, bg="black")
        calendar_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create header row (day names).
        header = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col, day in enumerate(header):
            lbl = tk.Label(calendar_frame, text=day, font=("Helvetica", 10, "bold"), borderwidth=1, relief="solid", width=4,
                           bg="black", fg="white")
            lbl.grid(row=0, column=col, padx=1, pady=1)
        
        # Build an index for events keyed by day in this month.
        events_by_day = {}
        for ev in events_in_month:
            day = ev["date"].day
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(ev)
        
        # Populate the calendar grid.
        cal = calendar.monthcalendar(self.year, month)
        for row_index, week in enumerate(cal, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(calendar_frame, text="", borderwidth=1, relief="solid", width=4,
                                   bg="black", fg="white")
                    lbl.grid(row=row_index, column=col, padx=1, pady=1)
                else:
                    if day in events_by_day:
                        total_score = sum(ev["score"] for ev in events_by_day[day])
                        day_color = self.get_volatility_color(total_score)
                    else:
                        day_color = "white"
                    
                    lbl = tk.Label(calendar_frame, text=str(day), borderwidth=1, relief="solid", width=4,
                                   bg="black", fg=day_color)
                    lbl.grid(row=row_index, column=col, padx=1, pady=1)
    
    def get_volatility_color(self, total_volatility):
        """
        Returns a color (as a string) based on the aggregated volatility score.
        Adjust thresholds as needed.
        """
        if total_volatility < 0:
            return color_map["blue"]
        elif total_volatility < 0.5:
            return color_map["white"]
        elif total_volatility < 1:
            return color_map["green"]
        elif total_volatility < 1.5:
            return color_map["yellow"]
        elif total_volatility >= 1.5:
            return color_map["red"]
    
    def add_event(self):
        # Clear any previous error message.
        self.error_label.config(text="")
        
        # Get input values.
        date_str = self.event_date_entry.get().strip()
        desc = self.event_desc_entry.get().strip()
        zscore_dates_str = self.zscore_dates_entry.get().strip()
        
        # Check if all fields are filled.
        if not date_str or not desc or not zscore_dates_str:
            self.error_label.config(text="Please fill in all fields.")
            return
        
        # Parse the event date.
        try:
            if len(date_str) == 5:
                event_dt = datetime.strptime("0" + date_str, "%d%m%y")
            elif len(date_str) == 6:
                event_dt = datetime.strptime(date_str, "%d%m%y")
            else:
                raise ValueError("Date must be 5 or 6 digits in DDMMYY format.")
        except Exception as e:
            self.error_label.config(text=f"Error parsing event date: {e}")
            return
        
        # Parse the comma-separated zscore dates.
        try:
            zscore_dates = [str(d.strip()) for d in zscore_dates_str.split(",") if d.strip()]
        except Exception as e:
            self.error_label.config(text=f"Error parsing z-score dates: {e}")
            return
        
        # Compute the average z-score using db.get_zscore (assumed implemented).
        score = db.get_zscore(zscore_dates)
        
        # Determine the event color using your volatility scoring logic.
        color = self.get_volatility_color(score)
        
        # Store the event with full date information.
        event = {
            "date": event_dt,
            "description": desc,
            "score": score,
            "color": color
        }
        self.events.append(event)
        
        print(f"Added event for {event_dt.strftime('%d/%m/%Y')}: {desc} with score {score} and color {color}")
        
        # Clear input fields.
        self.event_date_entry.delete(0, tk.END)
        self.event_desc_entry.delete(0, tk.END)
        self.zscore_dates_entry.delete(0, tk.END)
        
        # Clear any error message.
        self.error_label.config(text="")
        
        # Refresh the calendar display.
        self.update_calendar(self.current_month)

if __name__ == "__main__":
    app = VolatilityCalendarApp()
    app.mainloop()
