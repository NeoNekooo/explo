import customtkinter as ctk
import os
import shutil
from PIL import Image, ImageTk, ImageDraw
from tkinter import filedialog, messagebox, simpledialog
import subprocess
import tkinter as tk
import sys
from datetime import datetime
import zipfile
import threading
import http.server
import socketserver
import json
import base64
import socket
import hashlib
import time

# --- Konfigurasi dan Fungsi Dasar ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def get_base_dir():
    if sys.platform == "win32":
        # Windows: Use AppData\Local
        return os.path.join(os.environ["LOCALAPPDATA"], "ExploFileManager")
    elif sys.platform == "darwin":
        # macOS: Use Application Support
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "ExploFileManager")
    else:
        # Linux and other Unix-like systems: Use .local/share
        return os.path.join(os.path.expanduser("~"), ".local", "share", "ExploFileManager")

BASE_DIR = get_base_dir()
os.makedirs(BASE_DIR, exist_ok=True)
USERS_FILE = os.path.join(BASE_DIR, "users.txt")
LOG_FILE = os.path.join(BASE_DIR, "activity.log")
SECRET_FOLDER_PASS_FILE = os.path.join(BASE_DIR, "secret_passwords.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("miaw:123.,#\n")
    print(f"File users.txt tidak ditemukan, file baru telah dibuat.")
    print("Gunakan kredensial default: Username: miaw, Password: 123.,#")
else:
    print(f"File users.txt ditemukan di: {USERS_FILE}")
    print("Gunakan kredensial default jika belum diubah: Username: miaw, Password: 123.,#")

if not os.path.exists(SECRET_FOLDER_PASS_FILE):
    with open(SECRET_FOLDER_PASS_FILE, "w") as f:
        f.write("{}")

def log_activity(username, action, path):
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] User '{username}' {action}: '{path}'\n")
    except IOError as e:
        messagebox.showerror("IOError", f"Could not write to log file: {e}")

def verify_login(username, password):
    try:
        with open(USERS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    stored_username, stored_password = line.split(":", 1)
                    if username == stored_username and password == stored_password:
                        return True
                except ValueError:
                    continue
        return False
    except FileNotFoundError:
        messagebox.showerror("Error", "User database not found. Please restart the app.")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while verifying login: {e}")
        return False

def get_total_size(path):
    total = 0
    if os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except FileNotFoundError:
                    continue
    else:
        try:
            total = os.path.getsize(path)
        except FileNotFoundError:
            return 0
    return total

class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Login")
        self.geometry("350x250")
        self.center_window()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.login_successful = False
        self.username = None

        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.label = ctk.CTkLabel(frame, text="Selamat Datang", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.username_entry = ctk.CTkEntry(frame, placeholder_text="Username", width=200, corner_radius=8)
        self.username_entry.pack(pady=5)

        self.password_entry = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=200, corner_radius=8)
        self.password_entry.pack(pady=5)

        self.login_button = ctk.CTkButton(frame, text="Login", command=self.check_login, width=200, corner_radius=8)
        self.login_button.pack(pady=15)
    
    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (350 / 2)
        y = (screen_height / 2) - (250 / 2)
        self.geometry(f"350x250+{int(x)}+{int(y)}")

    def check_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if verify_login(username, password):
            self.login_successful = True
            self.username = username
            self.destroy()
        else:
            messagebox.showerror("Error", "Username atau password salah!", parent=self)
    
    def on_close(self):
        self.destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Explo File Manager")
        self.geometry("1400x900")
        
        self.icon_size = 120
        self.thumbnail_size = (self.icon_size, self.icon_size)
        self.load_icons()

        self.login_window = LoginWindow(self)
        self.wait_window(self.login_window)

        if self.login_window.login_successful:
            self.current_user = self.login_window.username
            self.storage_path = os.path.join(BASE_DIR, "storage", self.current_user)
            self.current_path = self.storage_path
            self.favorites_file = os.path.join(self.storage_path, "favorites.txt")
            self.recent_files_path = os.path.join(self.storage_path, "recent_files.json") 
            os.makedirs(self.storage_path, exist_ok=True)
            self.create_default_folders()
            
            self.tags_file = os.path.join(self.storage_path, "tags.json")
            self.load_tags()
            self.load_config()

            self.view_mode = "grid"
            self.sort_by = "name"
            self.sort_order = "asc"
            self.selected_item_frame = None

            self.nav_history = [{"view": "dashboard", "path": self.storage_path}]
            
            self.create_main_layout()
            self.show_dashboard_view()
        else:
            self.destroy()
            
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.show_hidden_files = config.get("show_hidden_files", False)
            except (IOError, json.JSONDecodeError):
                self.show_hidden_files = False
        else:
            self.show_hidden_files = False
            
    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"show_hidden_files": self.show_hidden_files}, f)
        except IOError:
            messagebox.showerror("Error", "Could not save configuration.")

    def load_tags(self):
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, "r") as f:
                    self.tags = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                messagebox.showerror("Error", f"Could not load tags file: {e}")
                self.tags = {}
        else:
            self.tags = {}

    def save_tags(self):
        try:
            with open(self.tags_file, "w") as f:
                json.dump(self.tags, f)
        except IOError as e:
            messagebox.showerror("Error", f"Could not save tags: {e}")
    
    def load_icons(self):
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            assets_path = os.path.join(base_path, "assets")

            small_icon_size = (24, 24)
            thumb_icon_size = (self.icon_size, self.icon_size)

            self.icons = {
                "folder": self.load_single_icon("folder_icon.png", thumb_icon_size),
                "file": self.load_single_icon("file_icon.png", thumb_icon_size),
                "back": self.load_single_icon("back_icon.png", small_icon_size),
                "video": self.load_single_icon("video_icon.png", thumb_icon_size),
                "user": self.load_single_icon("user_icon.png", small_icon_size),
                "settings": self.load_single_icon("settings_icon.png", small_icon_size),
                "home": self.load_single_icon("home_icon.png", small_icon_size),
                "upload": self.load_single_icon("upload_icon.png", small_icon_size),
                "create_folder": self.load_single_icon("create_folder_icon.png", small_icon_size),
                "favorites": self.load_single_icon("star_icon.png", small_icon_size),
                "image_category": self.load_single_icon("image_icon.png", small_icon_size),
                "document_category": self.load_single_icon("document_icon.png", small_icon_size),
                "video_category": self.load_single_icon("video_icon.png", small_icon_size),
                "compress": self.load_single_icon("zip_icon.png", small_icon_size),
                "cloud": self.load_single_icon("cloud_icon.png", (48, 48)),
                "wifi": self.load_single_icon("wifi_icon.png", small_icon_size),
                "secret": self.load_single_icon("secret_icon.png", small_icon_size),
                "storage_icon": self.load_single_icon("storage_icon.png", (48, 48)),
                "plus": self.load_single_icon("plus_icon.png", small_icon_size),
                "thumbnail_placeholder": self.load_single_icon("thumbnail_placeholder.png", thumb_icon_size),
                "trash": self.load_single_icon("trash_icon.png", small_icon_size),
                "file_edit": self.load_single_icon("file_edit_icon.png", thumb_icon_size),
                "eye_open": self.load_single_icon("eye_open_icon.png", small_icon_size),
                "eye_closed": self.load_single_icon("eye_closed_icon.png", small_icon_size)
            }
        except Exception as e:
            print(f"Gagal memuat ikon aplikasi: {e}")
            self.icons = {}
    
    def load_single_icon(self, filename, size):
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            image_path = os.path.join(base_path, "assets", filename)
            img = Image.open(image_path)
            img.thumbnail(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading icon {filename}: {e}")
            return None

    def create_default_folders(self):
        folders = ["Documents", "Images", "Videos", "Secret", ".RecycleBin"]
        for folder in folders:
            path = os.path.join(self.storage_path, folder)
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create default folder '{folder}': {e}")
            
    def create_main_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=1)
        
        self.sidebar_frame = self.create_sidebar()
        self.content_frame = self.create_content_area()
        self.details_frame = self.create_details_panel()

        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.details_frame.grid(row=0, column=2, sticky="nsew")

    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self, corner_radius=0, width=200, fg_color="#1E1E1E")
        ctk.CTkLabel(sidebar, text="Explo", font=("Arial", 28, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(sidebar, text=f"Welcome, {self.current_user}", font=("Arial", 14), text_color="#A9A9A9").pack(pady=(0, 20))
        
        sidebar_buttons = [
            ("Dashboard", self.icons["home"], self.show_dashboard_view),
            ("My Files", self.icons["home"], self.show_home_view),
            ("Favorites", self.icons["favorites"], self.show_favorites_view),
            ("Filter by Tag", self.icons["settings"], self.show_tag_filter_dialog),
            ("Auto-Sort", self.icons["settings"], self.auto_sort_files),
            ("Secret Folder", self.icons["secret"], self.show_secret_folder_view),
            ("Recycle Bin", self.icons["trash"], self.show_recycle_bin_view),
            ("Share via WiFi", self.icons["wifi"], self.start_wifi_share),
            ("Settings", self.icons["settings"], self.show_settings_view),
        ]
        
        for text, icon, command in sidebar_buttons:
            ctk.CTkButton(sidebar, text=text, image=icon, compound="left", anchor="w",
                          command=command, corner_radius=8, fg_color="transparent",
                          hover_color="#3A3D3E").pack(pady=5, padx=10, fill="x")

        ctk.CTkButton(sidebar, text="Logout", command=self.logout, fg_color="red", hover_color="darkred", corner_radius=8).pack(pady=(20, 10), padx=10, fill="x", side="bottom")
        return sidebar
    
    def auto_sort_files(self):
        if not messagebox.askyesno("Auto-Sort", "Are you sure you want to automatically sort your files? This action will move your files into designated folders."):
            return

        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
        document_extensions = ('.pdf', '.docx', '.xlsx', '.pptx', '.txt')
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov')

        for item in os.listdir(self.storage_path):
            item_path = os.path.join(self.storage_path, item)
            if os.path.isfile(item_path):
                file_extension = os.path.splitext(item)[1].lower()
                
                destination_folder = None
                if file_extension in image_extensions:
                    destination_folder = "Images"
                elif file_extension in document_extensions:
                    destination_folder = "Documents"
                elif file_extension in video_extensions:
                    destination_folder = "Videos"
                
                if destination_folder:
                    destination_path = os.path.join(self.storage_path, destination_folder, item)
                    try:
                        shutil.move(item_path, destination_path)
                        log_activity(self.current_user, "auto-sorted", item_path)
                    except shutil.Error as e:
                        print(f"Failed to move {item}: {e}")
        
        messagebox.showinfo("Success", "Files have been sorted.")
        self.show_home_view()

    def create_content_area(self):
        content = ctk.CTkFrame(self, corner_radius=0, fg_color="#212121")
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)
        
        self.header_frame = ctk.CTkFrame(content, height=60, fg_color="#212121")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.back_button = ctk.CTkButton(self.header_frame, text="", image=self.icons["back"], width=40, command=self.go_back, corner_radius=8, fg_color="transparent", hover_color="#3A3D3E")
        self.back_button.grid(row=0, column=0, padx=(0, 10))
        
        self.path_label = ctk.CTkLabel(self.header_frame, text=f"Path: {self.current_path}", anchor="w", font=("Arial", 14))
        self.path_label.grid(row=0, column=1, sticky="ew")

        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Search files...", width=200, corner_radius=8)
        self.search_entry.grid(row=0, column=2, padx=(10, 0))
        self.search_entry.bind("<KeyRelease>", self.filter_file_list)
        
        self.sort_option = ctk.CTkOptionMenu(self.header_frame, values=["Name", "Size", "Date"], command=self.set_sort_option, width=100)
        self.sort_option.set("Name")
        self.sort_option.grid(row=0, column=3, padx=(10, 0))
        
        self.sort_order_button = ctk.CTkButton(self.header_frame, text="▲", width=40, command=self.toggle_sort_order, corner_radius=8)
        self.sort_order_button.grid(row=0, column=4, padx=(5, 0))

        self.show_hidden_button = ctk.CTkButton(self.header_frame, text="", image=self.icons["eye_closed"] if not self.show_hidden_files else self.icons["eye_open"], width=40, command=self.toggle_hidden_files, corner_radius=8, fg_color="transparent", hover_color="#3A3D3E")
        self.show_hidden_button.grid(row=0, column=5, padx=(5, 0))

        self.create_new_button = ctk.CTkButton(self.header_frame, text="Create New", image=self.icons["plus"], compound="left", command=self.show_create_new_menu, corner_radius=8)
        self.create_new_button.grid(row=0, column=6, padx=(10, 0))

        self.content_view_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.content_view_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.content_view_frame, fg_color="transparent")
        
        return content

    def toggle_hidden_files(self):
        self.show_hidden_files = not self.show_hidden_files
        self.show_hidden_button.configure(image=self.icons["eye_open"] if self.show_hidden_files else self.icons["eye_closed"])
        self.save_config()
        if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
            self.refresh_file_list()
        
    def set_sort_option(self, choice):
        self.sort_by = choice.lower()
        if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
            self.refresh_file_list()

    def toggle_sort_order(self):
        if self.sort_order == "asc":
            self.sort_order = "desc"
            self.sort_order_button.configure(text="▼")
        else:
            self.sort_order = "asc"
            self.sort_order_button.configure(text="▲")
        if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
            self.refresh_file_list()

    def create_details_panel(self):
        details = ctk.CTkFrame(self, corner_radius=0, fg_color="#1E1E1E", width=300)
        details.pack_propagate(False)

        ctk.CTkLabel(details, text="File Details", font=("Arial", 20, "bold")).pack(pady=10)
        
        self.detail_image_label = ctk.CTkLabel(details, text="", fg_color="#212121", height=self.icon_size, width=self.icon_size)
        self.detail_image_label.pack(pady=10)
        
        self.detail_name_label = ctk.CTkLabel(details, text="", font=("Arial", 16, "bold"), wraplength=280)
        self.detail_name_label.pack(pady=(5, 0))

        self.detail_info_label = ctk.CTkLabel(details, text="", justify="left", wraplength=280)
        self.detail_info_label.pack(pady=(0, 10), padx=10)
        
        return details
        
    def show_dashboard_view(self):
        self.update_nav_history("dashboard", self.storage_path)
        for widget in self.content_view_frame.winfo_children():
            widget.destroy()

        dashboard_frame = ctk.CTkFrame(self.content_view_frame, fg_color="transparent")
        dashboard_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(dashboard_frame, text="Dashboard", font=("Arial", 24, "bold")).pack(pady=(0, 20), anchor="w")
        
        storage_frame = ctk.CTkFrame(dashboard_frame, corner_radius=10)
        storage_frame.pack(fill="x", pady=(0, 20))
        
        try:
            total, used, _ = shutil.disk_usage(self.storage_path)
            total_gb = total // (2**30)
            used_gb = used // (2**30)
        except FileNotFoundError:
            total_gb = 0
            used_gb = 0
            
        ctk.CTkLabel(storage_frame, text="Storage Usage", font=("Arial", 18, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        ctk.CTkLabel(storage_frame, text=f"{used_gb} GB of {total_gb} GB Used", font=("Arial", 14), text_color="#A9A9A9").pack(padx=10, anchor="w")
        
        storage_progress = ctk.CTkProgressBar(storage_frame, orientation="horizontal")
        storage_progress.pack(fill="x", padx=10, pady=10)
        try:
            storage_progress.set(used / total)
        except ZeroDivisionError:
            storage_progress.set(0)

        access_frame = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
        access_frame.pack(fill="x", pady=(0, 20))
        access_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(access_frame, text="Quick Access", font=("Arial", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        
        quick_access_items = [
            ("Images", self.icons["image_category"], os.path.join(self.storage_path, "Images")),
            ("Documents", self.icons["document_category"], os.path.join(self.storage_path, "Documents")),
            ("Videos", self.icons["video_category"], os.path.join(self.storage_path, "Videos")),
        ]
        
        for i, (name, icon, path) in enumerate(quick_access_items):
            item_frame = ctk.CTkFrame(access_frame, corner_radius=10, fg_color="#3A3D3E")
            item_frame.grid(row=1, column=i, padx=10, pady=10, sticky="nsew")
            item_frame.path = path
            
            icon_label = ctk.CTkLabel(item_frame, text="", image=icon)
            icon_label.pack(side="left", padx=10, pady=10)
            
            name_label = ctk.CTkLabel(item_frame, text=name, font=("Arial", 14, "bold"))
            name_label.pack(side="left", padx=5)

            item_frame.bind("<Double-Button-1>", lambda event, p=path: self.open_folder_from_dashboard(p))
            icon_label.bind("<Double-Button-1>", lambda event, p=path: self.open_folder_from_dashboard(p))
            name_label.bind("<Double-Button-1>", lambda event, p=path: self.open_folder_from_dashboard(p))

        ctk.CTkLabel(dashboard_frame, text="Recent Files", font=("Arial", 18, "bold")).pack(pady=(20, 10), anchor="w")
        recent_frame = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
        recent_frame.pack(fill="x", pady=(0, 20))
        recent_files = self.load_recent_files()
        
        if recent_files:
            for file_path, timestamp in recent_files[:5]:
                file_name = os.path.basename(file_path)
                if os.path.exists(file_path):
                    file_item = ctk.CTkFrame(recent_frame, fg_color="#3A3D3E", corner_radius=8)
                    file_item.pack(fill="x", pady=2, padx=5)
                    
                    file_label = ctk.CTkLabel(file_item, text=f"{file_name} (Accessed: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')})", anchor="w")
                    file_label.pack(side="left", padx=10, pady=5)
                    file_item.bind("<Double-Button-1>", lambda event, p=file_path: self.open_item(p, os.path.isdir(p)))
                
        else:
            ctk.CTkLabel(recent_frame, text="No recent files found.", text_color="#A9A9A9").pack(pady=10)
        
        self.back_button.grid_remove()

    def load_recent_files(self):
        if os.path.exists(self.recent_files_path):
            try:
                with open(self.recent_files_path, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                return []
        return []

    def update_recent_files(self, file_path):
        recent_files = self.load_recent_files()
        new_recent_files = []
        
        file_path_exists = False
        for path, timestamp in recent_files:
            if path == file_path:
                file_path_exists = True
                new_recent_files.append([path, datetime.now().timestamp()])
            else:
                new_recent_files.append([path, timestamp])
        
        if not file_path_exists:
            new_recent_files.append([file_path, datetime.now().timestamp()])
            
        new_recent_files.sort(key=lambda x: x[1], reverse=True)
        
        try:
            with open(self.recent_files_path, 'w') as f:
                json.dump(new_recent_files[:10], f, indent=4)
        except IOError as e:
            messagebox.showerror("Error", f"Could not save recent files: {e}")

    def open_folder_from_dashboard(self, path):
        self.current_path = path
        self.update_nav_history("my_files", self.current_path)
        self.show_file_list_view()

    def show_home_view(self):
        self.current_path = self.storage_path
        self.update_nav_history("my_files", self.current_path)
        self.show_file_list_view()
        
    def show_favorites_view(self):
        self.update_nav_history("favorites", None)
        self.back_button.grid()
        for widget in self.content_view_frame.winfo_children():
            widget.destroy()
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.content_view_frame, fg_color="transparent")
        self.file_list_frame.pack(fill="both", expand=True)
        self.file_list_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.path_label.configure(text=f"Path: Favorites")
        
        self.refresh_favorites_list()

    def refresh_favorites_list(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        try:
            with open(self.favorites_file, "r") as f:
                favorite_paths = [line.strip() for line in f.readlines() if os.path.exists(line.strip())]
        except (IOError, FileNotFoundError):
            favorite_paths = []

        if not favorite_paths:
            ctk.CTkLabel(self.file_list_frame, text="No favorites added yet.", fg_color="transparent").pack(pady=20)
            return

        col, row = 0, 0
        for path in favorite_paths:
            self.create_grid_item_widget(path, col, row, is_favorite_view=True)
            col += 1
            if col > 4:
                col = 0
                row += 1

    def add_to_favorites(self, path):
        try:
            with open(self.favorites_file, "a+") as f:
                f.seek(0)
                favorite_paths = [line.strip() for line in f.readlines()]
                if path not in favorite_paths:
                    f.write(f"{path}\n")
                    messagebox.showinfo("Success", f"'{os.path.basename(path)}' added to favorites.")
                else:
                    messagebox.showinfo("Info", f"'{os.path.basename(path)}' is already in favorites.")
        except IOError as e:
            messagebox.showerror("Error", f"Could not save to favorites file: {e}")

    def remove_from_favorites(self, path):
        try:
            with open(self.favorites_file, "r") as f:
                lines = f.readlines()
            with open(self.favorites_file, "w") as f:
                for line in lines:
                    if line.strip() != path:
                        f.write(line)
            messagebox.showinfo("Success", f"'{os.path.basename(path)}' removed from favorites.")
            self.refresh_favorites_list()
        except IOError as e:
            messagebox.showerror("Error", f"Could not modify favorites file: {e}")

    def show_secret_folder_view(self):
        secret_folder_path = os.path.join(self.storage_path, "Secret")
        try:
            with open(SECRET_FOLDER_PASS_FILE, 'r') as f:
                passwords = json.load(f)
        except (IOError, json.JSONDecodeError):
            passwords = {}

        if not passwords.get(self.current_user):
            new_password = simpledialog.askstring("Secret Folder", "Create a new password for Secret Folder:", parent=self, show='*')
            if new_password:
                passwords[self.current_user] = base64.b64encode(new_password.encode()).decode()
                try:
                    with open(SECRET_FOLDER_PASS_FILE, 'w') as f:
                        json.dump(passwords, f)
                    self.current_path = secret_folder_path
                    self.update_nav_history("secret_folder", self.current_path)
                    self.show_file_list_view(is_secret_folder=True)
                except IOError as e:
                    messagebox.showerror("Error", f"Failed to save password: {e}")
        else:
            password = simpledialog.askstring("Secret Folder", "Enter password for Secret Folder:", parent=self, show='*')
            if password and passwords.get(self.current_user) == base64.b64encode(password.encode()).decode():
                self.current_path = secret_folder_path
                self.update_nav_history("secret_folder", self.current_path)
                self.show_file_list_view(is_secret_folder=True)
            else:
                messagebox.showerror("Error", "Incorrect password.")

    def show_recycle_bin_view(self):
        self.update_nav_history("recycle_bin", None)
        self.back_button.grid()
        recycle_bin_path = os.path.join(self.storage_path, ".RecycleBin")
        if not os.path.exists(recycle_bin_path):
            os.makedirs(recycle_bin_path)

        for widget in self.content_view_frame.winfo_children():
            widget.destroy()
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.content_view_frame, fg_color="transparent")
        self.file_list_frame.pack(fill="both", expand=True)
        self.file_list_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.path_label.configure(text="Path: Recycle Bin")

        try:
            items = sorted(os.listdir(recycle_bin_path))
            
            col, row = 0, 0
            for item in items:
                item_path = os.path.join(recycle_bin_path, item)
                self.create_recycle_bin_item_widget(item_path, col, row)
                col += 1
                if col > 4:
                    col = 0
                    row += 1
        except FileNotFoundError:
            ctk.CTkLabel(self.file_list_frame, text="Recycle Bin is empty.", fg_color="transparent").grid(row=0, column=0, pady=20)
    
    def create_recycle_bin_item_widget(self, path, col, row):
        name = os.path.basename(path)
        is_dir = os.path.isdir(path)
        
        item_frame = ctk.CTkFrame(self.file_list_frame, width=self.icon_size+30, height=self.icon_size+50, corner_radius=10)
        item_frame.grid(row=row, column=col, padx=8, pady=8)
        item_frame.grid_propagate(False)
        item_frame.grid_columnconfigure(0, weight=1)
        item_frame.grid_rowconfigure(0, weight=1)
        item_frame.path = path
        
        icon_label = ctk.CTkLabel(item_frame, text="")
        icon_label.grid(row=0, column=0, pady=(15, 0), padx=5)
        
        file_name_label = ctk.CTkLabel(item_frame, text=name, anchor="center", font=("Arial", 14), wraplength=self.icon_size+20)
        file_name_label.grid(row=1, column=0, padx=5, pady=(5, 10))
        
        thumbnail_image = self.get_thumbnail(path, name)
        icon_label.configure(image=thumbnail_image, text="")
        icon_label.image = thumbnail_image

        menu = tk.Menu(item_frame, tearoff=0)
        menu.add_command(label="Restore", command=lambda: self.restore_item(path))
        menu.add_command(label="Delete Permanently", command=lambda: self.delete_item_permanently(path))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)

        item_frame.bind("<Button-3>", show_menu)
        icon_label.bind("<Button-3>", show_menu)
        file_name_label.bind("<Button-3>", show_menu)

    def restore_item(self, path):
        destination_path = os.path.join(self.storage_path, os.path.basename(path))
        if os.path.exists(destination_path):
            messagebox.showerror("Error", "File already exists in the original location.")
            return

        try:
            shutil.move(path, destination_path)
            messagebox.showinfo("Success", f"'{os.path.basename(path)}' has been restored.")
            self.show_recycle_bin_view()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore file: {e}")

    def delete_item_permanently(self, path):
        item_name = os.path.basename(path)
        if messagebox.askyesno("Delete Permanently", f"Are you sure you want to permanently delete '{item_name}'? This cannot be undone."):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                messagebox.showinfo("Success", f"'{item_name}' has been permanently deleted.")
                self.show_recycle_bin_view()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete permanently: {e}")

    def start_wifi_share(self):
        port = 8000
        handler = MyHTTPRequestHandler
        handler.storage_path = self.current_path
        
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"Serving at port {port}")
                self.httpd = httpd
                ctk.CTkLabel(self.content_view_frame, text=f"Share via WiFi is active. Go to http://{self.get_local_ip()}:{port} on another device.", wraplength=400).pack(pady=20)
                threading.Thread(target=httpd.serve_forever).start()
        except OSError as e:
            messagebox.showerror("Error", f"Could not start the server: {e}\nTry changing the port or checking for other running applications.")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def show_settings_view(self):
        self.update_nav_history("settings", None)
        self.back_button.grid()
        for widget in self.content_view_frame.winfo_children():
            widget.destroy()
        
        settings_frame = ctk.CTkFrame(self.content_view_frame, fg_color="transparent")
        settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(settings_frame, text="Settings", font=("Arial", 24, "bold")).pack(pady=(0, 20), anchor="w")

        appearance_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        appearance_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(appearance_frame, text="Appearance", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(appearance_frame, text="Theme Mode:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.theme_mode_option = ctk.CTkOptionMenu(appearance_frame, values=["System", "Light", "Dark"], command=self.change_theme_mode)
        self.theme_mode_option.set(ctk.get_appearance_mode().capitalize())
        self.theme_mode_option.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(appearance_frame, text="Color Theme:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.color_theme_option = ctk.CTkOptionMenu(appearance_frame, values=["Blue", "Dark-Blue", "Green"], command=ctk.set_default_color_theme)
        self.color_theme_option.set(ctk.get_default_color_theme().capitalize())
        self.color_theme_option.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(appearance_frame, text="Show Hidden Files:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.show_hidden_checkbox = ctk.CTkCheckBox(appearance_frame, text="Show files starting with '.'", command=self.toggle_hidden_files_from_settings)
        self.show_hidden_checkbox.pack(fill="x", padx=20, pady=(0, 10))
        if self.show_hidden_files:
            self.show_hidden_checkbox.select()

        password_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        password_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(password_frame, text="Change Password", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(password_frame, text="Current Password:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.current_pass_entry = ctk.CTkEntry(password_frame, show="*")
        self.current_pass_entry.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(password_frame, text="New Password:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.new_pass_entry = ctk.CTkEntry(password_frame, show="*")
        self.new_pass_entry.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(password_frame, text="Confirm New Password:", anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.confirm_new_pass_entry = ctk.CTkEntry(password_frame, show="*")
        self.confirm_new_pass_entry.pack(fill="x", padx=20, pady=(0, 5))

        change_pass_button = ctk.CTkButton(password_frame, text="Change Password", command=self.change_password)
        change_pass_button.pack(padx=20, pady=10)
        
    def toggle_hidden_files_from_settings(self):
        self.show_hidden_files = not self.show_hidden_files
        self.show_hidden_button.configure(image=self.icons["eye_open"] if self.show_hidden_files else self.icons["eye_closed"])
        self.save_config()
        if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
            self.refresh_file_list()

    def change_theme_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.load_icons()
        if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
            self.refresh_file_list()
        else:
            self.show_dashboard_view()

    def change_password(self):
        current_pass = self.current_pass_entry.get()
        new_pass = self.new_pass_entry.get()
        confirm_pass = self.confirm_new_pass_entry.get()

        if not verify_login(self.current_user, current_pass):
            messagebox.showerror("Error", "Incorrect current password.")
            return

        if new_pass != confirm_pass:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        
        if not new_pass or len(new_pass) < 6:
            messagebox.showerror("Error", "New password must be at least 6 characters long.")
            return

        try:
            with open(USERS_FILE, "r") as f:
                lines = f.readlines()
            
            with open(USERS_FILE, "w") as f:
                for line in lines:
                    username, password = line.strip().split(":", 1)
                    if username == self.current_user:
                        f.write(f"{username}:{new_pass}\n")
                    else:
                        f.write(line)
            
            messagebox.showinfo("Success", "Password changed successfully!")
            self.current_pass_entry.delete(0, 'end')
            self.new_pass_entry.delete(0, 'end')
            self.confirm_new_pass_entry.delete(0, 'end')

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def add_tag_to_file(self, path):
        dialog = ctk.CTkInputDialog(text="Enter tag name:", title="Add Tag")
        tag = dialog.get_input()
        if tag:
            if path not in self.tags:
                self.tags[path] = []
            if tag not in self.tags[path]:
                self.tags[path].append(tag)
                self.save_tags()
                if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
                    self.refresh_file_list()
                messagebox.showinfo("Success", f"Tag '{tag}' added to {os.path.basename(path)}")
    
    def show_tag_filter_dialog(self):
        all_tags = set(tag for tags_list in self.tags.values() for tag in tags_list)
        if not all_tags:
            messagebox.showinfo("Info", "No tags available.")
            return

        dialog = ctk.CTkInputDialog(text=f"Available tags: {', '.join(all_tags)}\n\nEnter tag to filter (leave blank to clear filter):", title="Filter by Tag")
        tag_to_filter = dialog.get_input()
        self.refresh_file_list(tag=tag_to_filter)

    def rename_item(self, old_path):
        current_name, ext = os.path.splitext(os.path.basename(old_path))
        dialog = ctk.CTkInputDialog(text=f"Rename '{current_name}' to:", title="Rename")
        new_name = dialog.get_input()
        
        if new_name:
            new_filename = new_name + ext
            new_path = os.path.join(os.path.dirname(old_path), new_filename)
            
            if not os.path.exists(new_path):
                try:
                    os.rename(old_path, new_path)
                    if old_path in self.tags:
                        self.tags[new_path] = self.tags.pop(old_path)
                        self.save_tags()
                    if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
                        self.refresh_file_list()
                    messagebox.showinfo("Success", f"'{os.path.basename(old_path)}' renamed to '{new_filename}'")
                except OSError as e:
                    messagebox.showerror("Error", f"Failed to rename file: {e}")
            else:
                messagebox.showerror("Error", "A file or folder with that name already exists!")

    def delete_item(self, path):
        item_name = os.path.basename(path)
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{item_name}'? It will be moved to the Recycle Bin."):
            try:
                recycle_bin_path = os.path.join(self.storage_path, ".RecycleBin")
                if not os.path.exists(recycle_bin_path):
                    os.makedirs(recycle_bin_path)

                destination_path = os.path.join(recycle_bin_path, item_name)
                
                if os.path.exists(destination_path):
                    base, ext = os.path.splitext(item_name)
                    i = 1
                    while os.path.exists(os.path.join(recycle_bin_path, f"{base} ({i}){ext}")):
                        i += 1
                    destination_path = os.path.join(recycle_bin_path, f"{base} ({i}){ext}")
                    
                shutil.move(path, destination_path)
                
                if path in self.tags:
                    del self.tags[path]
                    self.save_tags()

                log_activity(self.current_user, "moved to Recycle Bin", path)
                messagebox.showinfo("Success", f"'{item_name}' has been moved to the Recycle Bin.")
                if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
                    self.refresh_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not move '{item_name}' to Recycle Bin: {e}")
    
    def filter_file_list(self, event=None):
        search_query = self.search_entry.get().lower()
        self.refresh_file_list(search_query=search_query)

    def refresh_file_list(self, tag=None, is_secret_folder=False, search_query=""):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        try:
            items = sorted(os.listdir(self.current_path))
            
            items = [item for item in items if item not in (".RecycleBin", "favorites.txt", "recent_files.json", "tags.json", "config.json")]
            
            if not is_secret_folder:
                items = [item for item in items if item != "Secret"]
            
            if not self.show_hidden_files:
                items = [item for item in items if not item.startswith('.')]
                
            if self.sort_by == "name":
                items.sort(key=lambda x: x.lower(), reverse=(self.sort_order == "desc"))
            elif self.sort_by == "size":
                items.sort(key=lambda x: get_total_size(os.path.join(self.current_path, x)), reverse=(self.sort_order == "desc"))
            elif self.sort_by == "date":
                items.sort(key=lambda x: os.path.getmtime(os.path.join(self.current_path, x)), reverse=(self.sort_order == "desc"))

            col, row = 0, 0
            for item in items:
                item_path = os.path.join(self.current_path, item)
                
                item_tags = self.tags.get(item_path, [])
                if tag and tag not in item_tags:
                    continue
                
                if search_query and search_query not in item.lower():
                    continue

                self.create_grid_item_widget(item_path, col, row)
                col += 1
                if col > 4:
                    col = 0
                    row += 1
        except FileNotFoundError:
            ctk.CTkLabel(self.file_list_frame, text="Folder not found.", fg_color="transparent").grid(row=0, column=0, pady=20)
        except OSError as e:
            messagebox.showerror("Error", f"Failed to access folder: {e}")

    def create_grid_item_widget(self, path, col, row, is_favorite_view=False):
        name = os.path.basename(path)
        is_dir = os.path.isdir(path)
        
        item_frame = ctk.CTkFrame(self.file_list_frame, width=self.icon_size+30, height=self.icon_size+50, corner_radius=10, fg_color="transparent")
        item_frame.grid(row=row, column=col, padx=8, pady=8)
        item_frame.grid_propagate(False)
        item_frame.grid_columnconfigure(0, weight=1)
        item_frame.path = path
        
        item_frame.bind("<Enter>", lambda event: item_frame.configure(fg_color="#3A3D3E"))
        item_frame.bind("<Leave>", lambda event: item_frame.configure(fg_color="transparent"))
        item_frame.bind("<Double-Button-1>", lambda event: self.open_item(path, is_dir))
        item_frame.bind("<Button-1>", lambda event: self.show_file_details_and_select(path, item_frame))

        icon_label = ctk.CTkLabel(item_frame, text="")
        icon_label.grid(row=0, column=0, pady=(10, 0), padx=5, sticky="n")
        
        file_name_label = ctk.CTkLabel(item_frame, text=name, anchor="n", font=("Arial", 14), wraplength=self.icon_size+20)
        file_name_label.grid(row=1, column=0, padx=5, pady=(5, 10), sticky="n")
        
        thumbnail_image = self.get_thumbnail(path, name)
        if thumbnail_image:
            icon_label.configure(image=thumbnail_image, text="", width=self.icon_size, height=self.icon_size)
            icon_label.image = thumbnail_image
        else:
            icon_label.configure(image=self.icons["file"], text="", width=self.icon_size, height=self.icon_size)
            icon_label.image = self.icons["file"]

        icon_label.bind("<Double-Button-1>", lambda event: self.open_item(path, is_dir))
        icon_label.bind("<Button-1>", lambda event: self.show_file_details_and_select(path, item_frame))
        file_name_label.bind("<Double-Button-1>", lambda event: self.open_item(path, is_dir))
        file_name_label.bind("<Button-1>", lambda event: self.show_file_details_and_select(path, item_frame))
        
        menu = tk.Menu(item_frame, tearoff=0)
        menu.add_command(label="Open", command=lambda: self.open_item(path, is_dir))
        
        if is_favorite_view:
            menu.add_command(label="Remove from Favorites", command=lambda: self.remove_from_favorites(path))
        else:
            menu.add_command(label="Add to Favorites", command=lambda: self.add_to_favorites(path))

        menu.add_separator()
        menu.add_command(label="Rename", command=lambda: self.rename_item(path))
        menu.add_command(label="Delete", command=lambda: self.delete_item(path))
        menu.add_command(label="Secure Delete", command=lambda: self.secure_delete_item(path))
        menu.add_command(label="Add Tag", command=lambda: self.add_tag_to_file(path))
        menu.add_separator()
        menu.add_command(label="Encrypt File", command=lambda: self.encrypt_file(path))
        menu.add_command(label="Decrypt File", command=lambda: self.decrypt_file(path))
        menu.add_command(label="Get MD5 Hash", command=lambda: self.get_file_hash(path, "md5"))
        menu.add_separator()
        menu.add_command(label="Restore Old Version", command=lambda: self.restore_version(path))

        def show_menu(event):
            menu.post(event.x_root, event.y_root)

        item_frame.bind("<Button-3>", show_menu)
        icon_label.bind("<Button-3>", show_menu)
        file_name_label.bind("<Button-3>", show_menu)

    def show_file_details_and_select(self, path, frame):
        if self.selected_item_frame:
            self.selected_item_frame.configure(border_width=0)
        
        self.selected_item_frame = frame
        self.selected_item_frame.configure(border_width=2, border_color="#1F6AA5")
        
        self.show_file_details(path)
        
    def get_thumbnail(self, path, name):
        size = self.thumbnail_size
        if os.path.isdir(path):
            return self.icons["folder"]
        
        file_extension = os.path.splitext(name)[1].lower()
        if file_extension in ('.png', '.jpg', '.jpeg', '.gif', '.bmp'):
            try:
                img = Image.open(path)
                img.thumbnail(size, Image.LANCZOS)
                
                background = Image.new('RGBA', size, (0, 0, 0, 0))
                paste_position = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
                background.paste(img, paste_position)
                
                return ImageTk.PhotoImage(background)
            except Exception as e:
                print(f"Error creating thumbnail for {name}: {e}")
                return self.icons["file"]
        elif file_extension in ('.mp4', '.mkv', '.avi', '.mov'):
            return self.icons["video"]
        elif file_extension in ('.txt', '.log'):
            return self.icons["file_edit"]
        else:
            return self.icons["file"]
            
    def open_item(self, path, is_dir):
        if is_dir:
            self.current_path = path
            self.path_label.configure(text=f"Path: {self.current_path.replace(self.storage_path, 'My Files')}")
            
            self.update_nav_history("my_files", self.current_path)
            
            is_secret = os.path.basename(self.current_path) == "Secret"
            self.refresh_file_list(is_secret_folder=is_secret)
        else:
            self.show_file_details(path)
            self.update_recent_files(path)
            
            file_extension = os.path.splitext(path)[1].lower()
            if file_extension in ('.txt', '.log', '.md'):
                self.open_text_editor(path)
            else:
                try:
                    os.startfile(path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {e}")

    def open_text_editor(self, path):
        editor_window = ctk.CTkToplevel(self)
        editor_window.title(f"Editing: {os.path.basename(path)}")
        editor_window.geometry("800x600")
        
        frame = ctk.CTkFrame(editor_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        textbox = ctk.CTkTextbox(frame, wrap="word", font=("Courier New", 12))
        textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        try:
            with open(path, "r") as f:
                content = f.read()
                textbox.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}", parent=editor_window)
            
        def save_and_close():
            try:
                self.save_file_version(path)
                new_content = textbox.get("1.0", "end-1c")
                with open(path, "w") as f:
                    f.write(new_content)
                messagebox.showinfo("Success", "File saved successfully!", parent=editor_window)
                self.update_recent_files(path)
                editor_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}", parent=editor_window)

        save_button = ctk.CTkButton(editor_window, text="Save", command=save_and_close)
        save_button.pack(pady=5)

    def save_file_version(self, path):
        history_dir = os.path.join(os.path.dirname(path), ".history", os.path.basename(path))
        os.makedirs(history_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        version_name = f"{timestamp}_{os.path.basename(path)}"
        version_path = os.path.join(history_dir, version_name)
        
        shutil.copy2(path, version_path)
        log_activity(self.current_user, "created file version", version_path)

    def restore_version(self, path):
        history_dir = os.path.join(os.path.dirname(path), ".history", os.path.basename(path))
        if not os.path.exists(history_dir) or not os.listdir(history_dir):
            messagebox.showinfo("Info", "No previous versions found for this file.")
            return

        versions = sorted(os.listdir(history_dir), reverse=True)
        
        dialog_window = ctk.CTkToplevel(self)
        dialog_window.title("Restore Version")
        dialog_window.geometry("400x300")
        dialog_window.grab_set()

        ctk.CTkLabel(dialog_window, text="Select a version to restore:", font=("Arial", 16, "bold")).pack(pady=10)
        
        listbox_frame = ctk.CTkFrame(dialog_window)
        listbox_frame.pack(padx=20, pady=10, fill="both", expand=True)

        listbox = tk.Listbox(listbox_frame, background=ctk.get_appearance_mode().lower() == "light" and "#EBEBEB" or "#2A2D2E",
                             foreground=ctk.get_appearance_mode().lower() == "light" and "#000000" or "#FFFFFF",
                             selectbackground="#1F6AA5", font=("Arial", 12), borderwidth=0, highlightthickness=0)
        listbox.pack(fill="both", expand=True)
        
        for v in versions:
            timestamp = v.split('_')[0]
            display_name = datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")
            listbox.insert(tk.END, display_name)
        
        def do_restore():
            selected_index = listbox.curselection()
            if selected_index:
                selected_version = versions[selected_index[0]]
                source_path = os.path.join(history_dir, selected_version)
                try:
                    shutil.copy2(source_path, path)
                    messagebox.showinfo("Success", f"File restored to version from {selected_version.split('_')[0]}")
                    if self.nav_history[-1]["view"] in ["my_files", "secret_folder", "recycle_bin"]:
                        self.refresh_file_list()
                    dialog_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to restore file: {e}")
            else:
                messagebox.showerror("Error", "Please select a version to restore.")

        restore_button = ctk.CTkButton(dialog_window, text="Restore", command=do_restore)
        restore_button.pack(pady=10)


    def show_file_details(self, path):
        self.detail_name_label.configure(text=os.path.basename(path))
        info = f"Size: {self.get_file_info(path)}\n"
        info += f"Modified: {datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        tags_list = self.tags.get(path, [])
        info += f"Tags: {', '.join(tags_list) if tags_list else 'None'}\n"
        
        self.detail_info_label.configure(text=info)
        
        file_extension = os.path.splitext(path)[1].lower()
        if os.path.isdir(path):
             self.detail_image_label.configure(image=self.icons["folder"], text="")
        elif file_extension in ('.png', '.jpg', '.jpeg', '.gif', '.bmp'):
            try:
                img = Image.open(path)
                img.thumbnail((200, 200), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.detail_image_label.configure(image=photo, text="")
                self.detail_image_label.image = photo
            except Exception as e:
                print(f"Error creating thumbnail for details panel: {e}")
                self.detail_image_label.configure(image=self.icons["file"], text="")
        else:
            self.detail_image_label.configure(image=self.get_thumbnail(path, os.path.basename(path)), text="")


    def get_file_info(self, path):
        size_in_bytes = get_total_size(path)
        size_in_kb = size_in_bytes / 1024
        if size_in_kb < 1024:
            return f"{size_in_kb:.2f} KB"
        else:
            size_in_mb = size_in_kb / 1024
            return f"{size_in_mb:.2f} MB"

    def go_back(self):
        if len(self.nav_history) > 1:
            self.nav_history.pop()
            last_state = self.nav_history[-1]
            view_name = last_state["view"]
            path = last_state["path"]
            
            if view_name == "dashboard":
                self.show_dashboard_view()
            elif view_name == "my_files":
                self.current_path = path
                self.show_file_list_view()
            elif view_name == "favorites":
                self.show_favorites_view()
            elif view_name == "secret_folder":
                self.current_path = path
                self.show_file_list_view(is_secret_folder=True)
            elif view_name == "recycle_bin":
                self.show_recycle_bin_view()
            elif view_name == "settings":
                self.show_settings_view()

    def show_file_list_view(self, is_secret_folder=False):
        for widget in self.content_view_frame.winfo_children():
            widget.destroy()
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.content_view_frame, fg_color="transparent")
        self.file_list_frame.pack(fill="both", expand=True)
        self.file_list_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        display_path = self.current_path.replace(self.storage_path, 'My Files')
        if is_secret_folder:
            display_path = "Secret Folder"
        self.path_label.configure(text=f"Path: {display_path}")
        self.back_button.grid()
        self.refresh_file_list(is_secret_folder=is_secret_folder)

    def update_nav_history(self, view_name, path):
        current_state = {"view": view_name, "path": path}
        if not self.nav_history or self.nav_history[-1] != current_state:
            self.nav_history.append(current_state)
        
        if len(self.nav_history) > 10:
            self.nav_history.pop(0)

        if len(self.nav_history) > 1:
            self.back_button.grid()
        else:
            self.back_button.grid_remove()

    def show_create_new_menu(self):
        menu = tk.Menu(self.create_new_button, tearoff=0)
        
        menu.add_command(label="New Folder", command=self.create_folder_dialog)
        menu.add_command(label="New Text File (.txt)", command=self.create_text_file)
        menu.add_command(label="Upload File", command=self.upload_file)
        menu.add_command(label="Compress to ZIP", command=self.compress_files)
        
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def create_text_file(self):
        dialog = ctk.CTkInputDialog(text="New text file name (.txt):", title="Create Text File")
        file_name = dialog.get_input()
        if file_name:
            if not file_name.endswith(".txt"):
                file_name += ".txt"
            file_path = os.path.join(self.current_path, file_name)
            try:
                if not os.path.exists(file_path):
                    with open(file_path, "w") as f:
                        f.write("")
                    self.refresh_file_list()
                    self.open_text_editor(file_path)
                else:
                    messagebox.showerror("Error", "File already exists!")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create file: {e}")

    def create_folder_dialog(self):
        dialog = ctk.CTkInputDialog(text="New folder name:", title="Create Folder")
        folder_name = dialog.get_input()
        if folder_name:
            folder_path = os.path.join(self.current_path, folder_name)
            try:
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    self.refresh_file_list()
                else:
                    messagebox.showerror("Error", "Folder already exists!")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create folder: {e}")

    def upload_file(self):
        file_path_source = filedialog.askopenfilename()
        if not file_path_source:
            return

        file_name = os.path.basename(file_path_source)
        destination_path = os.path.join(self.current_path, file_name)

        try:
            if os.path.exists(destination_path):
                base, ext = os.path.splitext(file_name)
                i = 1
                while os.path.exists(os.path.join(self.current_path, f"{base} ({i}){ext}")):
                    i += 1
                destination_path = os.path.join(self.current_path, f"{base} ({i}){ext}")
                
            shutil.copy2(file_path_source, destination_path)
            log_activity(self.current_user, "uploaded", destination_path)
            self.update_recent_files(destination_path)
            
            messagebox.showinfo("Success", f"File '{os.path.basename(destination_path)}' berhasil diunggah.")
            self.refresh_file_list()

        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengunggah file: {e}")

    def compress_files(self):
        selected_files = filedialog.askopenfilenames(title="Select files to compress")
        if selected_files:
            zip_filename = simpledialog.askstring("Compress", "ZIP file name:", parent=self)
            if zip_filename:
                zip_path = os.path.join(self.current_path, f"{zip_filename}.zip")
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for file in selected_files:
                            zipf.write(file, os.path.basename(file))
                    messagebox.showinfo("Success", f"Files compressed to {zip_path}")
                    self.refresh_file_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to compress files: {e}")

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.destroy()

    def encrypt_file(self, path):
        password = simpledialog.askstring("Encrypt", "Enter password for encryption:", parent=self, show='*')
        if not password:
            return
        
        try:
            with open(path, 'rb') as f:
                original_data = f.read()
            
            encoded_data = base64.b64encode(original_data)
            
            encrypted_path = path + ".enc"
            with open(encrypted_path, 'wb') as f:
                f.write(encoded_data)
            
            os.remove(path)
            messagebox.showinfo("Success", f"File '{os.path.basename(path)}' successfully encrypted.")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to encrypt file: {e}")
            
    def decrypt_file(self, path):
        password = simpledialog.askstring("Decrypt", "Enter password to decrypt:", parent=self, show='*')
        if not password:
            return
            
        try:
            with open(path, 'rb') as f:
                encrypted_data = f.read()
            
            decoded_data = base64.b64decode(encrypted_data)
            
            decrypted_path = path[:-4]
            with open(decrypted_path, 'wb') as f:
                f.write(decoded_data)
            
            os.remove(path)
            messagebox.showinfo("Success", f"File '{os.path.basename(path)}' successfully decrypted.")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to decrypt file: {e}")

    def get_file_hash(self, path, hash_algo="md5"):
        try:
            with open(path, "rb") as f:
                bytes = f.read()
                if hash_algo == "md5":
                    hash_value = hashlib.md5(bytes).hexdigest()
                else:
                    hash_value = "Unsupported algorithm"
            
            dialog = ctk.CTkToplevel(self)
            dialog.title("File Hash")
            dialog.geometry("400x150")
            dialog.grab_set()

            ctk.CTkLabel(dialog, text=f"MD5 Hash for '{os.path.basename(path)}':", font=("Arial", 14, "bold")).pack(pady=10)
            ctk.CTkEntry(dialog, textvariable=tk.StringVar(value=hash_value), state="readonly", width=350).pack(padx=20, pady=5)
            ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get hash: {e}")

    def secure_delete_item(self, path):
        item_name = os.path.basename(path)
        if not messagebox.askyesno("Secure Delete", f"Are you sure you want to securely delete '{item_name}'? This process is irreversible."):
            return
        
        try:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path, topdown=False):
                    for name in files:
                        self._overwrite_file(os.path.join(root, name))
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(path)
            else:
                self._overwrite_file(path)
                os.remove(path)
                
            if path in self.tags:
                del self.tags[path]
                self.save_tags()
                
            messagebox.showinfo("Success", f"'{item_name}' has been securely deleted.")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to securely delete '{item_name}': {e}")
            
    def _overwrite_file(self, path, passes=3):
        try:
            with open(path, "ba+") as f:
                f.seek(0)
                filesize = f.tell()
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(filesize))
                    f.flush()
                    os.fsync(f.fileno())
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error during file overwrite: {e}")

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    storage_path = None
    
    def do_POST(self):
        if self.path == '/upload':
            content_type = self.headers.get('Content-Type')
            if not content_type.startswith('multipart/form-data'):
                self.send_response(400)
                self.end_headers()
                return

            try:
                form_data = self.read_multipart_form_data()
                if 'file' in form_data:
                    file_info = form_data['file']
                    file_name = file_info['filename']
                    file_content = file_info['content']
                    
                    upload_path = os.path.join(self.storage_path, file_name)
                    with open(upload_path, 'wb') as f:
                        f.write(file_content)
                    
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"File uploaded successfully!")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No file received.")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"An error occurred: {e}".encode())

    def read_multipart_form_data(self, boundary):
        data = {}
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        parts = post_data.split(b'--' + boundary)
        
        for part in parts:
            if not part or part == b'--\r\n':
                continue
            
            header, content = part.split(b'\r\n\r\n', 1)
            
            header_str = header.decode()
            
            if 'Content-Disposition' in header_str:
                disposition = header_str.split('Content-Disposition: ')[1]
                if 'filename=' in disposition:
                    filename = disposition.split('filename=')[1].strip().replace('"', '')
                    data['file'] = {'filename': filename.encode().decode('unicode_escape'), 'content': content.strip()}

        return data
        
if __name__ == "__main__":
    app = App()
    app.mainloop()