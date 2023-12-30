import tkinter as tk
from tkinter import ttk
import subprocess
from datetime import datetime
import atexit
import platform
import ctypes
import version

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class OperatingSystemChecker:
    def __init__(self):
        self.os_name = platform.system()
        self.os_version = platform.version()
        self.caffeinate_process = None
        self.inhibit_process = None

    def get_os_info(self):
        return f"{self.os_name} - ({self.os_version})"

    def is_windows(self):
        return self.os_name == "Windows"

    def is_mac(self):
        return self.os_name == "MAC"

    def is_linux(self):
        return self.os_name == "Linux"

    def prevent_sleep_windows(self):
        if self.is_windows():
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED)

    def allow_sleep_windows(self):
        if self.is_windows():
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    def prevent_sleep_mac(self):
        self.caffeinate_process = subprocess.Popen(["caffeinate"])

    def allow_sleep_mac(self):
        if self.caffeinate_process:
            self.caffeinate_process.terminate()
            self.caffeinate_process = None

    def prevent_sleep_linux(self):
        self.inhibit_process = subprocess.Popen(["systemd-inhibit", "--what=idle", "--who=TimerApp", "--why=Preventing sleep", "cat"])

    def allow_sleep_linux(self):
        if self.inhibit_process:
            self.inhibit_process.terminate()
            self.inhibit_process = None
    def prevent_sleep(self):
        if self.is_windows():
            self.prevent_sleep_windows()
        elif self.is_mac():
            self.prevent_sleep_mac()
        elif self.is_linux():
            self.prevent_sleep_linux()

    def allow_sleep(self):
        if self.is_windows():
            self.allow_sleep_windows()
        elif self.is_mac():
            self.allow_sleep_mac()
        elif self.is_linux():
            self.allow_sleep_linux()


class TimerApp:
    def __init__(self, root):
        self.root = root
        self.active = False
        self.TIMER = 0
        self.COUNTDOWN = 0
        self.os_checker = OperatingSystemChecker()
        self.create_widgets()
        self.configure_gui()
        atexit.register(self.exit_handler)
        self.log_text.insert(tk.END, f"Welcome!\nYou are running: {self.os_checker.get_os_info()}\n---------------\n"
                                     f"Version: {version.__version__}\n---------------\n")

    def start(self):  # FOR DEBUGGING: GUI Event Loop
        self.update_status()
        self.root.mainloop()

    def create_widgets(self):
        self.create_status_widgets()
        self.create_log_widgets()
        self.create_timer_widgets()
        self.create_control_widgets()

    def configure_gui(self):
        self.root.geometry("600x400")
        self.root.title("Display Sleep Preventer")
        self.root.configure(bg='#C0C0C0')
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

    def create_status_widgets(self):
        status_label = tk.Label(self.root, text="State:", bg='#C0C0C0', font=('TkDefaultFont', 10, 'bold'))
        status_label.grid(row=0, column=0, sticky='nsew', padx=10)

        status_frame = tk.Frame(self.root, bg='#C0C0C0')
        status_frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=1)

        self.status_text = tk.Text(status_frame, height=1, width=4, bg='#C0C0C0', bd=0, font=('TkDefaultFont', 10, 'bold'),
                                   relief='flat')
        self.status_text.tag_configure('ON', foreground='green')
        self.status_text.tag_configure('OFF', foreground='red')
        self.status_text.pack(expand=True)

        toggle_button = ttk.Button(self.root, text="Toggle", command=self.toggle_activity, width=20)
        toggle_button.grid(row=2, column=0, sticky='nsew', padx=20)

    def create_log_widgets(self):
        log_frame = tk.Frame(self.root, bg='#C0C0C0', relief='sunken', bd=2)
        log_frame.grid(row=0, column=1, rowspan=8, sticky='nsew', padx=20, pady=20)
        log_frame.config(width=200, height=100)

        self.log_text = tk.Text(log_frame, width=20, height=10, font=('TkDefaultFont', 10), relief='sunken', bd=2)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text['yscrollcommand'] = scrollbar.set

    def create_timer_widgets(self):
        timer_frame = tk.Frame(self.root)
        timer_frame.grid(row=5, column=0, padx=20, pady=10)
        self.timer_label = tk.Label(timer_frame, text=f"Timer: {self.format_time(self.TIMER)}", bg='#C0C0C0', font=('TkDefaultFont', 10))
        self.timer_label.grid(row=0, column=0, sticky="nsew", pady=10)

    def create_control_widgets(self):
        self.spinbox_var = tk.StringVar()
        self.spinbox_var.set(str(self.TIMER))
        spinbox = ttk.Spinbox(self.root, from_=1, to=72, textvariable=self.spinbox_var, width=5)
        spinbox.grid(row=3, column=0, padx=20, pady=10)

        terminate_button = ttk.Button(self.root, text="Reset", command=self.early_end)
        terminate_button.grid(row=4, column=0, padx=20, pady=10)

    def toggle_activity(self):
        self.active = not self.active
        if int(self.spinbox_var.get()) < 1:
            self.log_text.insert(tk.END, "ERROR: Timer cannot be zero!\n")
        if self.active:
            try:
                self.TIMER = int(self.spinbox_var.get())
            except ValueError:
                self.TIMER = 0
                self.spinbox_var.set("1")

            self.COUNTDOWN = self.TIMER * 3600
            self.os_checker.prevent_sleep()
            self.update_timer()
            self.update_status()
        else:
            self.os_checker.allow_sleep()
            self.active = False
            self.timer_label.config(text="Timer: 00:00:00")
            self.log_text.insert(tk.END, "Timer stopped.\n")
            self.update_status()

    def early_end(self):
        self.COUNTDOWN = 0
        self.active = False
        self.os_checker.allow_sleep()
        self.timer_label.config(text="Timer: 00:00:00")
        self.log_text.insert(tk.END, "Timer reset and stopped early.\n")
        self.update_status()

    def exit_handler(self):
        self.os_checker.allow_sleep()

    def format_time(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    def undo_kernel_state_change(self):
        self.active = False
        self.os_checker.allow_sleep()
        self.log_text.insert(tk.END,"Kernel state back to normal.\n")

    def update_status(self):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert('end', 'ON' if self.active else 'OFF', 'ON' if self.active else 'OFF')
        self.status_text.config(state=tk.DISABLED)
        self.log_status()

    def update_timer(self):
        if self.active and self.COUNTDOWN > 0:
            self.COUNTDOWN -= 1
            self.timer_label.config(text=f"Timer: {self.format_time(self.COUNTDOWN)}")
            self.root.after(1000, self.update_timer)  # Schedule next update
        elif self.COUNTDOWN <= 0:
            self.undo_kernel_state_change()  # Stop the timer when countdown reaches 0

    def log_status(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Active" if self.active else "Inactive"
        self.log_text.insert(tk.END, f"{timestamp} - {status}\n")
        self.log_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    app.start()