from pathlib import Path
import configparser
import os
import subprocess
import webbrowser
from datetime import datetime
import threading
import schedule
import time
import json
import queue
from tkcalendar import Calendar
from termcolor import colored
from PIL import Image, ImageTk
import pytz
from pytz import all_timezones
import json
from tkinter import (
    Tk,
    Canvas,
    Entry,
    Button,
    messagebox,
    ttk,
    Toplevel,
    Label,
    Frame,
    Text,
    PhotoImage,
    StringVar,
    Spinbox,
    Listbox,
    Scrollbar,
    OptionMenu,
)

"""
MedusaGuard GUI Application

This script implements the graphical user interface (GUI) for MedusaGuard, an automated vulnerability scanning
and exploitation tool. The GUI provides functionalities for starting/stopping scans, scheduling scans,
editing configurations, and viewing scan results.

The application is structured using Tkinter frames to represent different pages:
- Dashboard Frame: Main interface for initiating scans and viewing results.
- Edit Configuration Frame: Interface for editing scanning configurations.
- Schedule Frame: Interface for scheduling scans at specified times.

"""

# -------------------------------------------
# Global Variables and Helper Functions
# -------------------------------------------

# Get the base directory path of the script
BASE_PATH = Path(__file__).resolve().parent

# Define asset paths for different frames in the GUI
ASSETS_PATHS = {
    0: BASE_PATH / "assets" / "edit_conf_frame",
    1: BASE_PATH / "assets" / "dashboard_frame",
    2: BASE_PATH / "assets" / "scheduler_frame",
}

# Global variables for inter-thread communication and process management
output_queue = queue.Queue()  # Queue to hold subprocess output
scan_process = None           # Subprocess for running scans
start_scan_log_image = None   # Placeholder for start scan image
stop_scan_log_image = None    # Placeholder for stop scan image
cycling_images = False        # Flag to indicate if images should cycle during scan
current_image_index = 0       # Index for cycling images
new_vuln_image = None         # Holds the new vulnerability pie chart image after a scan
new_exploit_image = None      # Holds the new exploit pie chart image after a scan


def on_closing():
    """
    Handles the window close event by displaying a custom confirmation dialog.

    This function overrides the default window close behavior to prompt the user
    with a confirmation dialog before exiting the application.
    """

    # Create a custom dialog
    def confirm_exit():
        window.destroy()

    def cancel_exit():
        dialog.destroy()

    dialog = Toplevel(window)
    dialog.title("Exit")
    dialog.configure(bg="#121212")
    dialog.geometry("400x150")
    dialog.resizable(False, False)
    dialog.grab_set()  # Make the dialog modal
    dialog.focus_set()  # Focus on the dialog

    # Center the dialog over the main window
    window_x = window.winfo_x()
    window_y = window.winfo_y()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    dialog_width = 400
    dialog_height = 150
    position_right = window_x + int(window_width / 2 - dialog_width / 2)
    position_down = window_y + int(window_height / 2 - dialog_height / 2)
    dialog.geometry(f"{dialog_width}x{dialog_height}+{position_right}+{position_down}")

    # Message label
    message = Label(
        dialog,
        text="Are you sure you want to close this window?\nDoing so will end any ongoing tasks",
        bg="#121212",
        fg="#FFFFFF",
        font=("Inter", 12),
        wraplength=380,
        justify="center"
    )
    message.pack(pady=20)

    # Buttons frame
    buttons_frame = Frame(dialog, bg="#121212")
    buttons_frame.pack()

    # Yes button
    yes_button = Button(
        buttons_frame,
        text="Yes",
        command=confirm_exit,
        bg="#6A1B9A",
        fg="#FFFFFF",
        width=10,
        bd=0,
        highlightthickness=0,
        relief="flat",
        activebackground="#6A1B9A",
        activeforeground="#FFFFFF",
        font=("Inter", 12)
    )
    yes_button.pack(side="left", padx=20)

    # No button
    no_button = Button(
        buttons_frame,
        text="No",
        command=cancel_exit,
        bg="#313237",
        fg="#FFFFFF",
        width=10,
        bd=0,
        highlightthickness=0,
        relief="flat",
        activebackground="#313237",
        activeforeground="#FFFFFF",
        font=("Inter", 12)
    )
    no_button.pack(side="left", padx=20)

def open_supplied_link():
    """
    Opens the default browser to the desired link.
    """
    supplied_link = "https://github.com/LukeyBoyy/MedusaGuard"
    webbrowser.open(supplied_link)


# Helper functions
def relative_to_assets(path: str, frame_number: int = 0) -> Path:
    """
    Returns the full path to an asset file based on the frame number.

    Args:
        path (str): The relative path to the asset.
        frame_number (int): The frame identifier to select the correct asset path.

    Returns:
        Path: The full path to the asset file.
    """
    return ASSETS_PATHS.get(frame_number, BASE_PATH) / path


def open_directory(path: str):
    """
    Opens the specified directory or file using the default file explorer.

    Args:
        path (str): The path to the directory or file to open.
    """
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


def add_placeholder(entry, placeholder_text):
    """
    Adds a placeholder text to a Tkinter Entry widget and handles focus events.

    Args:
        entry (tkinter.Entry): The Entry widget to add the placeholder to.
        placeholder_text (str): The placeholder text to display.
    """
    entry.insert(0, placeholder_text)
    entry.config(fg="grey")

    def on_focus_in(event):
        if entry.get() == placeholder_text:
            entry.delete(0, "end")
            entry.config(fg="#FFFFFF")

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, placeholder_text)
            entry.config(fg="grey")

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)


class ToolTip:
    """
    Creates a tooltip for a given widget to display helpful information.

    Attributes:
        widget (tkinter.Widget): The widget to attach the tooltip to.
        text (str): The text to display in the tooltip.
        tooltip_window (tkinter.Toplevel): The window that displays the tooltip.
    """
    def __init__(self, widget, text):
        """
        Initializes the ToolTip instance.

        Args:
            widget (tkinter.Widget): The widget to attach the tooltip to.
            text (str): The text to display in the tooltip.
        """
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """
        Displays the tooltip near the widget when the mouse enters.

        Args:
            event: The event object.
        """
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 50
        y += self.widget.winfo_rooty() + 30
        self.tooltip_window = Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.geometry(f"+{x}+{y}")
        label = Label(
            self.tooltip_window,
            text=self.text,
            background="#121212",
            foreground="white",
            borderwidth=1,
            relief="solid",
            highlightbackground="#313237",
            highlightthickness=1,
            padx=7,
            pady=7,
        )
        label.pack()

    def hide_tooltip(self, event):
        """
        Hides the tooltip when the mouse leaves the widget.

        Args:
            event: The event object.
        """
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def save_dark_popup():
    """
    Displays a confirmation popup after saving configurations.
    """
    popup = Toplevel(window)  # Use Toplevel instead of Tk()
    popup.geometry("400x150")
    popup.configure(bg="#121212")
    popup.title("Success")

    label = ttk.Label(
        popup,
        text="Your changes have been made successfully!",
        foreground="#FFFFFF",
        background="#121212",
        font=("Inter", 11),
    )
    label.pack(pady=30)

    ok_button = ttk.Button(popup, text="OK", command=popup.destroy)
    ok_button.pack(pady=10)

# -------------------------------------------
# Scan Functions
# -------------------------------------------
# Function to insert text into the Text widget
def insert_output(line):
    dashboard_output_text.config(state='normal')
    dashboard_output_text.insert('end', line, 'spacing')
    dashboard_output_text.see('end')
    dashboard_output_text.config(state='disabled')

def start_scan():
    """
    Initiates the scan process by running 'main.py' in a separate thread.
    Clears previous output and starts cycling images during the scan.
    """
    global cycling_images, current_image_index

    # Clear previous output
    dashboard_output_text.config(state="normal")
    dashboard_output_text.delete("1.0", "end")
    dashboard_output_text.config(state="disabled")

    # Start the scan in a new daemon thread
    scan_thread = threading.Thread(target=run_main_py, daemon=True)
    scan_thread.start()

    # Start cycling the images
    cycling_images = True
    current_image_index = 0
    cycle_dashboard_images()


def cycle_dashboard_images():
    """
    Cycles through a list of images for the dashboard button during the scan.
    """
    global current_image_index, cycling_images

    if cycling_images:
        # Update the image
        dashboard_button_1.config(image=start_scan_log_images[current_image_index])
        # Move to the next image
        current_image_index = (current_image_index + 1) % len(start_scan_log_images)
        # Schedule the next update
        window.after(
            500, cycle_dashboard_images
        )  # Adjust the interval as needed (milliseconds)


def run_main_py():
    """
    Runs 'main.py' as a subprocess and captures its output.

    Captures stdout and stderr, placing each line into the output queue.
    Upon completion, signals the end of output by placing None into the queue.
    """
    global scan_process  # Declare as global to modify the global variable
    try:
        # Start the subprocess with unbuffered output
        scan_process = subprocess.Popen(
            ["python3", "-u", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered
        )

        # Read the stdout line by line
        for line in scan_process.stdout:
            output_queue.put(line)

        scan_process.stdout.close()
        scan_process.wait()
    except Exception as e:
        output_queue.put(f"Error running main.py: {e}\n")
    finally:
        # Signal that the scan has completed
        output_queue.put(None)
        scan_process = None  # Reset the scan_process variable


def process_output_queue():
    """
    Periodically checks the output queue for new lines and inserts them into the dashboard output.

    Re-enables the Start Scan button when the scan is complete.
    """
    global cycling_images     # Add cycling_images here
    global new_vuln_image     # Declare new_vuln_image as global
    global vuln_image_label
    global new_exploit_image  # Declare new_exploit_image as global
    global exploit_image_label
    try:
        while True:
            line = output_queue.get_nowait()
            if line is None:
                # Scan has completed
                dashboard_button_18.config(state="normal")
                insert_output("\nScan Completed.\n")
                # Stop cycling the images
                cycling_images = False
                # Change the image of dashboard_button_1 to a 'stopped' image
                dashboard_button_1.config(image=stop_scan_log_image)

                # Update the vuln graph image
                try:
                    # Load the new image
                    new_vuln_image = PhotoImage(file='result_graphs/vuln_pie.png')
                    new_exploit_image = PhotoImage(file='result_graphs/exploit_pie.png')
                    # Update the vuln_image_label with the new image
                    vuln_image_label.config(image=new_vuln_image)
                    # Update the exploit_image_label with the new image
                    exploit_image_label.config(image=new_exploit_image)
                    # Keep a reference to prevent garbage collection
                    vuln_image_label.image = new_vuln_image
                    exploit_image_label.image = new_exploit_image
                except Exception as e:
                    print(f"Error loading new vuln image: {e}")

                # Read the counts from counts.json
                try:
                    with open('counts.json', 'r') as f:
                        counts = json.load(f)
                    hosts_count = counts.get('hosts_count', 0)
                    apps_count = counts.get('apps_count', 0)
                    os_count = counts.get('os_count', 0)
                    high_count = counts.get('high_count', 0)
                    medium_count = counts.get('medium_count', 0)
                    low_count = counts.get('low_count', 0)
                    exploitedcves = counts.get('exploitedcves', 0)
                    incompatiblecves = counts.get('incompatiblecves', 0)
                    tot_cve = int(exploitedcves) + int(incompatiblecves)

                    # Update the vuln_content variable
                    vuln_content = f"""
    [+] Hosts scanned: {hosts_count}
    [+] Applications scanned: {os_count}
    [+] Operating systems scanned: {apps_count}

    ██████████ High vulnerabilities: {high_count}
    ██████░░░░ Medium vulnerabilities: {medium_count}
    ███░░░░░░░ Low vulnerabilities: {low_count}
    """
                    # Update the label
                    vuln_scan_results_label.config(text=vuln_content)

                    # Update the exploit_content variable
                    exploit_content = f"""
    [+] Number of exploited CVEs: {exploitedcves}
    [+] Number of CVEs without exploits: {incompatiblecves}
    [+] Total CVEs examined: {tot_cve}
    
    
    
    
    """
                    # Update the label
                    exploit_results_text.config(text=exploit_content)

                except Exception as e:
                    print(f"Error reading counts.json: {e}")
            else:
                insert_output(line)
    except queue.Empty:
        pass
    finally:
        # Schedule the next check
        window.after(50, process_output_queue)



def stop_scan():
    """
    Terminates the running scan subprocess if it exists.

    Inserts a message into the output indicating the scan was stopped.
    Re-enables the Start Scan button and stops image cycling.
    """
    global scan_process, cycling_images  # Add cycling_images here
    if scan_process and scan_process.poll() is None:
        try:
            scan_process.terminate()  # Gracefully terminate the subprocess
            scan_process.wait(timeout=5)  # Wait for it to terminate
            insert_output("\nScan has been terminated by the user.\n")
        except subprocess.TimeoutExpired:
            scan_process.kill()  # Force kill if it doesn't terminate
            insert_output("\nScan process was forcefully killed.\n")
        except Exception as e:
            insert_output(f"\nError stopping scan: {e}\n")
        finally:
            scan_process = None  # Reset the scan_process variable

        # Stop cycling the images
        cycling_images = False
        # Change the image of dashboard_button_1 to a 'stopped' image
        dashboard_button_1.config(image=stop_scan_log_image)
    else:
        insert_output("\nNo active scan to stop.\n")


# Global flag to control the scheduler
running_scheduler = True

# Process object for the scan (to allow termination)
scan_process = None

# -------------------------------------------
# Schedule Configuration Functions
# -------------------------------------------

# Function to run the scan (e.g., executing the main.py script)
def run_scan():
    """
    Executes the scan by running 'main.py' as a subprocess.

    Waits for the scan process to complete before returning.
    """
    global scan_process
    print("Starting the scan now...")
    scan_process = subprocess.Popen(["python3", "main.py"])  # Modify if needed
    scan_process.wait()  # Wait for the scan process to finish


# Function to schedule the scan based on schedule_config.JSON configuration
def start_scheduled_scan():
    """
    Reads the schedule configuration and schedules scans accordingly.

    If a future date and time are specified, schedules the scan to run at that time.
    Repeats the scan based on the specified interval.
    """
    global running_scheduler
    try:
        # Load the schedule config
        with open("schedule_config.json", "r") as config_file:
            schedule_data = json.load(config_file)

        # Extract scheduling information
        comment = schedule_data.get("Comment", "No Comment")
        scan_date = schedule_data.get("Date", "Not Selected")
        scan_time = schedule_data.get("Time", "Not Selected")
        scan_timezone = schedule_data.get("Timezone", "UTC")
        repeat_every = schedule_data.get("Repeat Every", 1)  # Repeat interval in days

        # Parse the date and time into a timezone-aware datetime object
        naive_scan_datetime = datetime.strptime(
            f"{scan_date} {scan_time}", "%d/%m/%Y %H:%M"
        )
        user_timezone = pytz.timezone(scan_timezone)  # Get the timezone object
        scan_datetime = user_timezone.localize(
            naive_scan_datetime
        )  # Make datetime timezone aware

        # Get current time in the same timezone
        now = datetime.now(user_timezone)

        # If the scan time is in the future, schedule it
        if scan_datetime > now:
            delay_seconds = (scan_datetime - now).total_seconds()
            print(
                f"Scan scheduled for {scan_datetime} ({scan_timezone}), which is in {delay_seconds} seconds."
            )
            print(f"The scan will repeat every {repeat_every} day(s).")
            threading.Timer(delay_seconds, run_scan).start()
        else:
            print("The scheduled scan time has already passed.")

        # Schedule to repeat the scan based on the interval
        if repeat_every > 0:
            schedule.every(repeat_every).days.do(run_scan)

    except Exception as e:
        print(f"Error reading schedule config: {str(e)}")


# Function to continuously check for scheduled tasks
def run_scheduler():
    """
    Continuously checks for scheduled tasks and runs them when due.

    Runs in a separate thread and checks the schedule every second.
    """
    global running_scheduler
    while running_scheduler:
        schedule.run_pending()
        time.sleep(31)


# Function to stop the scheduler and the scan process
def stop_scheduled_scan():
    """
    Stops the scheduler and any running scan process.

    Navigates back to the dashboard frame in the GUI.
    """
    global running_scheduler, scan_process

    # Stop the scheduler
    running_scheduler = False
    print("\nStopping the scheduler...")

    # Terminate the running scan process if it exists
    if scan_process and scan_process.poll() is None:  # Check if the process is running
        print("Terminating the running scan process...")
        scan_process.terminate()  # Terminate the scan process
        scan_process = None

    print("Scheduler and scan process stopped.")

    # Navigates back to the dashboard screen
    show_frame(dashboard_frame)


# Function to open the calendar and select a date
def open_calendar():
    """
    Opens a calendar widget for the user to select a date.

    Updates the 'date_display_var' with the selected date.
    """
    def get_selected_date():
        selected_date = cal.get_date()
        date_display_var.set(selected_date)
        update_summary()
        top.destroy()

    top = Toplevel(window)
    cal = Calendar(top, selectmode="day", date_pattern="dd/mm/yyyy")
    cal.pack(pady=20)
    select_btn = Button(top, text="Select", command=get_selected_date)
    select_btn.pack()


# Function that gets called when button_27 is pressed
def handle_comment_input():
    """
    Handles the comment input from the user and updates the summary.
    """
    comment_text = comment_input.get()
    print(f"Comment entered: {comment_text}")
    update_summary()


# Function to handle saving the schedule config
def save_schedule_config():
    """
    Saves the scheduling configuration to 'schedule_config.json'.

    Validates inputs and provides feedback to the user upon success or failure.
    """
    comment_text = comment_input.get()
    # Checks to see if it's the placeholder value
    if not comment_text or comment_text == "Enter your comment here":
        comment_text = "No Comment"  # Replace with default text

    interval_value = (
        repeat_interval_display_var.get()
        if repeat_interval_display_var.get()
        else "Not Selected"
    )
    interval_in_days = calculate_interval_days(interval_value)

    schedule_data = {
        "Comment": comment_text,
        "Date": date_display_var.get() if date_display_var.get() else "Not Selected",
        "Time": time_display_var.get() if time_display_var.get() else "Not Selected",
        "Timezone": timezone_display_var.get()
        if timezone_display_var.get()
        else "Not Selected",
        "Repeat Every": interval_in_days,  # Save the interval as days instead of the string
    }

    # Save (overwrite) the data to a JSON file (schedule_config.json)
    try:
        with open("schedule_config.json", "w") as config_file:
            json.dump(schedule_data, config_file, indent=4)

        messagebox.showinfo("Success", "The schedule configuration has been saved.")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save the configuration: {str(e)}")

    comment_input.delete(0, "end")

    start_scheduled_scan()
    show_frame(dashboard_frame)


def calculate_interval_days(interval_value):
    """
    Converts the repeat interval string into the corresponding number of days.

    Args:
        interval_value (str): The repeat interval selected by the user.

    Returns:
        int: The number of days corresponding to the interval.
    """
    if interval_value == "Daily":
        return 1
    elif interval_value == "Weekly":
        return 7
    elif interval_value == "Fortnightly":
        return 14
    elif interval_value == "Monthly":
        return 30
    else:
        return 1


# Function to open time selection
def open_time_selector():
    """
    Opens a time selector for the user to select hours and minutes.

    Updates the 'time_display_var' with the selected time.
    """
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
    """
    Opens a listbox for the user to select a timezone.

    Updates the 'timezone_display_var' with the selected timezone.
    """
    def on_select(event):
        selected = listbox.get(listbox.curselection())
        timezone_display_var.set(selected)
        update_summary()
        top.destroy()

    top = Toplevel(window)
    top.title("Select Timezone")
    top.configure(bg="#121212")  # Set the background color to dark theme

    # Style the scrollbar (Note: Styling the scrollbar is limited in Tkinter)
    scrollbar = Scrollbar(top)
    scrollbar.pack(side="right", fill="y")
    scrollbar.configure(
        background="#313237",
        troughcolor="#1B1C21",
        bd=0,
        highlightthickness=0
    )

    # Style the listbox
    listbox = Listbox(
        top,
        yscrollcommand=scrollbar.set,
        width=50,
        height=20,
        bg="#1B1C21",              # Background color for dark theme
        fg="#FFFFFF",              # Text color
        selectbackground="#6A1B9A",  # Highlight color when an item is selected
        selectforeground="#FFFFFF",  # Text color of selected item
        bd=0,
        highlightthickness=0
    )
    for tz in all_timezones:
        listbox.insert("end", tz)

    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    listbox.bind("<<ListboxSelect>>", on_select)


# Function to handle showing the Repeat Interval OptionMenu when button_21 is clicked
def show_interval_menu():
    """
    Displays an OptionMenu for the user to select a repeat interval.

    Updates the summary after selection.
    """
    interval_menu = OptionMenu(
        window, interval_var, *interval_options, command=select_repeat_interval
    )
    interval_menu.place(x=660.0, y=320.0, width=150.0, height=30.0)


# Function to handle Repeat Interval Selection
def select_repeat_interval(selected_option):
    """
    Updates the 'repeat_interval_display_var' and summary when an interval is selected.

    Args:
        selected_option (str): The selected repeat interval option.
    """
    repeat_interval_display_var.set(selected_option)
    update_summary()

    for widget in window.winfo_children():
        if isinstance(widget, OptionMenu):
            widget.destroy()


# Function to update the summary section on button_23
def update_summary():
    """
    Updates the summary label to reflect the current scheduling selections.
    """
    summary_text = (
        f"Date: {date_display_var.get() if date_display_var.get() else 'Not Selected'}, "
        f"Time: {time_display_var.get() if time_display_var.get() else 'Not Selected'}, "
        f"Timezone: {timezone_display_var.get() if timezone_display_var.get() else 'Not Selected'}, "
        f"Repeat Every: {repeat_interval_display_var.get() if repeat_interval_display_var.get() else 'Not Selected'}"
    )
    button_23.config(text=summary_text)

# -------------------------------------------
# Configuration Editing Functions
# -------------------------------------------

def save_to_config():
    """
    Saves the configuration settings to 'config.ini'.

    Only saves fields that have been modified (i.e., not matching placeholder text).
    """
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Define placeholder strings for each field
    placeholder_path = "Enter the socket path here"
    placeholder_username = "Enter your greenbone username here"
    placeholder_password = "Enter your password here"
    placeholder_target_name = "Enter your target name here"
    placeholder_target_ip = "Enter the target IP here"
    placeholder_port_list_name = "Enter the port list ID here"
    placeholder_task_name = "Enter your task name here"
    placeholder_scan_config = "Enter the scan config ID here"
    placeholder_scanner = "Enter the scanner ID here"

    # Only save values that don't match the placeholder strings
    if edit_conf_path.get() != placeholder_path and edit_conf_path.get():
        config["connection"]["path"] = edit_conf_path.get()
    if edit_conf_username.get() != placeholder_username and edit_conf_username.get():
        config["connection"]["username"] = edit_conf_username.get()
    if edit_conf_password.get() != placeholder_password and edit_conf_password.get():
        config["connection"]["password"] = edit_conf_password.get()

    if (
        edit_conf_target_name.get() != placeholder_target_name
        and edit_conf_target_name.get()
    ):
        config["target"]["target_name"] = edit_conf_target_name.get()
    if (
        edit_conf_port_list_name.get() != placeholder_port_list_name
        and edit_conf_port_list_name.get()
    ):
        config["target"]["port_list_name"] = edit_conf_port_list_name.get()

    if edit_conf_task_name.get() != placeholder_task_name and edit_conf_task_name.get():
        config["task"]["task_name"] = edit_conf_task_name.get()
    if (
        edit_conf_scan_config.get() != placeholder_scan_config
        and edit_conf_scan_config.get()
    ):
        config["task"]["scan_config"] = edit_conf_scan_config.get()
    if edit_conf_scanner.get() != placeholder_scanner and edit_conf_scanner.get():
        config["task"]["scanner"] = edit_conf_scanner.get()

    # Save the updated config file
    with open("config.ini", "w") as configfile:
        config.write(configfile)

    # Handle the target IP input
    target_ip_value = edit_conf_target_ip.get()
    if target_ip_value != placeholder_target_ip and target_ip_value:
        # Ensure the new IP is added on a new line
        if os.path.exists("targets.txt"):
            with open("targets.txt", "r+") as targets_file:
                targets_file.seek(0, os.SEEK_END)  # Move to the end of the file
                if targets_file.tell() > 0:
                    targets_file.seek(targets_file.tell() - 1)
                    last_char = targets_file.read(1)
                    if last_char != '\n':
                        targets_file.write('\n')  # Add newline if not present
                targets_file.write(f"{target_ip_value}\n")  # Append new IP
        else:
            # If the file doesn't exist, create it and write the IP
            with open("targets.txt", "w") as targets_file:
                targets_file.write(f"{target_ip_value}\n")

    # Clear all entries after saving
    clear_entries()

    # Show success popup
    save_dark_popup()

    show_frame(dashboard_frame)


def clear_entries():
    """
    Clears all input fields in the configuration editor.
    """
    edit_conf_path.delete(0, "end")
    edit_conf_username.delete(0, "end")
    edit_conf_password.delete(0, "end")
    edit_conf_target_name.delete(0, "end")
    edit_conf_target_ip.delete(0, "end")
    edit_conf_port_list_name.delete(0, "end")
    edit_conf_task_name.delete(0, "end")
    edit_conf_scan_config.delete(0, "end")
    edit_conf_scanner.delete(0, "end")


def show_frame(frame):
    """
    Raises the specified frame to the top of the stacking order.

    Args:
        frame (tkinter.Frame): The frame to display.
    """
    frame.tkraise()

# -------------------------------------------
# Main Application Initialization
# -------------------------------------------

# Initialize the main application window
window = Tk()
window.title("MedusaGuard")
window.geometry("1000x885")
window.configure(bg="#121212")
window.withdraw()  # Hide the window initially
logo_image = PhotoImage(file=BASE_PATH / "assets" / "logo.png")  # Load the logo image
window.iconphoto(False, logo_image)  # Set the window icon
window.protocol("WM_DELETE_WINDOW", on_closing)  # Bind the close event

# Create the splash screen window
splash = Toplevel()
splash.overrideredirect(True)
splash.geometry("550x450")
splash.configure(bg="#121212")

# Center the splash screen
screen_width = splash.winfo_screenwidth()
screen_height = splash.winfo_screenheight()
x = int((screen_width / 2) - (400 / 2))
y = int((screen_height / 2) - (300 / 2))
splash.geometry(f"+{x}+{y}")

# Add content to the splash screen
logo_image_splash = PhotoImage(file=BASE_PATH / "assets" / "splash_image.png")
logo_label = Label(splash, image=logo_image_splash, bg="#121212")
logo_label.pack(expand=True)

# Keep a reference to prevent garbage collection
splash.logo_image_splash = logo_image_splash

# Function to destroy splash screen and show main window
def show_main_window():
    splash.destroy()
    # Center the main window
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window_width = 1000
    window_height = 885
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    window.deiconify()  # Show the main window

# Schedule splash screen to close after 3 seconds
window.after(6000, show_main_window)

# Create frames for different pages
edit_config_frame = Frame(window, bg="#121212")  # Edit configuration frame
dashboard_frame = Frame(window, bg="#121212")  # Dashboard/Main frame
schedule_frame = Frame(window, bg="#121212")  # Scan scheduler frame

# Place all frames in the same location; only the raised frame will be visible
for frame in (edit_config_frame, dashboard_frame, schedule_frame):
    frame.place(relwidth=1, relheight=1)
show_frame(dashboard_frame)  # Initially display the dashboard frame

# Check if the script is being run with root privileges
if os.getuid() != 0:
    exit(
        colored(
            "You need to have root privileges to use this tool correctly.\nPlease try again, this time using 'sudo'. Exiting...",
            "red",
        )
    )

# -------------------------------------------
# Variables and UI Elements for Schedule Page
# -------------------------------------------

# Create the canvas for the schedule frame
canvas = Canvas(
    schedule_frame,
    bg="#FFFFFF",
    height=885,
    width=1000,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

canvas.place(x=0, y=0)
canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    885.0,
    fill="#121212",
    outline=""
)

canvas.create_rectangle(
    0.0,
    0.0,
    272.0,
    885.0,
    fill="#1B1C21",
    outline=""
)

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

# Variables to hold user selections
# Entry for displaying the selected date
date_display_var = StringVar()
# Entry for displaying the selected time
time_display_var = StringVar()
# Entry for displaying the selected timezone
timezone_display_var = StringVar()
# Label for displaying the selected repeat interval
repeat_interval_display_var = StringVar()

# OptionMenu variables for repeat interval
interval_var = StringVar()
interval_var.set("Daily")
interval_options = ["Daily", "Weekly", "Fortnightly", "Monthly"]

# Sidebar buttons with hover effects and commands
stop_scan_image = PhotoImage(
    file=relative_to_assets("button_1.png", 2))
stop_scan_button = Button(
    schedule_frame,
    image=stop_scan_image,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('custom_reports'),
    relief="flat"
)
stop_scan_button.place(
    x=24.0,
    y=209.0,
    width=248.0,
    height=44.0
)

stop_scan_button_hover_image = PhotoImage(
    file=relative_to_assets("button_hover_1.png", 2))


def button_1_hover(e):
    stop_scan_button.config(
        image=stop_scan_button_hover_image
    )


def button_1_leave(e):
    stop_scan_button.config(
        image=stop_scan_image
    )


stop_scan_button.bind('<Enter>', button_1_hover)
stop_scan_button.bind('<Leave>', button_1_leave)

# Sidebar greenbone reports link
button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png", 2))
button_2 = Button(
    schedule_frame,
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('openvas_reports'),
    relief="flat"
)
button_2.place(
    x=19.0,
    y=240.0,
    width=246.0,
    height=46.0
)

button_image_hover_2 = PhotoImage(
    file=relative_to_assets("button_hover_2.png", 2))


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
    file=relative_to_assets("button_3.png", 2))
button_3 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_3.png", 2))


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
    file=relative_to_assets("button_4.png", 2))
button_4 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_4.png", 2))


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
    file=relative_to_assets("button_5.png", 2))
button_5 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_5.png", 2))


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
    file=relative_to_assets("button_6.png", 2))
button_6 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_6.png", 2))


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
    file=relative_to_assets("button_7.png", 2))
button_7 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_7.png", 2))


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
    file=relative_to_assets("button_8.png", 2))
button_8 = Button(
    schedule_frame,
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
button_8.place(
    x=24.0,
    y=129.0,
    width=248.0,
    height=44.0
)

button_image_hover_8 = PhotoImage(
    file=relative_to_assets("button_hover_8.png", 2))


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

# Tips feed button
button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png", 2))
button_9 = Button(
    schedule_frame,
    image=button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
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
    outline=""
)

canvas.create_text(
    75.0,
    11.0,
    anchor="nw",
    text="Scan Scheduler",
    fill="#FFFFFF",
    font=("Inter Bold", 18 * -1)
)

# Top right documentation link
button_image_10 = PhotoImage(
    file=relative_to_assets("button_10.png", 2))
button_10 = Button(
    schedule_frame,
    image=button_image_10,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
button_10.place(
    x=902.0,
    y=0.0,
    width=76.0,
    height=41.0
)

button_image_hover_10 = PhotoImage(
    file=relative_to_assets("button_hover_9.png", 2))


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

# Back button
button_image_11 = PhotoImage(
    file=relative_to_assets("button_11.png", 2))
button_11 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_10.png", 2))


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
    file=relative_to_assets("button_12.png", 2))
button_12 = Button(
    schedule_frame,
    image=button_image_12,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: show_frame(dashboard_frame),
    relief="flat"
)
button_12.place(
    x=24.0,
    y=98.0,
    width=248.0,
    height=39.0
)

button_image_hover_12 = PhotoImage(
    file=relative_to_assets("button_hover_11.png", 2))


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
    file=relative_to_assets("button_13.png", 2))
button_13 = Button(
    schedule_frame,
    image=button_image_13,
    borderwidth=0,
    highlightthickness=0,
    command=stop_scheduled_scan,
    relief="flat"
)
button_13.place(
    x=415.0,
    y=450,
    width=118.0,
    height=73.0
)

button_image_hover_13 = PhotoImage(
    file=relative_to_assets("button_hover_12.png", 2))


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
    file=relative_to_assets("button_14.png", 2))
button_14 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_13.png", 2))


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
    file=relative_to_assets("button_15.png", 2))
button_15 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_16.png", 2))
button_16 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_14.png", 2))


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
    file=relative_to_assets("button_17.png", 2))
button_17 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_15.png", 2))


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
    file=relative_to_assets("button_18.png", 2))
button_18 = Button(
    schedule_frame,
    image=button_image_18,
    borderwidth=0,
    highlightthickness=0,
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
    file=relative_to_assets("button_19.png", 2))
button_19 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_16.png", 2))


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
    file=relative_to_assets("button_20.png", 2))
button_20 = Button(
    schedule_frame,
    image=button_image_20,
    borderwidth=0,
    highlightthickness=0,
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
    file=relative_to_assets("button_21.png", 2))
button_21 = Button(
    schedule_frame,
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
    file=relative_to_assets("button_hover_17.png", 2))


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
    file=relative_to_assets("button_22.png", 2))
button_22 = Button(
    schedule_frame,
    image=button_image_22,
    borderwidth=0,
    highlightthickness=0,
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
    file=relative_to_assets("button_23.png", 2))

button_23 = Label(
    schedule_frame,
    text="Date: , Time: , Timezone: , Repeat Every:",
    borderwidth=0,
    relief="flat",
    anchor="w",
    bg="#1B1C21",
    fg="#FFFFFF",
    font=("Inter", 10),
    justify="left",
    padx=10,
    pady=10,
    wraplength=580
)
button_23.place(
    x=321.0,
    y=371.0,
    width=631.0,
    height=55.0
)

button_image_24 = PhotoImage(
    file=relative_to_assets("button_24.png", 2))
button_24 = Button(
    schedule_frame,
    image=button_image_24,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_24.place(
    x=425.0,
    y=328.0,
    width=13.0,
    height=13.0
)

button_image_hover_24 = PhotoImage(
    file=relative_to_assets("button_hover_18.png", 2))


def button_24_hover(e):
    button_24.config(
        image=button_image_hover_24
    )


def button_24_leave(e):
    button_24.config(
        image=button_image_24
    )

# Apply Tooltip to button_24
tooltip_24 = ToolTip(button_24, """Required section, enables you to have this scheduled scan run
repeatedly, rather than only once""")
button_24.bind("<Enter>", tooltip_24.show_tooltip)
button_24.bind("<Leave>", tooltip_24.hide_tooltip)

button_image_25 = PhotoImage(
    file=relative_to_assets("button_25.png", 2))
button_25 = Button(
    schedule_frame,
    image=button_image_25,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_25.place(
    x=402.0,
    y=261.0,
    width=13.0,
    height=13.0
)

button_image_hover_25 = PhotoImage(
    file=relative_to_assets("button_hover_19.png", 2))


def button_25_hover(e):
    button_25.config(
        image=button_image_hover_25
    )


def button_25_leave(e):
    button_25.config(
        image=button_image_25
    )


# Apply Tooltip to button_25
tooltip_25 = ToolTip(button_25, """Required section, please select your timezone""")
button_25.bind("<Enter>", tooltip_25.show_tooltip)
button_25.bind("<Leave>", tooltip_25.hide_tooltip)

button_image_26 = PhotoImage(
    file=relative_to_assets("button_26.png", 2))
button_26 = Button(
    schedule_frame,
    image=button_image_26,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_26.place(
    x=402.0,
    y=191.0,
    width=13.0,
    height=13.0
)

button_image_hover_26 = PhotoImage(
    file=relative_to_assets("button_hover_20.png", 2))


def button_26_hover(e):
    button_26.config(
        image=button_image_hover_26
    )


def button_26_leave(e):
    button_26.config(
        image=button_image_26
    )


# Apply Tooltip to button_26
tooltip_26 = ToolTip(button_26, """Required section, please provide the time you want the scan
to run, and on what date""")
button_26.bind("<Enter>", tooltip_26.show_tooltip)
button_26.bind("<Leave>", tooltip_26.hide_tooltip)

button_image_27 = PhotoImage(
    file=relative_to_assets("button_27.png", 2))
button_27 = Button(
    schedule_frame,
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
comment_input = Entry(
    schedule_frame,
    width=40,
    font=("Helvetica", 12),
    bg="#313237",
    fg="#FFFFFF",
    bd=0,
    highlightthickness=0,
    relief="flat",
    insertbackground="#FFFFFF"
)
add_placeholder(comment_input, "Enter your comment here")
comment_input.place(x=560, y=115, width=385, height=35)

button_image_28 = PhotoImage(
    file=relative_to_assets("button_28.png", 2))
button_28 = Button(
    schedule_frame,
    image=button_image_28,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
button_28.place(
    x=402.0,
    y=126.0,
    width=13.0,
    height=13.0
)

button_image_hover_28 = PhotoImage(
    file=relative_to_assets("button_hover_21.png", 2))


def button_28_hover(e):
    button_28.config(
        image=button_image_hover_28
    )


def button_28_leave(e):
    button_28.config(
        image=button_image_28
    )


# Apply Tooltip to button_28
tooltip_28 = ToolTip(button_28, """Optional section, allows you to provide 
a comment for the schedule.""")
button_28.bind("<Enter>", tooltip_28.show_tooltip)
button_28.bind("<Leave>", tooltip_28.hide_tooltip)

# -----------------------------------------------------
# Variables and UI Elements for Edit Configuration Page
# -----------------------------------------------------
edit_conf_canvas = Canvas(
    edit_config_frame,
    bg="#FFFFFF",
    height=885,
    width=1000,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

edit_conf_canvas.place(x=0, y=0)
edit_conf_canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    885.0,
    fill="#121212",
    outline="")

edit_conf_canvas.create_rectangle(
    0.0,
    0.0,
    272.0,
    885.0,
    fill="#1B1C21",
    outline="")

edit_conf_canvas.create_text(
    37.0,
    194.0,
    anchor="nw",
    text="Folders",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

edit_conf_canvas.create_text(
    37.0,
    412.0,
    anchor="nw",
    text="Config",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

edit_conf_button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
edit_conf_button_1 = Button(
    edit_config_frame,
    image=edit_conf_button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('custom_reports'),
    relief="flat"
)
edit_conf_button_1.place(
    x=24.0,
    y=209.0,
    width=248.0,
    height=44.0
)

edit_conf_button_image_hover_1 = PhotoImage(
    file=relative_to_assets("button_hover_1.png"))


def edit_conf_button_1_hover(e):
    edit_conf_button_1.config(
        image=edit_conf_button_image_hover_1
    )


def edit_conf_button_1_leave(e):
    edit_conf_button_1.config(
        image=edit_conf_button_image_1
    )


edit_conf_button_1.bind('<Enter>', edit_conf_button_1_hover)
edit_conf_button_1.bind('<Leave>', edit_conf_button_1_leave)

edit_conf_button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
edit_conf_button_2 = Button(
    edit_config_frame,
    image=edit_conf_button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('openvas_reports'),
    relief="flat"
)
edit_conf_button_2.place(
    x=19.0,
    y=240.0,
    width=246.0,
    height=46.0
)

edit_conf_button_image_hover_2 = PhotoImage(
    file=relative_to_assets("button_hover_2.png"))


def edit_conf_button_2_hover(e):
    edit_conf_button_2.config(
        image=edit_conf_button_image_hover_2
    )


def edit_conf_button_2_leave(e):
    edit_conf_button_2.config(
        image=edit_conf_button_image_2
    )


edit_conf_button_2.bind('<Enter>', edit_conf_button_2_hover)
edit_conf_button_2.bind('<Leave>', edit_conf_button_2_leave)

edit_conf_button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
edit_conf_button_3 = Button(
    edit_config_frame,
    image=edit_conf_button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nuclei_results'),
    relief="flat"
)
edit_conf_button_3.place(
    x=24.497802734375,
    y=275.791748046875,
    width=225.80621337890625,
    height=37.6944465637207
)

edit_conf_button_image_hover_3 = PhotoImage(
    file=relative_to_assets("button_hover_3.png"))


def edit_conf_button_3_hover(e):
    edit_conf_button_3.config(
        image=edit_conf_button_image_hover_3
    )


def edit_conf_button_3_leave(e):
    edit_conf_button_3.config(
        image=edit_conf_button_image_3
    )


edit_conf_button_3.bind('<Enter>', edit_conf_button_3_hover)
edit_conf_button_3.bind('<Leave>', edit_conf_button_3_leave)

edit_conf_button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
edit_conf_button_4 = Button(
    edit_config_frame,
    image=edit_conf_button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('metasploit_results'),
    relief="flat"
)
edit_conf_button_4.place(
    x=19.0,
    y=311.0,
    width=253.0,
    height=43.0
)

edit_conf_button_image_hover_4 = PhotoImage(
    file=relative_to_assets("button_hover_4.png"))


def edit_conf_button_4_hover(e):
    edit_conf_button_4.config(
        image=edit_conf_button_image_hover_4
    )


def edit_conf_button_4_leave(e):
    edit_conf_button_4.config(
        image=edit_conf_button_image_4
    )


edit_conf_button_4.bind('<Enter>', edit_conf_button_4_hover)
edit_conf_button_4.bind('<Leave>', edit_conf_button_4_leave)

edit_conf_button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
edit_conf_button_5 = Button(
    edit_config_frame,
    image=edit_conf_button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nikto_results'),
    relief="flat"
)
edit_conf_button_5.place(
    x=19.0,
    y=347.0,
    width=238.0,
    height=50.0
)

edit_conf_button_image_hover_5 = PhotoImage(
    file=relative_to_assets("button_hover_5.png"))


def edit_conf_button_5_hover(e):
    edit_conf_button_5.config(
        image=edit_conf_button_image_hover_5
    )


def edit_conf_button_5_leave(e):
    edit_conf_button_5.config(
        image=edit_conf_button_image_5
    )


edit_conf_button_5.bind('<Enter>', edit_conf_button_5_hover)
edit_conf_button_5.bind('<Leave>', edit_conf_button_5_leave)

edit_conf_button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png"))
edit_conf_button_6 = Button(
    edit_config_frame,
    image=edit_conf_button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('config.ini'),
    relief="flat"
)
edit_conf_button_6.place(
    x=32.830322265625,
    y=431.4862060546875,
    width=217.47396850585938,
    height=37.6944465637207
)

edit_conf_button_image_hover_6 = PhotoImage(
    file=relative_to_assets("button_hover_6.png"))


def edit_conf_button_6_hover(e):
    edit_conf_button_6.config(
        image=edit_conf_button_image_hover_6
    )


def edit_conf_button_6_leave(e):
    edit_conf_button_6.config(
        image=edit_conf_button_image_6
    )


edit_conf_button_6.bind('<Enter>', edit_conf_button_6_hover)
edit_conf_button_6.bind('<Leave>', edit_conf_button_6_leave)

edit_conf_button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png"))
edit_conf_button_7 = Button(
    edit_config_frame,
    image=edit_conf_button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('targets.txt'),
    relief="flat"
)
edit_conf_button_7.place(
    x=14.4990234375,
    y=466.72216796875,
    width=235.80499267578125,
    height=37.6944465637207
)

edit_conf_button_image_hover_7 = PhotoImage(
    file=relative_to_assets("button_hover_7.png"))


def edit_conf_button_7_hover(e):
    edit_conf_button_7.config(
        image=edit_conf_button_image_hover_7
    )


def edit_conf_button_7_leave(e):
    edit_conf_button_7.config(
        image=edit_conf_button_image_7
    )


edit_conf_button_7.bind('<Enter>', edit_conf_button_7_hover)
edit_conf_button_7.bind('<Leave>', edit_conf_button_7_leave)

edit_conf_button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png"))
edit_conf_button_8 = Button(
    edit_config_frame,
    image=edit_conf_button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: show_frame(schedule_frame),
    relief="flat"
)
edit_conf_button_8.place(
    x=14.0,
    y=496.0,
    width=258.0,
    height=58.0
)

edit_conf_button_image_hover_8 = PhotoImage(
    file=relative_to_assets("button_hover_8.png"))


def edit_conf_button_8_hover(e):
    edit_conf_button_8.config(
        image=edit_conf_button_image_hover_8
    )


def edit_conf_button_8_leave(e):
    edit_conf_button_8.config(
        image=edit_conf_button_image_8
    )


edit_conf_button_8.bind('<Enter>', edit_conf_button_8_hover)
edit_conf_button_8.bind('<Leave>', edit_conf_button_8_leave)

# documentation link button
edit_conf_button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png"))
edit_conf_button_9 = Button(
    edit_config_frame,
    image=edit_conf_button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
edit_conf_button_9.place(
    x=24.0,
    y=129.0,
    width=248.0,
    height=44.0
)

edit_conf_button_image_hover_9 = PhotoImage(
    file=relative_to_assets("button_hover_9.png"))


def edit_conf_button_9_hover(e):
    edit_conf_button_9.config(
        image=edit_conf_button_image_hover_9
    )


def edit_conf_button_9_leave(e):
    edit_conf_button_9.config(
        image=edit_conf_button_image_9
    )


edit_conf_button_9.bind('<Enter>', edit_conf_button_9_hover)
edit_conf_button_9.bind('<Leave>', edit_conf_button_9_leave)

edit_conf_button_image_10 = PhotoImage(
    file=relative_to_assets("button_10.png"))
edit_conf_button_10 = Button(
    edit_config_frame,
    image=edit_conf_button_image_10,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
edit_conf_button_10.place(
    x=24.0,
    y=663.0,
    width=215.80738830566406,
    height=180.27777099609375
)

# Apply Tooltip to edit_conf_button_10
tooltip = ToolTip(edit_conf_button_10, "Click to view more tips in our documentation")
edit_conf_button_10.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_10.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_canvas.create_text(
    37.0,
    78.0,
    anchor="nw",
    text="Navigation",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

edit_conf_canvas.create_text(
    12.0,
    855.0,
    anchor="nw",
    text="© 2024 MedusaGuard. All Rights Reserved",
    fill="#FFFFFF",
    font=("Inter", 11 * -1)
)

edit_conf_canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    41.0,
    fill="#6A1B9A",
    outline="")

edit_conf_canvas.create_text(
    75.0,
    11.0,
    anchor="nw",
    text="Configuration Editor\n",
    fill="#FFFFFF",
    font=("Inter Bold", 18 * -1)
)

edit_conf_button_image_11 = PhotoImage(
    file=relative_to_assets("button_11.png"))
edit_conf_button_11 = Button(
    edit_config_frame,
    image=edit_conf_button_image_11,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
edit_conf_button_11.place(
    x=902.0,
    y=0.0,
    width=76.0,
    height=41.0
)

# Apply Tooltip to edit_conf_button_11
tooltip = ToolTip(edit_conf_button_11, "Click to view our documentation")
edit_conf_button_11.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_11.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_12 = PhotoImage(
    file=relative_to_assets("button_12.png"))
edit_conf_button_12 = Button(
    edit_config_frame,
    image=edit_conf_button_image_12,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_12.place(
    x=24.0,
    y=0.0,
    width=50.0,
    height=41.0
)

edit_conf_button_image_hover_12 = PhotoImage(
    file=relative_to_assets("button_hover_11.png"))


def edit_conf_button_12_hover(e):
    edit_conf_button_12.config(
        image=edit_conf_button_image_hover_12
    )


def edit_conf_button_12_leave(e):
    edit_conf_button_12.config(
        image=edit_conf_button_image_12
    )


edit_conf_button_12.bind('<Enter>', edit_conf_button_12_hover)
edit_conf_button_12.bind('<Leave>', edit_conf_button_12_leave)

edit_conf_button_image_13 = PhotoImage(
    file=relative_to_assets("button_13.png"))
edit_conf_button_13 = Button(
    edit_config_frame,
    image=edit_conf_button_image_13,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: show_frame(dashboard_frame),  # Navigate to page2_frame
    relief="flat"
)
edit_conf_button_13.place(
    x=24.0,
    y=98.0,
    width=248.0,
    height=39.0
)

edit_conf_button_image_hover_13 = PhotoImage(
    file=relative_to_assets("button_hover_12.png"))


def edit_conf_button_13_hover(e):
    edit_conf_button_13.config(
        image=edit_conf_button_image_hover_13
    )


def edit_conf_button_13_leave(e):
    edit_conf_button_13.config(
        image=edit_conf_button_image_13
    )


edit_conf_button_13.bind('<Enter>', edit_conf_button_13_hover)
edit_conf_button_13.bind('<Leave>', edit_conf_button_13_leave)

edit_conf_button_image_14 = PhotoImage(
    file=relative_to_assets("button_14.png"))
edit_conf_button_14 = Button(
    edit_config_frame,
    image=edit_conf_button_image_14,
    borderwidth=0,
    highlightthickness=0,
    command=clear_entries,
    relief="flat"
)
edit_conf_button_14.place(
    x=415.1180419921875,
    y=501.91668701171875,
    width=118.31910705566406,
    height=57.36111068725586
)

edit_conf_button_image_hover_14 = PhotoImage(
    file=relative_to_assets("button_hover_13.png"))


def edit_conf_button_14_hover(e):
    edit_conf_button_14.config(
        image=edit_conf_button_image_hover_14
    )


def edit_conf_button_14_leave(e):
    edit_conf_button_14.config(
        image=edit_conf_button_image_14
    )


edit_conf_button_14.bind('<Enter>', edit_conf_button_14_hover)
edit_conf_button_14.bind('<Leave>', edit_conf_button_14_leave)

edit_conf_button_image_15 = PhotoImage(
    file=relative_to_assets("button_15.png"))
edit_conf_button_15 = Button(
    edit_config_frame,
    image=edit_conf_button_image_15,
    borderwidth=0,
    highlightthickness=0,
    command=save_to_config,
    relief="flat"
)
edit_conf_button_15.place(
    x=295.965576171875,
    y=501.91668701171875,
    width=123.31851196289062,
    height=57.36111068725586
)

edit_conf_button_image_hover_15 = PhotoImage(
    file=relative_to_assets("button_hover_14.png"))


def edit_conf_button_15_hover(e):
    edit_conf_button_15.config(
        image=edit_conf_button_image_hover_15
    )


def edit_conf_button_15_leave(e):
    edit_conf_button_15.config(
        image=edit_conf_button_image_15
    )


edit_conf_button_15.bind('<Enter>', edit_conf_button_15_hover)
edit_conf_button_15.bind('<Leave>', edit_conf_button_15_leave)

edit_conf_button_image_16 = PhotoImage(
    file=relative_to_assets("button_16.png"))
edit_conf_button_16 = Button(
    edit_config_frame,
    image=edit_conf_button_image_16,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_16.place(
    x=296.0,
    y=561.74951171875,
    width=682.0,
    height=315.5204162597656
)

edit_conf_button_image_17 = PhotoImage(
    file=relative_to_assets("button_17.png"))
edit_conf_button_17 = Button(
    edit_config_frame,
    image=edit_conf_button_image_17,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_17.place(
    x=296.0,
    y=46.0,
    width=682.0,
    height=462.0
)

edit_conf_button_image_18 = PhotoImage(
    file=relative_to_assets("button_18.png"))
edit_conf_button_18 = Button(
    edit_config_frame,
    image=edit_conf_button_image_18,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_18.place(
    x=664.0,
    y=338.0,
    width=284.0,
    height=76.0
)

edit_conf_scanner_image_1 = PhotoImage(
    file=relative_to_assets("entry_1.png"))
edit_conf_scanner_bg_1 = edit_conf_canvas.create_image(
    804.0,
    382.5,
    image=edit_conf_scanner_image_1
)
edit_conf_scanner = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_scanner.place(
    x=677.0,
    y=374.0,
    width=254.0,
    height=15.0
)
add_placeholder(edit_conf_scanner, "Enter the scanner ID here")

edit_conf_button_image_19 = PhotoImage(
    file=relative_to_assets("button_19.png"))
edit_conf_button_19 = Button(
    edit_config_frame,
    image=edit_conf_button_image_19,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_19.place(
    x=664.0,
    y=260.0,
    width=284.0,
    height=76.0
)

edit_conf_scan_config_image_2 = PhotoImage(
    file=relative_to_assets("entry_2.png"))
edit_conf_scan_config_bg_2 = edit_conf_canvas.create_image(
    804.0,
    307.5,
    image=edit_conf_scan_config_image_2
)
edit_conf_scan_config = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_scan_config.place(
    x=677.0,
    y=299.0,
    width=254.0,
    height=15.0
)
add_placeholder(edit_conf_scan_config, "Enter the scan config ID here")

edit_conf_button_image_20 = PhotoImage(
    file=relative_to_assets("button_20.png"))
edit_conf_button_20 = Button(
    edit_config_frame,
    image=edit_conf_button_image_20,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_20.place(
    x=664.0,
    y=185.0,
    width=284.0,
    height=76.0
)

edit_conf_task_name_image_3 = PhotoImage(
    file=relative_to_assets("entry_3.png"))
edit_conf_task_name_bg_3 = edit_conf_canvas.create_image(
    804.0,
    230.5,
    image=edit_conf_task_name_image_3
)
edit_conf_task_name = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_task_name.place(
    x=677.0,
    y=222.0,
    width=254.0,
    height=15.0
)
add_placeholder(edit_conf_task_name, "Enter your task name here")

edit_conf_button_image_21 = PhotoImage(
    file=relative_to_assets("button_21.png"))
edit_conf_button_21 = Button(
    edit_config_frame,
    image=edit_conf_button_image_21,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_21.place(
    x=664.0,
    y=107.0,
    width=284.0,
    height=76.0
)

edit_conf_port_list_name_image_4 = PhotoImage(
    file=relative_to_assets("entry_4.png"))
edit_conf_port_list_name_bg_4 = edit_conf_canvas.create_image(
    804.0,
    153.5,
    image=edit_conf_port_list_name_image_4
)
edit_conf_port_list_name = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_port_list_name.place(
    x=677.0,
    y=145.0,
    width=254.0,
    height=15.0
)
add_placeholder(edit_conf_port_list_name, "Enter the port list ID here")

edit_conf_button_image_22 = PhotoImage(
    file=relative_to_assets("button_22.png"))
edit_conf_button_22 = Button(
    edit_config_frame,
    image=edit_conf_button_image_22,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_22.place(
    x=326.0,
    y=412.0,
    width=284.0,
    height=76.0
)

edit_conf_target_ip_image_5 = PhotoImage(
    file=relative_to_assets("entry_5.png"))
edit_conf_target_ipbg_5 = edit_conf_canvas.create_image(
    462.0,
    455.5,
    image=edit_conf_target_ip_image_5
)
edit_conf_target_ip = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_target_ip.place(
    x=337.0,
    y=447.0,
    width=250.0,
    height=15.0
)
add_placeholder(edit_conf_target_ip, "Enter the target IP here")

edit_conf_button_image_23 = PhotoImage(
    file=relative_to_assets("button_23.png"))
edit_conf_button_23 = Button(
    edit_config_frame,
    image=edit_conf_button_image_23,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_23.place(
    x=326.0,
    y=340.0,
    width=284.0,
    height=76.0
)

edit_conf_target_name_image_6 = PhotoImage(
    file=relative_to_assets("entry_6.png"))
edit_conf_target_name_bg_6 = edit_conf_canvas.create_image(
    462.0,
    382.5,
    image=edit_conf_target_name_image_6
)
edit_conf_target_name = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_target_name.place(
    x=337.0,
    y=374.0,
    width=250.0,
    height=15.0
)
add_placeholder(edit_conf_target_name, "Enter your target name here")

edit_conf_button_image_24 = PhotoImage(
    file=relative_to_assets("button_24.png"))
edit_conf_button_24 = Button(
    edit_config_frame,
    image=edit_conf_button_image_24,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_24.place(
    x=324.0,
    y=191.0,
    width=284.0,
    height=69.0
)

edit_conf_username_image_7 = PhotoImage(
    file=relative_to_assets("entry_7.png"))
edit_conf_username_bg_7 = edit_conf_canvas.create_image(
    462.0,
    230.5,
    image=edit_conf_username_image_7
)
edit_conf_username = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_username.place(
    x=337.0,
    y=222.0,
    width=250.0,
    height=15.0
)
add_placeholder(edit_conf_username, "Enter your greenbone username here")

edit_conf_button_image_25 = PhotoImage(
    file=relative_to_assets("button_25.png"))
edit_conf_button_25 = Button(
    edit_config_frame,
    image=edit_conf_button_image_25,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_25.place(
    x=324.0,
    y=265.0,
    width=284.0,
    height=69.0
)

edit_conf_password_image_8 = PhotoImage(
    file=relative_to_assets("entry_8.png"))
edit_conf_password_bg_8 = edit_conf_canvas.create_image(
    462.0,
    306.5,
    image=edit_conf_password_image_8
)
edit_conf_password = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_password.place(
    x=337.0,
    y=298.0,
    width=250.0,
    height=15.0
)
add_placeholder(edit_conf_password, "Enter your password here")

edit_conf_button_image_26 = PhotoImage(
    file=relative_to_assets("button_26.png"))
edit_conf_button_26 = Button(
    edit_config_frame,
    image=edit_conf_button_image_26,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_26.place(
    x=326.0,
    y=108.0,
    width=284.0,
    height=76.0
)

edit_conf_path_image_9 = PhotoImage(
    file=relative_to_assets("entry_9.png"))
edit_conf_path_bg_9 = edit_conf_canvas.create_image(
    462.0,
    154.5,
    image=edit_conf_path_image_9
)
edit_conf_path = Entry(
    edit_config_frame,
    bd=0,
    bg="#313237",
    fg="#FFFFFF",
    highlightthickness=0,
    insertbackground="#FFFFFF"
)
edit_conf_path.place(
    x=337.0,
    y=146.0,
    width=250.0,
    height=15.0
)
add_placeholder(edit_conf_path, "Enter the socket path here")

edit_conf_button_image_27 = PhotoImage(
    file=relative_to_assets("button_27.png"))
edit_conf_button_27 = Button(
    edit_config_frame,
    image=edit_conf_button_image_27,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_27.place(
    x=437.0,
    y=418.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_target_ip
tooltip = ToolTip(edit_conf_button_27,
                  """Provide the IP address you wish to scan or 
target list, by default it is set to targets.txt""")
edit_conf_button_27.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_27.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_28 = PhotoImage(
    file=relative_to_assets("button_28.png"))
edit_conf_button_28 = Button(
    edit_config_frame,
    image=edit_conf_button_image_28,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_28.place(
    x=410.0,
    y=345.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_target_name
tooltip = ToolTip(edit_conf_button_28,
                  """Provide the name of the target""")
edit_conf_button_28.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_28.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_29 = PhotoImage(
    file=relative_to_assets("button_29.png"))
edit_conf_button_29 = Button(
    edit_config_frame,
    image=edit_conf_button_image_29,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_29.place(
    x=458.0,
    y=269.0,
    width=13.0,
    height=13.0
)

edit_conf_button_image_hover_29 = PhotoImage(
    file=relative_to_assets("button_hover_17.png"))


def edit_conf_button_29_hover(e):
    edit_conf_button_29.config(
        image=edit_conf_button_image_hover_29
    )


def edit_conf_button_29_leave(e):
    edit_conf_button_29.config(
        image=edit_conf_button_image_29
    )


edit_conf_button_29.bind('<Enter>', edit_conf_button_29_hover)
edit_conf_button_29.bind('<Leave>', edit_conf_button_29_leave)

# Apply Tooltip to edit_conf_password
tooltip = ToolTip(edit_conf_button_29,
                  """Enter your password for greenbone""")
edit_conf_button_29.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_29.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_30 = PhotoImage(
    file=relative_to_assets("button_30.png"))
edit_conf_button_30 = Button(
    edit_config_frame,
    image=edit_conf_button_image_30,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_30.place(
    x=460.0,
    y=193.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_username
tooltip = ToolTip(edit_conf_button_30,
                  """Enter your username for greenbone""")
edit_conf_button_30.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_30.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_31 = PhotoImage(
    file=relative_to_assets("button_31.png"))
edit_conf_button_31 = Button(
    edit_config_frame,
    image=edit_conf_button_image_31,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_31.place(
    x=404.0,
    y=117.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_path
tooltip = ToolTip(edit_conf_button_31,
                  """Specify the socket path for communication. 
By default this is set to /run/gvmd/gvmd.sock.""")
edit_conf_button_31.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_31.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_32 = PhotoImage(
    file=relative_to_assets("button_32.png"))
edit_conf_button_32 = Button(
    edit_config_frame,
    image=edit_conf_button_image_32,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_32.place(
    x=776.0,
    y=116.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_port_list
tooltip = ToolTip(edit_conf_button_32,
                  """Enter the port List ID to be used for scanning. 
For more information look below or check our documentation.""")
edit_conf_button_32.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_32.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_33 = PhotoImage(
    file=relative_to_assets("button_33.png"))
edit_conf_button_33 = Button(
    edit_config_frame,
    image=edit_conf_button_image_33,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_33.place(
    x=740.0,
    y=193.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_task_name
tooltip = ToolTip(edit_conf_button_33,
                  """Specify the name of the task for this scan.""")
edit_conf_button_33.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_33.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_34 = PhotoImage(
    file=relative_to_assets("button_34.png"))
edit_conf_button_34 = Button(
    edit_config_frame,
    image=edit_conf_button_image_34,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_34.place(
    x=760.0,
    y=269.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_scan_config
tooltip = ToolTip(edit_conf_button_34,
                  """Enter the scan config ID to be used for scanning. 
For more information look below or check our documentation.""")
edit_conf_button_34.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_34.bind("<Leave>", tooltip.hide_tooltip)

edit_conf_button_image_35 = PhotoImage(
    file=relative_to_assets("button_35.png"))
edit_conf_button_35 = Button(
    edit_config_frame,
    image=edit_conf_button_image_35,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
edit_conf_button_35.place(
    x=738.0,
    y=345.0,
    width=13.0,
    height=13.0
)

# Apply Tooltip to edit_conf_scanner
tooltip = ToolTip(edit_conf_button_35,
                  """Enter the scanner ID to be used for scanning. 
For more information look below or check our documentation.""")
edit_conf_button_35.bind("<Enter>", tooltip.show_tooltip)
edit_conf_button_35.bind("<Leave>", tooltip.hide_tooltip)

# --------------------------------------------
# Variables and UI Elements for Dashboard Page
# --------------------------------------------
dashboard_canvas = Canvas(
    dashboard_frame,
    bg="#FFFFFF",
    height=885,
    width=1000,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

dashboard_canvas.place(x=0, y=0)
dashboard_canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    885.0,
    fill="#121212",
    outline="")

# Load the initial image for dashboard_button_1
dashboard_button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png", 1))

# Load images for changing dashboard_button_1
start_scan_log_image = PhotoImage(file=relative_to_assets("start_scan_log.png", 1))
start_scan_log_image2 = PhotoImage(file=relative_to_assets("start_scan_log2.png", 1))
start_scan_log_image3 = PhotoImage(file=relative_to_assets("start_scan_log3.png", 1))
start_scan_log_image4 = PhotoImage(file=relative_to_assets("start_scan_log4.png", 1))
stop_scan_log_image = PhotoImage(file=relative_to_assets("stop_scan_log.png", 1))
stop_scan_log_image = PhotoImage(file=relative_to_assets("stop_scan_log.png", 1))


start_scan_log_images = [
    start_scan_log_image2,
    start_scan_log_image3,
    start_scan_log_image4,
]

dashboard_button_1 = Button(
    dashboard_frame,
    image=dashboard_button_image_1,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
dashboard_button_1.place(
    x=295.0,
    y=52.0,
    width=682.0,
    height=386.0
)

dashboard_output_text = Text(
    dashboard_frame,
    bg="#1B1C21",
    fg="#FFFFFF",
    font=("Inter", 10),
    wrap="word",
    state='disabled',
    bd=0,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
dashboard_output_text.place(
    x=326.0,
    y=110.0,
    width=616.0,
    height=285
)

# Add a Scrollbar to the Text widget, positioned at the far right
output_scrollbar = Scrollbar(
    dashboard_frame,
    command=dashboard_output_text.yview,
    orient='vertical',
    borderwidth=0,
    highlightthickness=0,
    relief='flat',
    bg="#313237",
    activebackground="#313237",
    troughcolor="#1B1C21"
)
output_scrollbar.place(
    x=315.0 + 614.0,  # 932.0 pixels
    y=110.0,
    width=15.0,         # Explicit scrollbar width
    height=285.0
)

# Link the Scrollbar to the Text widget
dashboard_output_text.configure(yscrollcommand=output_scrollbar.set)

# Configure the spacing tag to adjust line spacing only
dashboard_output_text.tag_configure('spacing', spacing2=5)

# Function to insert text into the Text widget
def insert_initial(line):
    dashboard_output_text.config(state='normal')
    dashboard_output_text.insert('end', line, 'spacing')
    dashboard_output_text.see('end')
    dashboard_output_text.config(state='disabled')

# Example usage: Insert some text
insert_initial(
"""This window will populate with logs once you start a scan.
"""
)

dashboard_canvas.create_rectangle(
    0.0,
    0.0,
    272.0,
    885.0,
    fill="#1B1C21",
    outline="")

# Tips feed button
dashboard_button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png", 1))
dashboard_button_3 = Button(
    dashboard_frame,
    image=dashboard_button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
dashboard_button_3.place(
    x=24.0,
    y=663.0,
    width=215.80738830566406,
    height=180.27777099609375
)

dashboard_canvas.create_text(
    37.0,
    78.0,
    anchor="nw",
    text="Folders",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

dashboard_canvas.create_text(
    37.0,
    296.0,
    anchor="nw",
    text="Config",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

dashboard_canvas.create_text(
    12.0,
    855.0,
    anchor="nw",
    text="© 2024 MedusaGuard. All Rights Reserved",
    fill="#FFFFFF",
    font=("Inter", 11 * -1)
)

# Report Summary Background Rectangle
dashboard_button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png", 1))
dashboard_button_4 = Button(
    dashboard_frame,
    image=dashboard_button_image_4,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
dashboard_button_4.place(
    x=289.133056640625,
    y=472.0,
    width=694.083251953125,
    height=407.2638854980469
)

# Report Summary Section
dashboard_button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png", 1))
dashboard_button_5 = Button(
    dashboard_frame,
    image=dashboard_button_image_5,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
dashboard_button_5.place(
    x=318.0,
    y=528.0,
    width=634.0,
    height=341.0
)

dashboard_canvas.create_rectangle(
    0.0,
    0.0,
    1000.0,
    41.0,
    fill="#6A1B9A",
    outline="")

dashboard_canvas.create_text(
    206.0,
    17.0,
    anchor="nw",
    text="Automated Vulnerability Scanning and Exploitation Tool",
    fill="#FFFFFF",
    font=("Inter BoldItalic", 12 * -1)
)

dashboard_canvas.create_text(
    75.0,
    11.0,
    anchor="nw",
    text="MedusaGuard ",
    fill="#FFFFFF",
    font=("Inter Bold", 18 * -1)
)

dashboard_canvas.create_text(
    328.0,
    504.0,
    anchor="nw",
    text="Report Summary",
    fill="#FFFFFF",
    font=("Inter Bold", 16 * -1)
)

# Documentation button (v1.0)
dashboard_button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png", 1))
dashboard_button_6 = Button(
    dashboard_frame,
    image=dashboard_button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=open_supplied_link,
    relief="flat"
)
dashboard_button_6.place(
    x=902.0,
    y=0.0,
    width=76.0,
    height=41.0
)

dashboard_button_image_hover_6 = PhotoImage(
    file=relative_to_assets("button_hover_1.png", 1))


def dashboard_button_6_hover(e):
    dashboard_button_6.config(
        image=dashboard_button_image_hover_6
    )


def dashboard_button_6_leave(e):
    dashboard_button_6.config(
        image=dashboard_button_image_6
    )


dashboard_button_6.bind('<Enter>', dashboard_button_6_hover)
dashboard_button_6.bind('<Leave>', dashboard_button_6_leave)

dashboard_button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png", 1))
dashboard_button_7 = Button(
    dashboard_frame,
    image=dashboard_button_image_7,
    borderwidth=0,
    highlightthickness=0,
    relief="flat"
)
dashboard_button_7.place(
    x=24.0,
    y=0.0,
    width=50.0,
    height=41.0
)

dashboard_button_image_hover_7 = PhotoImage(
    file=relative_to_assets("button_hover_2.png", 1))


def dashboard_button_7_hover(e):
    dashboard_button_7.config(
        image=dashboard_button_image_hover_7
    )


def dashboard_button_7_leave(e):
    dashboard_button_7.config(
        image=dashboard_button_image_7
    )


dashboard_button_7.bind('<Enter>', dashboard_button_7_hover)
dashboard_button_7.bind('<Leave>', dashboard_button_7_leave)

dashboard_button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png", 1))
dashboard_button_8 = Button(
    dashboard_frame,
    image=dashboard_button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('custom_reports'),
    relief="flat"
)
dashboard_button_8.place(
    x=24.0,
    y=93.0,
    width=248.0,
    height=44.0
)

dashboard_button_image_hover_8 = PhotoImage(
    file=relative_to_assets("button_hover_3.png", 1))


def dashboard_button_8_hover(e):
    dashboard_button_8.config(
        image=dashboard_button_image_hover_8
    )


def dashboard_button_8_leave(e):
    dashboard_button_8.config(
        image=dashboard_button_image_8
    )


dashboard_button_8.bind('<Enter>', dashboard_button_8_hover)
dashboard_button_8.bind('<Leave>', dashboard_button_8_leave)

dashboard_button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png", 1))
dashboard_button_9 = Button(
    dashboard_frame,
    image=dashboard_button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('openvas_reports'),
    relief="flat"
)
dashboard_button_9.place(
    x=19.0,
    y=124.0,
    width=246.0,
    height=46.0
)

dashboard_button_image_hover_9 = PhotoImage(
    file=relative_to_assets("button_hover_4.png", 1))


def dashboard_button_9_hover(e):
    dashboard_button_9.config(
        image=dashboard_button_image_hover_9
    )


def dashboard_button_9_leave(e):
    dashboard_button_9.config(
        image=dashboard_button_image_9
    )


dashboard_button_9.bind('<Enter>', dashboard_button_9_hover)
dashboard_button_9.bind('<Leave>', dashboard_button_9_leave)

dashboard_button_image_10 = PhotoImage(
    file=relative_to_assets("button_10.png", 1))
dashboard_button_10 = Button(
    dashboard_frame,
    image=dashboard_button_image_10,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nuclei_results'),
    relief="flat"
)
dashboard_button_10.place(
    x=24.497802734375,
    y=159.791748046875,
    width=225.80621337890625,
    height=37.6944465637207
)

dashboard_button_image_hover_10 = PhotoImage(
    file=relative_to_assets("button_hover_5.png", 1))


def dashboard_button_10_hover(e):
    dashboard_button_10.config(
        image=dashboard_button_image_hover_10
    )


def dashboard_button_10_leave(e):
    dashboard_button_10.config(
        image=dashboard_button_image_10
    )


dashboard_button_10.bind('<Enter>', dashboard_button_10_hover)
dashboard_button_10.bind('<Leave>', dashboard_button_10_leave)

dashboard_button_image_11 = PhotoImage(
    file=relative_to_assets("button_11.png", 1))
dashboard_button_11 = Button(
    dashboard_frame,
    image=dashboard_button_image_11,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('metasploit_results'),
    relief="flat"
)
dashboard_button_11.place(
    x=19.0,
    y=195.0,
    width=253.0,
    height=43.0
)

dashboard_button_image_hover_11 = PhotoImage(
    file=relative_to_assets("button_hover_6.png", 1))


def dashboard_button_11_hover(e):
    dashboard_button_11.config(
        image=dashboard_button_image_hover_11
    )


def dashboard_button_11_leave(e):
    dashboard_button_11.config(
        image=dashboard_button_image_11
    )


dashboard_button_11.bind('<Enter>', dashboard_button_11_hover)
dashboard_button_11.bind('<Leave>', dashboard_button_11_leave)

dashboard_button_image_12 = PhotoImage(
    file=relative_to_assets("button_12.png", 1))
dashboard_button_12 = Button(
    dashboard_frame,
    image=dashboard_button_image_12,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('nikto_results'),
    relief="flat"
)
dashboard_button_12.place(
    x=19.0,
    y=231.0,
    width=238.0,
    height=50.0
)

dashboard_button_image_hover_12 = PhotoImage(
    file=relative_to_assets("button_hover_7.png", 1))


def dashboard_button_12_hover(e):
    dashboard_button_12.config(
        image=dashboard_button_image_hover_12
    )


def dashboard_button_12_leave(e):
    dashboard_button_12.config(
        image=dashboard_button_image_12
    )


dashboard_button_12.bind('<Enter>', dashboard_button_12_hover)
dashboard_button_12.bind('<Leave>', dashboard_button_12_leave)

dashboard_button_image_13 = PhotoImage(
    file=relative_to_assets("button_13.png", 1))
dashboard_button_13 = Button(
    dashboard_frame,
    image=dashboard_button_image_13,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('config.ini'),
    relief="flat"
)
dashboard_button_13.place(
    x=32.830322265625,
    y=315.4862060546875,
    width=217.47396850585938,
    height=37.6944465637207
)

dashboard_button_image_hover_13 = PhotoImage(
    file=relative_to_assets("button_hover_8.png", 1))


def dashboard_button_13_hover(e):
    dashboard_button_13.config(
        image=dashboard_button_image_hover_13
    )


def dashboard_button_13_leave(e):
    dashboard_button_13.config(
        image=dashboard_button_image_13
    )


dashboard_button_13.bind('<Enter>', dashboard_button_13_hover)
dashboard_button_13.bind('<Leave>', dashboard_button_13_leave)

dashboard_button_image_14 = PhotoImage(
    file=relative_to_assets("button_14.png", 1))
dashboard_button_14 = Button(
    dashboard_frame,
    image=dashboard_button_image_14,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: open_directory('targets.txt'),
    relief="flat"
)
dashboard_button_14.place(
    x=14.4990234375,
    y=350.72216796875,
    width=235.80499267578125,
    height=37.6944465637207
)

dashboard_button_image_hover_14 = PhotoImage(
    file=relative_to_assets("button_hover_9.png", 1))


def dashboard_button_14_hover(e):
    dashboard_button_14.config(
        image=dashboard_button_image_hover_14
    )


def dashboard_button_14_leave(e):
    dashboard_button_14.config(
        image=dashboard_button_image_14
    )


dashboard_button_14.bind('<Enter>', dashboard_button_14_hover)
dashboard_button_14.bind('<Leave>', dashboard_button_14_leave)

dashboard_button_image_15 = PhotoImage(
    file=relative_to_assets("button_15.png", 1))
dashboard_button_15 = Button(
    dashboard_frame,
    image=dashboard_button_image_15,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: show_frame(schedule_frame),
    relief="flat"
)
dashboard_button_15.place(
    x=14.0,
    y=380.0,
    width=258.0,
    height=58.0
)

dashboard_button_image_hover_15 = PhotoImage(
    file=relative_to_assets("button_hover_10.png", 1))


def dashboard_button_15_hover(e):
    dashboard_button_15.config(
        image=dashboard_button_image_hover_15
    )


def dashboard_button_15_leave(e):
    dashboard_button_15.config(
        image=dashboard_button_image_15
    )


dashboard_button_15.bind('<Enter>', dashboard_button_15_hover)
dashboard_button_15.bind('<Leave>', dashboard_button_15_leave)

dashboard_button_image_16 = PhotoImage(
    file=relative_to_assets("button_16.png", 1))
dashboard_button_16 = Button(
    dashboard_frame,
    image=dashboard_button_image_16,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: show_frame(edit_config_frame),  # Navigate back to main_frame
    relief="flat"
)
dashboard_button_16.place(
    x=847.0,
    y=418.0,
    width=151.0,
    height=61.0
)

dashboard_button_image_hover_16 = PhotoImage(
    file=relative_to_assets("button_hover_11.png", 1))


def dashboard_button_16_hover(e):
    dashboard_button_16.config(
        image=dashboard_button_image_hover_16
    )


def dashboard_button_16_leave(e):
    dashboard_button_16.config(
        image=dashboard_button_image_16
    )


dashboard_button_16.bind('<Enter>', dashboard_button_16_hover)
dashboard_button_16.bind('<Leave>', dashboard_button_16_leave)

# Stop scan button
dashboard_button_image_17 = PhotoImage(
    file=relative_to_assets("button_17.png", 1))
dashboard_button_17 = Button(
    dashboard_frame,
    image=dashboard_button_image_17,
    borderwidth=0,
    highlightthickness=0,
    command=stop_scan,
    relief="flat"
)
dashboard_button_17.place(
    x=414.1180419921875,
    y=417.91668701171875,
    width=118.31910705566406,
    height=57.36111068725586
)

dashboard_button_image_hover_17 = PhotoImage(
    file=relative_to_assets("button_hover_12.png", 1))


def dashboard_button_17_hover(e):
    dashboard_button_17.config(
        image=dashboard_button_image_hover_17
    )


def dashboard_button_17_leave(e):
    dashboard_button_17.config(
        image=dashboard_button_image_17
    )


dashboard_button_17.bind('<Enter>', dashboard_button_17_hover)
dashboard_button_17.bind('<Leave>', dashboard_button_17_leave)

# Start scan button
dashboard_button_image_18 = PhotoImage(
    file=relative_to_assets("button_18.png", 1))
dashboard_button_18 = Button(
    dashboard_frame,
    image=dashboard_button_image_18,
    borderwidth=0,
    highlightthickness=0,
    command=start_scan,
    relief="flat"
)
dashboard_button_18.place(
    x=294.965576171875,
    y=417.91668701171875,
    width=123.31851196289062,
    height=57.36111068725586
)

dashboard_button_image_hover_18 = PhotoImage(
    file=relative_to_assets("button_hover_13.png", 1))


def dashboard_button_18_hover(e):
    dashboard_button_18.config(
        image=dashboard_button_image_hover_18
    )


def dashboard_button_18_leave(e):
    dashboard_button_18.config(
        image=dashboard_button_image_18
    )


# Vuln graph placeholder
vuln_graph_placeholder = PhotoImage(file=relative_to_assets("vuln_graph_placeholder.png", 1))
vuln_image_label = Label(
    dashboard_frame,
    image=vuln_graph_placeholder,
    borderwidth=0,
    bg="#313237",
    highlightthickness=0
)
vuln_image_label.place(x=350, y=550)

# Exploit graph placeholder
exploit_graph_placeholder = PhotoImage(file=relative_to_assets("exploit_graph_placeholder.png", 1))
exploit_image_label = Label(
    dashboard_frame,
    image=exploit_graph_placeholder,
    borderwidth=0,
    bg="#313237",
    highlightthickness=0)
exploit_image_label.place(x=660, y=550)

# Define the text to display in the two Text widgets
vuln_content = """



                              Awaiting Results



"""

exploit_content = """



                              Awaiting Results



"""

vuln_scan_results_text_content = vuln_content
exploit_results_text_content = exploit_content

vuln_scan_results_label = Label(
    dashboard_frame,
    text=vuln_scan_results_text_content,
    bg="#313237",
    fg="#FFFFFF",
    font=("Inter Bold", 8),
    wraplength=280,  # Set wraplength to the width of the label
    anchor="w",      # Left-align the text within the label
    justify="left"   # Justify the text to the left when wrapped
)
vuln_scan_results_label.place(
    x=335.0,
    y=750.0,
    width=280.0,
    height=90.0
)

exploit_results_text = Label(
    dashboard_frame,
    text=exploit_results_text_content,
    bg="#313237",
    fg="#FFFFFF",
    font=("Inter Bold", 8),
    wraplength=280,  # Set wraplength to the width of the label
    anchor="w",      # Left-align the text within the label
    justify="left"   # Justify the text to the left when wrapped
)
exploit_results_text.place(
    x=650.0,
    y=750.0,
    width=280.0,
    height=90.0
)

# Running the scheduler in a background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

dashboard_button_18.bind('<Enter>', dashboard_button_18_hover)
dashboard_button_18.bind('<Leave>', dashboard_button_18_leave)

window.resizable(False, False)  # Prevent the window from being resized
window.after(100, process_output_queue)  # Start processing the output queue
window.mainloop()  # Start the Tkinter event loop
