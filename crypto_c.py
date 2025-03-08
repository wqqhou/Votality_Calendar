import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime
import db  # Your module with get_zscore function

# Dark mode colors
DARK_BG = "#121212"  # Deep gray background
LIGHT_TEXT = "#E0E0E0"  # Off-white text for contrast
BTN_COLOR = "#4A90E2"  # Light Blue (Ensures white font is readable)
BTN_HOVER = "#357ABD"  # Slightly darker blue for hover effect
BORDER_COLOR = "#222222"  # Slightly lighter border for elements

# Volatility Color Mapping (Original Score System Restored)
color_map = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
    "negative": "blue",
    "default": DARK_BG  # Make default background dark instead of white
}

# Font Settings
FONT_NORMAL = ("Arial", 11)
FONT_BOLD = ("Arial", 11, "bold")

class VolatilityCalendarApp(tk.Tk):
    def get_volatility_color(self, total_score):
        """ Returns a color based on the **SUMMED** score, following original logic """
        if total_score < 0:
            return color_map["negative"]
        elif total_score < 0.5:
            return color_map["default"]
        elif total_score < 1:
            return color_map["low"]
        elif total_score < 1.5:
            return color_map["medium"]
        elif total_score >= 1.5:
            return color_map["high"]
    def __init__(self):
        super().__init__()
        self.title("2025 Volatility Calendar")
        self.geometry("750x500")
        self.configure(bg=DARK_BG)

        # Store events as a list of dictionaries
        self.events = []

        self.year = 2025
        self.current_month = 1  # Start in January

        # Tkinter Style for Buttons
        style = ttk.Style()
        style.configure("TButton",
                        background=BTN_COLOR, foreground=BTN_COLOR,
                        font=("Arial", 11, "bold"), borderwidth=1,
                        focuscolor="none")
        style.map("TButton",
                  background=[("active", BTN_HOVER)],
                  foreground=[("active", BTN_HOVER)])

        # Layout: Sidebar, Main Frame, Input Frame
        self.sidebar_frame = tk.Frame(self, width=180, bg=BORDER_COLOR)
        self.sidebar_frame.pack(side="left", fill="y")

        self.main_frame = tk.Frame(self, bg=DARK_BG)
        self.main_frame.pack(side="top", fill="both", expand=True)

        self.input_frame = tk.Frame(self, height=120, bg=BORDER_COLOR)
        self.input_frame.pack(side="bottom", fill="x")

        # Sidebar Title
        tk.Label(self.sidebar_frame, text="2025 Volatility Calendar",
                 bg=BORDER_COLOR, fg=LIGHT_TEXT, font=("Arial", 12, "bold")).pack(pady=15)

        # Sidebar Month Buttons
        for m in range(1, 13):
            btn = ttk.Button(self.sidebar_frame, text=calendar.month_name[m], style="TButton",
                             command=lambda m=m: self.update_calendar(m))
            btn.pack(fill="x", pady=2, padx=8)

        # Input Fields
        tk.Label(self.input_frame, text="Event Date (DDMMYY):", bg=BORDER_COLOR, fg=LIGHT_TEXT, font=FONT_BOLD).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.event_date_entry = tk.Entry(self.input_frame, width=40, bg=DARK_BG, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT)
        self.event_date_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.input_frame, text="Event Description:", bg=BORDER_COLOR, fg=LIGHT_TEXT, font=FONT_BOLD).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.event_desc_entry = tk.Entry(self.input_frame, width=40, bg=DARK_BG, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT)
        self.event_desc_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.input_frame, text="Z-Score Dates (comma separated):", bg=BORDER_COLOR, fg=LIGHT_TEXT, font=FONT_BOLD).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.zscore_dates_entry = tk.Entry(self.input_frame, width=40, bg=DARK_BG, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT)
        self.zscore_dates_entry.grid(row=2, column=1, padx=5, pady=5)

        # Add Event Button
        self.add_event_button = ttk.Button(self.input_frame, text="Add Event", style="TButton",
                                           command=self.add_event)
        self.add_event_button.grid(row=3, column=1, padx=5, pady=5, sticky="e")

        self.update_calendar(self.current_month)

    def update_calendar(self, month):
        self.current_month = month
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # **Event Details Section (Restored)**
        event_details_frame = tk.Frame(self.main_frame, bg=DARK_BG)
        event_details_frame.pack(fill="x", padx=10, pady=10)

        events_in_month = [e for e in self.events if e["date"].month == self.current_month and e["date"].year == self.year]

        if events_in_month:
            tk.Label(event_details_frame, text=f"Events for {calendar.month_name[self.current_month]}",
                     font=FONT_BOLD, bg=DARK_BG, fg=LIGHT_TEXT).pack(anchor="w")
            for ev in events_in_month:
                ev_date_str = ev["date"].strftime("%d/%m/%Y")
                event_text = f"{ev_date_str}: {ev['description']} (Score: {ev['score']})"
                fg_color = self.get_volatility_color(float((ev['score'])))
                if fg_color != "#121212":
                    tk.Label(event_details_frame, text=event_text, fg=fg_color, bg=DARK_BG).pack(anchor="w")
                else:
                    tk.Label(event_details_frame, text=event_text, fg='white', bg=DARK_BG).pack(anchor="w")

        # **Calendar Grid**
        calendar_frame = tk.Frame(self.main_frame, bg=DARK_BG)
        calendar_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col, day in enumerate(header):
            tk.Label(calendar_frame, text=day, font=FONT_BOLD, fg=LIGHT_TEXT, bg=DARK_BG).grid(row=0, column=col, padx=4, pady=4)

        cal = calendar.monthcalendar(self.year, month)

        # Sum total score for each date
        total_scores = {}
        for event in self.events:
            event_date = event["date"]
            if event_date.month == self.current_month and event_date.year == self.year:
                total_scores[event_date.day] = total_scores.get(event_date.day, 0) + event["score"]

        for row_index, week in enumerate(cal, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue  # Empty days

                # Use summed score to determine color
                total_score = total_scores.get(day, 0)
                bg_color = self.get_volatility_color(total_score)

                lbl = tk.Label(calendar_frame, text=str(day), font=FONT_NORMAL, 
                               fg=LIGHT_TEXT, bg=bg_color, width=5, height=2, relief="flat")
                lbl.grid(row=row_index, column=col, padx=4, pady=4)



    def add_event(self):
        date_str = self.event_date_entry.get().strip()
        desc = self.event_desc_entry.get().strip()
        zscore_dates_str = self.zscore_dates_entry.get().strip()

        if not date_str or not desc or not zscore_dates_str:
            return

        event_dt = datetime.strptime(date_str.zfill(6), "%d%m%y")
        zscore_dates = [str(d.strip()) for d in zscore_dates_str.split(",") if d.strip()]
        score = db.get_zscore(zscore_dates)

        self.events.append({"date": event_dt, "description": desc, "score": score})

        # ✅ **Force Calendar to Refresh Immediately**
        self.update_calendar(self.current_month)

if __name__ == "__main__":
    app = VolatilityCalendarApp()
    app.mainloop()
