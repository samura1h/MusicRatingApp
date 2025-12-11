import customtkinter as ctk
from PIL import Image
import io

class ContentFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, logic_controller, on_play_callback):
        super().__init__(master)
        self.logic = logic_controller
        self.on_play_callback = on_play_callback
        self.view_mode = "list"
        self.current_data_type = "tracks"
        self.columns_in_grid = 3

    def set_view_mode(self, mode): self.view_mode = mode; self.refresh()
    def set_data_type(self, data_type): self.current_data_type = data_type; self.refresh()

    def refresh(self, sort_by="artist"):
        for widget in self.winfo_children(): widget.destroy()
        if self.current_data_type == "tracks":
            items = self.logic.get_playlist(sort_by)
            self._draw_tracks(items)
        elif self.current_data_type == "artists":
            items = self.logic.get_artists()
            if self.view_mode == "grid": self._draw_groups_grid(items, "artist")
            else: self._draw_groups_list(items, "artist")
        elif self.current_data_type == "albums":
            items = self.logic.get_albums()
            if self.view_mode == "grid": self._draw_groups_grid(items, "album")
            else: self._draw_groups_list(items, "album")

    # === DRAW MIXED TOP CHART ===
    def draw_top_chart(self, data, header):
        # Очищаємо екран
        for w in self.winfo_children(): w.destroy()
        
        # Заголовок
        ctk.CTkLabel(self, text=header, font=("Arial", 20, "bold"), text_color="#daa520").pack(pady=15)
        
        if not data:
            ctk.CTkLabel(self, text="Not enough data yet.", font=("Arial", 14)).pack(pady=20)
            return

        # Малюємо список
        for i, item in enumerate(data):
            # Розпаковка даних з TopItemData (структура з C++)
            # name=Title, secondary=Artist, rating=Rating, cover_path=File Path (для треків)
            title = item['name']
            artist = item['secondary']
            rating = item['rating']
            file_path = item['cover_path'] # У C++ для треків сюди записується шлях до файлу
            
            # Текст кнопки
            text = f"{i+1}. {artist} - {title} | ⭐ {rating:.1f}"
            
            # Команда для відтворення
            # Ми передаємо file_path напряму в логіку програвання
            cmd = lambda p=file_path: self.logic.play_file(p)
            
            # Створюємо кнопку
            btn = ctk.CTkButton(
                self, 
                text=text, 
                anchor="w",
                height=45, 
                fg_color="transparent", 
                border_width=1, 
                border_color="#444",
                font=("Arial", 13, "bold"), 
                hover_color="#333",
                command=cmd  # Тепер по кліку грає музика
            )
            btn.pack(fill="x", padx=15, pady=2)

    # === TRACKS DRAWING ===
    def _draw_tracks(self, tracks, header_text=None):
        if header_text:
             for w in self.winfo_children(): w.destroy()
             ctk.CTkLabel(self, text=header_text, font=("Arial", 18, "bold")).pack(pady=10)
        
        default_icon = ctk.CTkImage(Image.new("RGBA", (30, 30), (50, 50, 50, 0)), size=(30, 30))
        row, col = 0, 0
        for i, t in enumerate(tracks):
            path, title, artist = t[1], t[2], t[3]; album, genre, rating = t[4], t[5], t[7]
            m, s = divmod(int(t[6]), 60)
            display_text = f"{artist:<15} - {title:<25} | {m:02}:{s:02} | {album:<15} | {genre:<10} | ⭐ {rating:.1f}"
            cmd = lambda playlist=tracks, idx=i: self.on_play_callback(playlist, idx)

            if self.view_mode == "list":
                icon = default_icon
                try:
                    d = self.logic.get_cover_data(path)
                    if d: icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(30, 30))
                except: pass
                ctk.CTkButton(self, text=display_text, image=icon, compound="left", anchor="w", height=40, fg_color="transparent", hover_color="#3b3b55", font=("Consolas", 12), command=cmd).pack(fill="x", padx=5)
                ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x")
            else:
                l_icon = None
                try:
                    d = self.logic.get_cover_data(path)
                    if d: l_icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(120, 120))
                except: pass
                btn = ctk.CTkButton(self, text=f"{title}\n{artist}\n⭐{rating:.1f}", image=l_icon, compound="top", width=150, height=160, fg_color="#2b2b40", hover_color="#3b3b55", command=cmd)
                btn.grid(row=row, column=col, padx=10, pady=10)
                col += 1; 
                if col >= self.columns_in_grid: col = 0; row += 1

    # === GROUPS (Artist/Album) ===
    def _draw_groups_list(self, items, type_g):
        for item in items:
            name, sec, count, path = item
            text = f"{name} ({count} tracks)"
            if type_g == "album": text = f"{name} - {sec} ({count} tracks)"
            cmd = lambda n=name, t=type_g: self._open_group(t, n)
            ctk.CTkButton(self, text=text, anchor="w", height=40, fg_color="transparent", hover_color="#3b3b55", font=("Arial", 14), command=cmd).pack(fill="x", padx=5)
            ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x")

    def _draw_groups_grid(self, items, type_g):
        row, col = 0, 0
        for item in items:
            name, sec, count, path = item
            icon = None
            try:
                d = self.logic.get_cover_data(path)
                if d: icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(120, 120))
            except: pass
            label = f"{name}\n{count} tracks"
            if type_g == "album": label = f"{name}\n{sec}"
            cmd = lambda n=name, t=type_g: self._open_group(t, n)
            btn = ctk.CTkButton(self, text=label, image=icon, compound="top", width=150, height=160, fg_color="#2b2b40", hover_color="#3b3b55", command=cmd)
            btn.grid(row=row, column=col, padx=10, pady=10)
            col += 1; 
            if col >= self.columns_in_grid: col = 0; row += 1

    # У файлі Frontend/content_view.py

    def _draw_tracks(self, tracks, header_text=None):
        if header_text:
             for w in self.winfo_children(): w.destroy()
             ctk.CTkLabel(self, text=header_text, font=("Arial", 18, "bold")).pack(pady=10)
        
        # Використовуємо прозору іконку, якщо немає обкладинки
        default_icon = ctk.CTkImage(Image.new("RGBA", (30, 30), (50, 50, 50, 0)), size=(30, 30))
        
        row, col = 0, 0
        for i, t in enumerate(tracks):
            # Розпаковка даних
            # 1:path, 2:title, 3:artist, 4:album, 5:genre, 6:duration, 7:rating
            path = t[1]
            # Обрізаємо занадто довгі назви, щоб не ламали таблицю
            title = (t[2][:30] + '..') if len(t[2]) > 30 else t[2]
            artist = (t[3][:20] + '..') if len(t[3]) > 20 else t[3]
            album = (t[4][:20] + '..') if len(t[4]) > 20 else t[4]
            genre = (t[5][:15] + '..') if len(t[5]) > 15 else t[5]
            
            # Форматуємо час
            m, s = divmod(int(t[6]), 60)
            time_str = f"{m:02}:{s:02}"
            
            # === ГОЛОВНЕ: РІВНОМІРНЕ ФОРМАТУВАННЯ ===
            # Використовуємо f-string з відступами
            # <25 = 25 символів вліво, ^10 = 10 символів по центру
            display_text = f"{artist:<22} | {title:<32} | {time_str:^7} | {album:<22} | {genre:<15} | ⭐ {t[7]:.1f}"
            
            cmd = lambda playlist=tracks, idx=i: self.on_play_callback(playlist, idx)

            if self.view_mode == "list":
                icon = default_icon
                try:
                    d = self.logic.get_cover_data(path)
                    if d: icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(30, 30))
                except: pass

                btn = ctk.CTkButton(
                    self, 
                    text=display_text, 
                    image=icon, 
                    compound="left", 
                    anchor="w", 
                    height=40, 
                    fg_color="transparent", 
                    hover_color="#3b3b55", 
                    font=("Consolas", 13), # Моноширинний шрифт ОБОВ'ЯЗКОВО!
                    command=cmd
                )
                btn.pack(fill="x", padx=5)
                # Тонка лінія-розділювач
                ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=10)
            
            else:
                # Grid mode (плитка) - тут без змін
                l_icon = None
                try:
                    d = self.logic.get_cover_data(path)
                    if d: l_icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(120, 120))
                except: pass
                btn = ctk.CTkButton(self, text=f"{title}\n{artist}\n⭐{t[7]:.1f}", image=l_icon, compound="top", width=150, height=160, fg_color="#2b2b40", hover_color="#3b3b55", command=cmd)
                btn.grid(row=row, column=col, padx=10, pady=10)
                col += 1; 
                if col >= self.columns_in_grid: col = 0; row += 1

    def _open_group(self, g_type, name):
        for w in self.winfo_children(): w.destroy()
        back_type = "artists" if g_type == "artist" else "albums"
        ctk.CTkButton(self, text="⬅ BACK TO LIST", fg_color="darkred", command=lambda: self.set_data_type(back_type)).pack(fill="x", pady=5)
        ctk.CTkLabel(self, text=f"Tracks by: {name}", font=("Arial", 18, "bold")).pack(pady=10)
        tracks = self.logic.get_tracks_filtered(g_type, name)
        self._draw_tracks(tracks)