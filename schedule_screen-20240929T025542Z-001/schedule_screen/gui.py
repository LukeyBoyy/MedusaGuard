from pathlib import Path
import os
import subprocess
import json
from tkinter import messagebox
# from tkinter import *
# Explicit imports to satisfy Flake8
from tkinter import Tk, Canvas, Entry, Button, PhotoImage, Toplevel, StringVar, Spinbox, Listbox, Scrollbar, OptionMenu, Label, Text
from tkcalendar import Calendar
from pytz import timezone, all_timezones


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"/home/kali/Desktop/schedule_screen/assets/frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

def add_placeholder(entry, placeholder_text):
    entry.insert(0, placeholder_text)
    entry.config(fg='grey')

    def on_focus_in(event):
        if entry.get() == placeholder_text:
            entry.delete(0, "end")
            entry.config(fg='#FFFFFF')

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, placeholder_text)
            entry.config(fg='grey')

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        # Create a Toplevel window for the tooltip
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 50
        y += self.widget.winfo_rooty() + 30
        self.tooltip_window = Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.geometry(f"+{x}+{y}")
        label = Label(self.tooltip_window, text=self.text, background="#121212", foreground="white", borderwidth=1, relief="solid", highlightbackground="#313237", highlightthickness=1, padx=7, pady=7)
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# Function to open the calendar and select a date
def open_calendar():
    def get_selected_date():
        selected_date = cal.get_date()
        date_display_var.set(selected_date)
        update_summary()
        top.destroy()

    top = Toplevel(window)
    cal = Calendar(top, selectmode='day', date_pattern="dd/mm/yyyy")
    cal.pack(pady=20)
    select_btn = Button(top, text="Select", command=get_selected_date)
    select_btn.pack()


# Function that gets called when button_27 is pressed
def handle_comment_input():
    comment_text = comment_input.get()
    print(f"Comment entered: {comment_text}")
    update_summary() 


# Function to handle saving the schedule config
def save_schedule_config():
    comment_text = comment_input.get() if comment_input.get() else 'No Comment'
    interval_value = repeat_interval_display_var.get() if repeat_interval_display_var.get() else 'Not Selected'
    interval_in_days = calculate_interval_days(interval_value)
    

    schedule_data = {
        "Comment": comment_text,
        "Date": date_display_var.get() if date_display_var.get() else 'Not Selected',
        "Time": time_display_var.get() if time_display_var.get() else 'Not Selected',
        "Timezone": timezone_display_var.get() if timezone_display_var.get() else 'Not Selected',
        "Repeat Every": interval_in_days  # Save the interval as days instead of the string
    }
    
    # Save (overwrite) the data to a JSON file (schedule_config.json)
    try:
        with open("schedule_config.json", "w") as config_file:
            json.dump(schedule_data, config_file, indent=4)
       
        messagebox.showinfo("Success", "The schedule configuration has been saved.")
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save the configuration: {str(e)}")
        
def calculate_interval_days(interval_value):
    if interval_value == "Daily":
        return 1
    elif interval_value == "Weekly":
        return 7
    elif interval_value == "Fortnightly":
        return 14
    elif interval_value == "Monthly":
        return 30
    else:
        return 1;
        
# Function to open time selection
def open_time_selector():
    def update_time():
        selected_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}"
        time_display_var.set(selected_time)
        update_summary()
        top.destroy()

    top = Toplevel(window)

    # Spinbox for hours
    hour_spinbox = Spinbox(top, from_=0, to=23, width=2, format="%02.0f")
    hour_spinbox.pack(side="left", padx=5)

    # Spinbox for minutes
    minute_spinbox = Spinbox(top, from_=0, to=59, width=2, format="%02.0f")
    minute_spinbox.pack(side="left", padx=5)

    select_btn = Button(top, text="Select Time", command=update_time)
    select_btn.pack()

# Scrollable timezone selection dialog
def select_timezone():
    def on_select(event):
        selected = listbox.get(listbox.curselection())
        timezone_display_var.set(selected)
        update_summary()
        top.destroy()

    top = Toplevel(window)
    top.title("Select Timezone")

    scrollbar = Scrollbar(top)
    scrollbar.pack(side="right", fill="y")

    listbox = Listbox(top, yscrollcommand=scrollbar.set, width=50, height=20)
    for tz in all_timezones:
        listbox.insert("end", tz)

    listbox.pack(side="left", fill="both")
    scrollbar.config(command=listbox.yview)
    listbox.bind("<<ListboxSelect>>", on_select)

# Function to handle showing the Repeat Interval OptionMenu when button_21 is clicked
def show_interval_menu():
    interval_menu = OptionMenu(window, interval_var, *interval_options, command=select_repeat_interval)
    interval_menu.place(x=660.0, y=320.0, width=150.0, height=30.0)

# Function to handle Repeat Interval Selection
def select_repeat_interval(selected_option):
    repeat_interval_display_var.set(selected_option)
    update_summary()
    
    for widget in window.winfo_children():
        if isinstance(widget, OptionMenu):
            widget.destroy()

# Function to update the summary section on button_23
def update_summary():
    summary_text = (
        f"Date: {date_display_var.get() if date_display_var.get() else 'Not Selected'}, "
        f"Time: {time_display_var.get() if time_display_var.get() else 'Not Selected'}, "
        f"Timezone: {timezone_display_var.get() if timezone_display_var.get() else 'Not Selected'}, "
        f"Repeat Every: {repeat_interval_display_var.get() if repeat_interval_display_var.get() else 'Not Selected'}"
    )
    button_23.config(text=summary_text)


    
window = Tk()
window.title("MedusaGuard Scan Scheduler")

window.geometry("1000x885")
window.configure(bg = "#FFFFFF")


canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 885,
    width = 1000,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    885.0,
    fill="#121212",
    outline="")

canvas.create_rectangle(
    0.0,
    0.0,
    272.0,
    885.0,
    fill="#1B1C21",
    outline="")

canvas.create_text(
    37.0,
    194.0,
    anchor="nw",
    text="Folders",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

canvas.create_text(
    37.0,
    412.0,
    anchor="nw",
    text="Config",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

# Entry for displaying the selected date
date_display_var = StringVar()

# Entry for displaying the selected time
time_display_var = StringVar()

# Entry for displaying the selected timezone
timezone_display_var = StringVar()

# Label for displaying the selected repeat interval
repeat_interval_display_var = StringVar()

# OptionMenu for repeat interval
interval_var = StringVar()
interval_var.set("Daily")
interval_options = ["Daily", "Weekly", "Fortnightly", "Monthly"]

# Sidebar custom reports link
button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('custom_reports'),
    relief="flat"
)
button_1.place(
    x=24.0,
    y=209.0,
    width=248.0,
    height=44.0
)

button_image_hover_1 = PhotoImage(
    file=relative_to_assets("button_hover_1.png"))

def button_1_hover(e):
    button_1.config(
        image=button_image_hover_1
    )
def button_1_leave(e):
    button_1.config(
        image=button_image_1
    )

button_1.bind('<Enter>', button_1_hover)
button_1.bind('<Leave>', button_1_leave)


# Sidebar greenbone reports link
button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('greenbone_reports'),
    relief="flat"
)
button_2.place(
    x=19.0,
    y=240.0,
    width=246.0,
    height=46.0
)

button_image_hover_2 = PhotoImage(
    file=relative_to_assets("button_hover_2.png"))

def button_2_hover(e):
    button_2.config(
        image=button_image_hover_2
    )
def button_2_leave(e):
    button_2.config(
        image=button_image_2
    )

button_2.bind('<Enter>', button_2_hover)
button_2.bind('<Leave>', button_2_leave)


# Sidebar nuclei results link
button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nuclei_results'),
    relief="flat"
)
button_3.place(
    x=24.497802734375,
    y=275.791748046875,
    width=225.80621337890625,
    height=37.6944465637207
)

button_image_hover_3 = PhotoImage(
    file=relative_to_assets("button_hover_3.png"))

def button_3_hover(e):
    button_3.config(
        image=button_image_hover_3
    )
def button_3_leave(e):
    button_3.config(
        image=button_image_3
    )

button_3.bind('<Enter>', button_3_hover)
button_3.bind('<Leave>', button_3_leave)


# Sidebar metasploit results link
button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('metasploit_results'),
    relief="flat"
)
button_4.place(
    x=19.0,
    y=311.0,
    width=253.0,
    height=43.0
)

button_image_hover_4 = PhotoImage(
    file=relative_to_assets("button_hover_4.png"))

def button_4_hover(e):
    button_4.config(
        image=button_image_hover_4
    )
def button_4_leave(e):
    button_4.config(
        image=button_image_4
    )

button_4.bind('<Enter>', button_4_hover)
button_4.bind('<Leave>', button_4_leave)


# Sidebar nikto results link
button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nikto_results'),
    relief="flat"
)
button_5.place(
    x=19.0,
    y=347.0,
    width=238.0,
    height=50.0
)

button_image_hover_5 = PhotoImage(
    file=relative_to_assets("button_hover_5.png"))

def button_5_hover(e):
    button_5.config(
        image=button_image_hover_5
    )
def button_5_leave(e):
    button_5.config(
        image=button_image_5
    )

button_5.bind('<Enter>', button_5_hover)
button_5.bind('<Leave>', button_5_leave)


# Sidebar scan configuration link
button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png"))
button_6 = Button(
    image=button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('config.ini'),
    relief="flat"
)
button_6.place(
    x=32.830322265625,
    y=431.4862060546875,
    width=217.47396850585938,
    height=37.6944465637207
)

button_image_hover_6 = PhotoImage(
    file=relative_to_assets("button_hover_6.png"))

def button_6_hover(e):
    button_6.config(
        image=button_image_hover_6
    )
def button_6_leave(e):
    button_6.config(
        image=button_image_6
    )

button_6.bind('<Enter>', button_6_hover)
button_6.bind('<Leave>', button_6_leave)


# Sidebar target list link
button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png"))
button_7 = Button(
    image=button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('targets.txt'),
    relief="flat"
)
button_7.place(
    x=14.4990234375,
    y=466.72216796875,
    width=235.80499267578125,
    height=37.6944465637207
)

button_image_hover_7 = PhotoImage(
    file=relative_to_assets("button_hover_7.png"))

def button_7_hover(e):
    button_7.config(
        image=button_image_hover_7
    )
def button_7_leave(e):
    button_7.config(
        image=button_image_7
    )

button_7.bind('<Enter>', button_7_hover)
button_7.bind('<Leave>', button_7_leave)

# Sidebar documentation link
button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png"))
button_8 = Button(
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_8 clicked"),
    relief="flat"
)
button_8.place(
    x=24.0,
    y=129.0,
    width=248.0,
    height=44.0
)

button_image_hover_8 = PhotoImage(
    file=relative_to_assets("button_hover_8.png"))

def button_8_hover(e):
    button_8.config(
        image=button_image_hover_8
    )
def button_8_leave(e):
    button_8.config(
        image=button_image_8
    )

button_8.bind('<Enter>', button_8_hover)
button_8.bind('<Leave>', button_8_leave)

# sidebar tips feed link
button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png"))
button_9 = Button(
    image=button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_9 clicked"),
    relief="flat"
)
button_9.place(
    x=24.0,
    y=663.0,
    width=216.0,
    height=192.0
)

canvas.create_text(
    37.0,
    78.0,
    anchor="nw",
    text="Navigation",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

canvas.create_text(
    12.0,
    855.0,
    anchor="nw",
    text="© 2024 MedusaGuard. All Rights Reserved",
    fill="#FFFFFF",
    font=("Inter", 11 * -1)
)

canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    41.0,
    fill="#6A1B9A",
    outline="")

canvas.create_text(
    75.0,
    11.0,
    anchor="nw",
    text="Scan Scheduler",
    fill="#FFFFFF",
    font=("Inter Bold", 18 * -1)
)

# top right documentation link
button_image_10 = PhotoImage(
    file=relative_to_assets("button_10.png"))
button_10 = Button(
    image=button_image_10,
    borderwidth=0,
    highlightthickness=0,
    #command=lambda: print("button_10 clicked"),
    relief="flat"
)
button_10.place(
    x=902.0,
    y=0.0,
    width=76.0,
    height=41.0
)

button_image_hover_10 = PhotoImage(
    file=relative_to_assets("button_hover_9.png"))

def button_10_hover(e):
    button_10.config(
        image=button_image_hover_10
    )
def button_10_leave(e):
    button_10.config(
        image=button_image_10
    )

button_10.bind('<Enter>', button_10_hover)
button_10.bind('<Leave>', button_10_leave)


button_image_11 = PhotoImage(
    file=relative_to_assets("button_11.png"))
button_11 = Button(
    image=button_image_11,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_11.place(
    x=24.0,
    y=0.0,
    width=50.0,
    height=41.0
)

button_image_hover_11 = PhotoImage(
    file=relative_to_assets("button_hover_10.png"))

def button_11_hover(e):
    button_11.config(
        image=button_image_hover_11
    )
def button_11_leave(e):
    button_11.config(
        image=button_image_11
    )

button_11.bind('<Enter>', button_11_hover)
button_11.bind('<Leave>', button_11_leave)

# Sidebar dashboard link
button_image_12 = PhotoImage(
    file=relative_to_assets("button_12.png"))
button_12 = Button(
    image=button_image_12,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_12 clicked"),
    relief="flat"
)
button_12.place(
    x=24.0,
    y=98.0,
    width=248.0,
    height=39.0
)

button_image_hover_12 = PhotoImage(
    file=relative_to_assets("button_hover_11.png"))

def button_12_hover(e):
    button_12.config(
        image=button_image_hover_12
    )
def button_12_leave(e):
    button_12.config(
        image=button_image_12
    )

button_12.bind('<Enter>', button_12_hover)
button_12.bind('<Leave>', button_12_leave)

# Cancel button
button_image_13 = PhotoImage(
    file=relative_to_assets("button_13.png"))
button_13 = Button(
    image=button_image_13,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_13 clicked"),
    relief="flat"
)
button_13.place(
    x=415.0,
    y=450,
    width=118.0,
    height=73.0
)

button_image_hover_13 = PhotoImage(
    file=relative_to_assets("button_hover_12.png"))

def button_13_hover(e):
    button_13.config(
        image=button_image_hover_13
    )
def button_13_leave(e):
    button_13.config(
        image=button_image_13
    )

button_13.bind('<Enter>', button_13_hover)
button_13.bind('<Leave>', button_13_leave)

# Save Button
button_image_14 = PhotoImage(
    file=relative_to_assets("button_14.png"))
button_14 = Button(
    image=button_image_14,
    borderwidth=0,
    highlightthickness=0,
    command=save_schedule_config,
    relief="flat"
)
button_14.place(
    x=296.0,
    y=450,
    width=123.0,
    height=73.0
)

button_image_hover_14 = PhotoImage(
    file=relative_to_assets("button_hover_13.png"))

def button_14_hover(e):
    button_14.config(
        image=button_image_hover_14
    )
def button_14_leave(e):
    button_14.config(
        image=button_image_14
    )

button_14.bind('<Enter>', button_14_hover)
button_14.bind('<Leave>', button_14_leave)


button_image_15 = PhotoImage(
    file=relative_to_assets("button_15.png"))
button_15 = Button(
    image=button_image_15,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_15.place(
    x=299.0,
    y=46.0,
    width=682.0,
    height=399.0
)

# Select date button
button_image_16 = PhotoImage(
    file=relative_to_assets("button_16.png"))
button_16 = Button(
    image=button_image_16,
    borderwidth=0,
    highlightthickness=0,
    command=open_calendar,
    relief="flat"
)
button_16.place(
    x=542.0,
    y=166.0,
    width=149.0,
    height=69.0
)

button_image_hover_16 = PhotoImage(
    file=relative_to_assets("button_hover_14.png"))

def button_16_hover(e):
    button_16.config(
        image=button_image_hover_16
    )
def button_16_leave(e):
    button_16.config(
        image=button_image_16
    )

button_16.bind('<Enter>', button_16_hover)
button_16.bind('<Leave>', button_16_leave)

# Select time button
button_image_17 = PhotoImage(
    file=relative_to_assets("button_17.png"))
button_17 = Button(
    image=button_image_17,
    borderwidth=0,
    highlightthickness=0,
    command=open_time_selector,
    relief="flat"
)
button_17.place(
    x=691.0,
    y=167.0,
    width=141.0,
    height=69.0
)

button_image_hover_17 = PhotoImage(
    file=relative_to_assets("button_hover_15.png"))

def button_17_hover(e):
    button_17.config(
        image=button_image_hover_17
    )
def button_17_leave(e):
    button_17.config(
        image=button_image_17
    )

button_17.bind('<Enter>', button_17_hover)
button_17.bind('<Leave>', button_17_leave)


button_image_18 = PhotoImage(
    file=relative_to_assets("button_18.png"))
button_18 = Button(
    image=button_image_18,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_18 clicked"),
    relief="flat"
)
button_18.place(
    x=316.0,
    y=165.0,
    width=116.0,
    height=75.0
)

# Select timezone button
button_image_19 = PhotoImage(
    file=relative_to_assets("button_19.png"))
button_19 = Button(
    image=button_image_19,
    borderwidth=0,
    highlightthickness=0,
    command=select_timezone,
    relief="flat"
)
button_19.place(
    x=538.0,
    y=235.0,
    width=191.0,
    height=71.0
)

button_image_hover_19 = PhotoImage(
    file=relative_to_assets("button_hover_16.png"))

def button_19_hover(e):
    button_19.config(
        image=button_image_hover_19
    )
def button_19_leave(e):
    button_19.config(
        image=button_image_19
    )

button_19.bind('<Enter>', button_19_hover)
button_19.bind('<Leave>', button_19_leave)


button_image_20 = PhotoImage(
    file=relative_to_assets("button_20.png"))
button_20 = Button(
    image=button_image_20,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_20 clicked"),
    relief="flat"
)
button_20.place(
    x=325.0,
    y=235.0,
    width=113.0,
    height=71.0
)

# Repeat every select button
button_image_21 = PhotoImage(
    file=relative_to_assets("button_21.png"))
button_21 = Button(
    image=button_image_21,
    borderwidth=0,
    highlightthickness=0,
    command=show_interval_menu,
    relief="flat"
)
button_21.place(
    x=542.0,
    y=296.0,
    width=105.0,
    height=76.0
)

button_image_hover_21 = PhotoImage(
    file=relative_to_assets("button_hover_17.png"))

def button_21_hover(e):
    button_21.config(
        image=button_image_hover_21
    )
def button_21_leave(e):
    button_21.config(
        image=button_image_21
    )

button_21.bind('<Enter>', button_21_hover)
button_21.bind('<Leave>', button_21_leave)


button_image_22 = PhotoImage(
    file=relative_to_assets("button_22.png"))
button_22 = Button(
    image=button_image_22,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_22 clicked"),
    relief="flat"
)
button_22.place(
    x=316.0,
    y=295.0,
    width=166.0,
    height=76.0
)

# Summary section
button_image_23 = PhotoImage(
    file=relative_to_assets("button_23.png"))
    
button_23 = Button(window, 
                   text="Date: , Time: , Timezone: , Repeat Every:", 
                   borderwidth=2, 
                   highlightthickness=2, 
                   relief="ridge", 
                   anchor="w", 
                   bg="#1E1E1E", 
                   fg="#FFFFFF", 
                   font=("Helvetica", 10),
                   justify="left", 
                   padx=10, 
                   pady=10,
                   wraplength=580
                  )
button_23.place(
    x=316.0,
    y=371.0,
    width=631.0,
    height=55.0
)

button_image_24 = PhotoImage(
    file=relative_to_assets("button_24.png"))
button_24 = Button(
    image=button_image_24,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_24 clicked"),
    relief="flat"
)
button_24.place(
    x=425.0,
    y=328.0,
    width=13.0,
    height=13.0
)

button_image_hover_24 = PhotoImage(
    file=relative_to_assets("button_hover_18.png"))

def button_24_hover(e):
    button_24.config(
        image=button_image_hover_24
    )
def button_24_leave(e):
    button_24.config(
        image=button_image_24
    )

# Apply Tooltip to button_24
tooltip = ToolTip(button_24, """Required section, enables you to have this scheduled scan run
repeatedly, rather than only once""")
button_24.bind("<Enter>", tooltip.show_tooltip)
button_24.bind("<Leave>", tooltip.hide_tooltip)



button_image_25 = PhotoImage(
    file=relative_to_assets("button_25.png"))
button_25 = Button(
    image=button_image_25,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_25 clicked"),
    relief="flat"
)
button_25.place(
    x=402.0,
    y=261.0,
    width=13.0,
    height=13.0
)

button_image_hover_25 = PhotoImage(
    file=relative_to_assets("button_hover_19.png"))

def button_25_hover(e):
    button_25.config(
        image=button_image_hover_25
    )
def button_25_leave(e):
    button_25.config(
        image=button_image_25
    )

# Apply Tooltip to button_25
tooltip = ToolTip(button_25, """Required section, please select your timezone""")
button_25.bind("<Enter>", tooltip.show_tooltip)
button_25.bind("<Leave>", tooltip.hide_tooltip)


button_image_26 = PhotoImage(
    file=relative_to_assets("button_26.png"))
button_26 = Button(
    image=button_image_26,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_26 clicked"),
    relief="flat"
)
button_26.place(
    x=402.0,
    y=191.0,
    width=13.0,
    height=13.0
)

button_image_hover_26 = PhotoImage(
    file=relative_to_assets("button_hover_20.png"))

def button_26_hover(e):
    button_26.config(
        image=button_image_hover_26
    )
def button_26_leave(e):
    button_26.config(
        image=button_image_26
    )

# Apply Tooltip to button_26
tooltip = ToolTip(button_26, """Required section, please provide the time you want the scan
to run, and on what date""")
button_26.bind("<Enter>", tooltip.show_tooltip)
button_26.bind("<Leave>", tooltip.hide_tooltip)


button_image_27 = PhotoImage(
    file=relative_to_assets("button_27.png"))
button_27 = Button(
    window,
    image=button_image_27,
    borderwidth=0,
    command=handle_comment_input,
    highlightthickness=0,
    relief="flat"
)
button_27.place(
    x=331.0,
    y=98.0,
    width=621.0,
    height=75.0
)
comment_input = Entry(window, width=40, font=("Helvetica", 12), bg="#2C2C2C", fg="#FFFFFF", borderwidth=0)
comment_input.place(x=550, y=115, width=400, height=35)

button_image_28 = PhotoImage(
    file=relative_to_assets("button_28.png"))
button_28 = Button(
    image=button_image_28,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_28 clicked"),
    relief="flat"
)
button_28.place(
    x=402.0,
    y=126.0,
    width=13.0,
    height=13.0
)

button_image_hover_28 = PhotoImage(
    file=relative_to_assets("button_hover_21.png"))

def button_28_hover(e):
    button_28.config(
        image=button_image_hover_28
    )
def button_28_leave(e):
    button_28.config(
        image=button_image_28
    )

# Apply Tooltip to button_28
tooltip = ToolTip(button_28, """Optional section, allows you to provide 
a comment for the schedule.""")
button_28.bind("<Enter>", tooltip.show_tooltip)
button_28.bind("<Leave>", tooltip.hide_tooltip)



window.resizable(False, False)
window.mainloop()
