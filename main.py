import customtkinter as ctk
import os
import shutil
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import subprocess
import tkinter as tk
import sys

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BASE_DIR = "data"
os.makedirs(BASE_DIR, exist_ok=True)
USERS_FILE = os.path.join(BASE_DIR, "users.txt")

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("miaw:123.,#")

def verify_login(username, password):
    with open(USERS_FILE, "r") as f:
        for line in f:
            stored_username, stored_password = line.strip().split(":")
            if username == stored_username and password == stored_password:
                return True
    return False

class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Login")
        self.geometry("300x200")
        self.center_window()
        self.grab_set()

        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, "assets", "app_icon.png")
            icon_image = Image.open(icon_path)
            icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(False, icon_photo)
        except Exception:
            pass

        self.label = ctk.CTkLabel(self, text="Login Pengguna", font=("Arial", 16))
        self.label.pack(pady=10)

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username")
        self.username_entry.pack(pady=5, padx=20)

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=5, padx=20)

        self.login_button = ctk.CTkButton(self, text="Login", command=self.check_login)
        self.login_button.pack(pady=10)

        self.login_successful = False

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (300 / 2)
        y = (screen_height / 2) - (200 / 2)
        self.geometry(f"300x200+{int(x)}+{int(y)}")

    def check_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if verify_login(username, password):
            self.login_successful = True
            self.destroy()
        else:
            messagebox.showerror("Error", "Username atau password salah!")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aplikasi Penyimpanan Gambar & Dokumen")
        self.geometry("1200x800")
        
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, "assets", "app_icon.png")
            icon_image = Image.open(icon_path)
            icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(False, icon_photo)
        except Exception as e:
            print(f"Gagal memuat ikon aplikasi: {e}")
            pass

        self.folder_icon_img = self.load_icon("folder_icon.png")
        self.file_icon_img = self.load_icon("file_icon.png")
        self.back_icon_img = self.load_icon("back_icon.png", (24, 24))
        self.video_icon_img = self.load_icon("video_icon.png")

        self.login_window = LoginWindow(self)
        self.wait_window(self.login_window)

        if self.login_window.login_successful:
            self.current_path = os.path.join(BASE_DIR, "storage")
            os.makedirs(self.current_path, exist_ok=True)
            self.show_main_dashboard()
        else:
            self.destroy()

    def load_icon(self, filename, size=(120, 120)):
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            image_path = os.path.join(base_path, "assets", filename)
            
            img = Image.open(image_path)
            img.thumbnail(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def show_main_dashboard(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(self.sidebar_frame, text="Menu", font=("Arial", 20)).pack(pady=20)
        
        self.create_folder_button = ctk.CTkButton(self.sidebar_frame, text="Buat Folder", command=self.create_folder_dialog)
        self.create_folder_button.pack(pady=5, padx=10)

        self.upload_button = ctk.CTkButton(self.sidebar_frame, text="Upload File", command=self.upload_file)
        self.upload_button.pack(pady=5, padx=10)

        self.logout_button = ctk.CTkButton(self.sidebar_frame, text="Logout", fg_color="red", hover_color="darkred", command=self.logout)
        self.logout_button.pack(pady=20, padx=10)
        
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_frame, height=50)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.header_frame.grid_columnconfigure(2, weight=1)

        self.back_button = ctk.CTkButton(self.header_frame, text="Kembali", image=self.back_icon_img, compound="left", command=self.go_back)
        self.back_button.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.path_label = ctk.CTkLabel(self.header_frame, text=f"Jalur: {self.current_path}", anchor="w", font=("Arial", 12))
        self.path_label.grid(row=0, column=1, sticky="ew", padx=5, pady=10)

        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Cari file...")
        self.search_entry.grid(row=0, column=2, padx=(5, 5), pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.search_files)

        self.search_button = ctk.CTkButton(self.header_frame, text="Cari", command=self.search_files)
        self.search_button.grid(row=0, column=3, padx=(0, 10), pady=10)
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.file_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.file_list_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.refresh_file_list()

    def refresh_file_list(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        try:
            items = sorted(os.listdir(self.current_path))
            col, row = 0, 0
            for item in items:
                item_path = os.path.join(self.current_path, item)
                self.create_item_widget(item_path, col, row)
                col += 1
                if col > 5:
                    col = 0
                    row += 1

        except FileNotFoundError:
            ctk.CTkLabel(self.file_list_frame, text="Folder tidak ditemukan.", fg_color="transparent").grid(row=0, column=0, pady=20)

    def create_item_widget(self, path, col, row):
        name = os.path.basename(path)
        is_dir = os.path.isdir(path)
        
        item_frame = ctk.CTkFrame(self.file_list_frame, width=150, height=170)
        item_frame.grid(row=row, column=col, padx=3, pady=3)
        item_frame.grid_columnconfigure(0, weight=1)
        item_frame.grid_rowconfigure(0, weight=1)

        icon_label = ctk.CTkLabel(item_frame, text="")
        icon_label.grid(row=0, column=0, pady=(15, 0), padx=5)
        
        file_name_label = ctk.CTkLabel(item_frame, text=name, anchor="center", font=("Arial", 14), wraplength=130)
        file_name_label.grid(row=1, column=0, padx=5, pady=(5, 10))
        
        if is_dir:
            icon_label.configure(image=self.folder_icon_img, text="📂") if not self.folder_icon_img else icon_label.configure(image=self.folder_icon_img, text="")
        else:
            file_extension = os.path.splitext(name)[1].lower()
            if file_extension in ('.png', '.jpg', '.jpeg', '.gif', '.bmp'):
                try:
                    img = Image.open(path)
                    img.thumbnail((120, 120))
                    photo = ImageTk.PhotoImage(img)
                    icon_label.configure(image=photo, text="")
                    icon_label.image = photo
                except Exception:
                    icon_label.configure(image=self.file_icon_img, text="🖼️") if not self.file_icon_img else icon_label.configure(image=self.file_icon_img, text="")
            elif file_extension in ('.mp4', '.mkv', '.avi', '.mov'):
                # Cukup tampilkan ikon video, tidak perlu membuat thumbnail
                icon_label.configure(image=self.video_icon_img, text="▶️") if not self.video_icon_img else icon_label.configure(image=self.video_icon_img, text="")
            elif file_extension in ('.mp3', '.wav', '.ogg'):
                icon_label.configure(image=self.file_icon_img, text="🎵") if not self.file_icon_img else icon_label.configure(image=self.file_icon_img, text="")
            else:
                icon_label.configure(image=self.file_icon_img, text="📄") if not self.file_icon_img else icon_label.configure(image=self.file_icon_img, text="")

        def open_action(event):
            self.open_item(path, is_dir)

        item_frame.bind("<Button-1>", open_action)
        icon_label.bind("<Button-1>", open_action)
        file_name_label.bind("<Button-1>", open_action)

        option_button = ctk.CTkButton(item_frame, text="...", width=20, height=20, fg_color="transparent", hover_color="gray", command=lambda: show_options_menu(option_button))
        option_button.grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        
        def show_options_menu(button):
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Ganti Nama", command=lambda: self.rename_item(path))
            menu.add_command(label="Hapus", command=lambda: self.delete_item(path))
            menu.post(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())
            
    def go_back(self):
        parent_dir = os.path.dirname(self.current_path)
        if parent_dir and os.path.exists(parent_dir) and parent_dir.startswith(os.path.join(BASE_DIR, "storage")):
            self.current_path = parent_dir
            self.path_label.configure(text=f"Jalur: {self.current_path}")
            self.refresh_file_list()

    def open_item(self, path, is_dir):
        if is_dir:
            self.current_path = path
            self.path_label.configure(text=f"Jalur: {self.current_path}")
            self.refresh_file_list()
        else:
            try:
                # Menggunakan os.startfile() untuk membuka file dengan program default
                os.startfile(path)
            except AttributeError:
                if os.name == 'posix':
                    subprocess.Popen(['open', path] if os.uname().sysname == 'Darwin' else ['xdg-open', path])
                else:
                    messagebox.showinfo("Informasi", "Fitur ini tidak didukung di sistem operasi Anda.")
            except OSError as e:
                messagebox.showerror("Error", f"Tidak dapat membuka file: {e}")

    def create_folder_dialog(self):
        dialog = ctk.CTkInputDialog(text="Nama folder baru:", title="Buat Folder")
        folder_name = dialog.get_input()
        if folder_name:
            folder_path = os.path.join(self.current_path, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                self.refresh_file_list()
            else:
                messagebox.showerror("Error", "Folder sudah ada!")

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                shutil.copy(file_path, self.current_path)
                self.refresh_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mengunggah file: {e}")

    def delete_item(self, path):
        if messagebox.askyesno("Konfirmasi", f"Yakin ingin menghapus '{os.path.basename(path)}'?"):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.refresh_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus: {e}")
    
    def rename_item(self, path):
        dialog = ctk.CTkInputDialog(text=f"Nama baru untuk '{os.path.basename(path)}':", title="Ganti Nama")
        new_name = dialog.get_input()
        if new_name:
            directory, old_full_name = os.path.split(path)
            old_name, ext = os.path.splitext(old_full_name)
            
            if not os.path.isdir(path):
                new_full_name = new_name + ext
            else:
                new_full_name = new_name
                
            new_path = os.path.join(directory, new_full_name)
            
            if not os.path.exists(new_path):
                try:
                    os.rename(path, new_path)
                    self.refresh_file_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Gagal mengganti nama: {e}")
            else:
                messagebox.showerror("Error", "Nama sudah digunakan!")

    def search_files(self, event=None):
        keyword = self.search_entry.get()
        if keyword:
            self.search_results_path = []
            for root, dirs, files in os.walk(os.path.join(BASE_DIR, "storage")):
                for name in dirs + files:
                    if keyword.lower() in name.lower():
                        self.search_results_path.append(os.path.join(root, name))
            self.show_search_results()
        else:
            self.refresh_file_list()

    def show_search_results(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        if not self.search_results_path:
            ctk.CTkLabel(self.file_list_frame, text="Tidak ada hasil yang ditemukan.", fg_color="transparent").grid(row=0, column=0, pady=20)
            return

        col, row = 0, 0
        for path in self.search_results_path:
            self.create_item_widget(path, col, row)
            col += 1
            if col > 5:
                col = 0
                row += 1

    def logout(self):
        if messagebox.askyesno("Logout", "Apakah Anda yakin ingin logout?"):
            self.destroy()
            self.login_window = LoginWindow(self)
            self.wait_window(self.login_window)
            if self.login_window.login_successful:
                self.show_main_dashboard()
            else:
                self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()