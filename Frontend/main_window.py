import customtkinter as ctk
from tkinter import filedialog, messagebox
from Frontend.player import PlayerFrame
from Frontend.content_view import ContentFrame

class MusicAppUI(ctk.CTk):
    def __init__(self, logic_controller):
        super().__init__()
        self.logic = logic_controller
        self.title("Music System Ultimate")
        self.geometry("1100x750")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_layout()

    def _setup_layout(self):
        # 1. ЛІВА ПАНЕЛЬ (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="MEDIA LIBRARY", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="📂 Add Folder", command=self.add_folder).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="🔄 Show All Tracks", command=self.refresh_all).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="🗑️ Clear Library", fg_color="darkred", hover_color="#800000",
                      command=self.clear_all_data).pack(pady=20, padx=20, side="bottom")

        ctk.CTkLabel(self.sidebar, text="Browser:").pack(pady=(20, 5))
        self.seg_tabs = ctk.CTkSegmentedButton(self.sidebar, values=["Tracks", "Artists", "Albums"],
                                               command=self.change_tab)
        self.seg_tabs.set("Tracks")
        self.seg_tabs.pack(padx=10)

        ctk.CTkLabel(self.sidebar, text="Auto-Playlists:", font=("Arial", 14, "bold")).pack(pady=(30, 10))
        ctk.CTkButton(self.sidebar, text="🔥 TOP 10 Best", fg_color="#D4AF37", text_color="black",
                      command=lambda: self.show_playlist("best")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="💩 TOP 10 Worst", fg_color="#555",
                      command=lambda: self.show_playlist("worst")).pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="View Mode:").pack(side="bottom", pady=5)
        self.seg_view = ctk.CTkSegmentedButton(self.sidebar, values=["List", "Grid"], command=self.change_view)
        self.seg_view.set("List")
        self.seg_view.pack(side="bottom", padx=10, pady=20)

        # 2. ПРАВА ПАНЕЛЬ (Main Content)
        self.right = ctk.CTkFrame(self, fg_color="transparent")
        self.right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.right.grid_columnconfigure(0, weight=1)
        # ВАЖЛИВО: Тепер контент знаходиться в рядку 1 (раніше був 2), тому розтягуємо рядок 1
        self.right.grid_rowconfigure(1, weight=1)

        # 2.1 Sort Header (Тепер Row 0, бо пошук видалено)
        self.sort_frame = ctk.CTkFrame(self.right, height=30, fg_color="#222")
        self.sort_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.setup_sort_buttons()

        # 2.2 Content (Тепер Row 1)
        self.content = ContentFrame(self.right, self.logic, on_play_callback=self.play_track)
        self.content.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # 2.3 Player (Тепер Row 2 - фіксований знизу)
        self.player = PlayerFrame(self.right, self.logic, on_rate_callback=self.refresh_current, on_delete_callback=None)
        self.player.grid(row=2, column=0, sticky="ew")

        self.refresh_all()

    # ... решта методів (add_folder, setup_sort_buttons і т.д.) залишаються без змін ...
    # ТІЛЬКИ видали методи perform_search та clear_search, бо кнопок більше немає.
    
    def setup_sort_buttons(self):
        for w in self.sort_frame.winfo_children(): w.destroy()
        cols = [("Artist", "artist"), ("Title", "title"), ("Time", "duration"), ("Album", "album"), ("Rating", "rating")]
        for col, key in cols:
            ctk.CTkButton(self.sort_frame, text=col, fg_color="transparent", hover_color="#333", anchor="w",
                          command=lambda k=key: self.sort_tracks(k)).pack(side="left", fill="y", expand=True)

    def change_tab(self, value):
        self.content.set_data_type(value.lower())
        if value == "Tracks": self.sort_frame.grid()
        else: self.sort_frame.grid_remove()

    def sort_tracks(self, key): self.content.refresh(sort_by=key)
    
    def clear_all_data(self):
        if messagebox.askyesno("Confirm", "Delete ALL tracks?"):
            self.logic.clear_database()
            self.refresh_all()

    def add_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.logic.scan_directory(d)
            self.refresh_all()

    def refresh_all(self):
        self.content.set_data_type("tracks")
        self.content.refresh()

    def show_playlist(self, mode):
        # Ховаємо панель сортування, бо це спец-плейлист
        self.sort_frame.grid_remove()
        # 1. Беремо ТІЛЬКИ треки (параметр "tracks")
        # C++ вже має LIMIT 10 у SQL запиті, тому повернеться рівно 10 пісень
        tracks = self.logic.get_advanced_top("tracks", mode)
        # 2. Формуємо заголовок
        header = "🔥 TOP 10 BEST TRACKS" if mode == "best" else "💩 TOP 10 WORST TRACKS"
        # 3. Малюємо тільки ці треки
        self.content.draw_top_chart(tracks, header)

    def change_view(self, val): self.content.set_view_mode("list" if val == "List" else "grid")
    def refresh_current(self): self.content.refresh()
    def play_track(self, playlist, index): self.player.load_playlist(playlist, index)