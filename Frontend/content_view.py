import customtkinter as ctk
from PIL import Image
import io
from mutagen.mp3 import MP3

class ContentFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, logic_controller, on_play_callback):
        super().__init__(master)
        self.logic = logic_controller
        self.on_play_callback = on_play_callback
        
        self.current_data_type = "tracks"
        self.columns_in_grid = 3 
        
        # Список створених віджетів для очищення пам'яті
        self.generated_widgets = [] 

    def set_data_type(self, data_type): 
        self.current_data_type = data_type 
        self.refresh()

    def clear_content(self):
        """Повне очищення перед зміною вигляду"""
        for widget in self.generated_widgets:
            try:
                widget.destroy()
            except: pass
        self.generated_widgets.clear()
        
        self.update_idletasks()
        self._parent_canvas.yview_moveto(0)

    def refresh(self, sort_by="artist"):
        self.clear_content()

        # === ЛОГІКА ВИБОРУ РЕЖИМУ (LIST vs GRID) ===
        
        # 1. ТРЕКИ -> СПИСОК
        if self.current_data_type == "tracks":
            # Тут можна додати заголовок для треків, якщо треба
            items = self.logic.get_playlist(sort_by)
            self._draw_list_mode(items)

        # 2. АРТИСТИ -> ПЛИТКА (ЗМІНЕНО ТУТ)
        elif self.current_data_type == "artists":
            items = self.logic.get_artists()
            # Додаємо заголовок "ARTISTS"
            self._draw_grid_mode(items, "artist", header_text="🎤 ARTISTS LIBRARY")

        # 3. АЛЬБОМИ -> ПЛИТКА (ЗМІНЕНО ТУТ)
        elif self.current_data_type == "albums":
            items = self.logic.get_albums()
            # Додаємо заголовок "ALBUMS"
            self._draw_grid_mode(items, "album", header_text="💿 ALBUMS LIBRARY")
            
        # 4. АЛЬБОМИ КОНКРЕТНОГО АРТИСТА -> ПЛИТКА (+ Навігація)
        elif self.current_data_type.startswith("albums_by_"):
            artist_name = self.current_data_type.replace("albums_by_", "")
            items = self.logic.get_artist_albums(artist_name)
            
            back_cmd = lambda: self.set_data_type("artists")
            header_text = f"Albums by: {artist_name}"
            
            self._draw_grid_mode(items, "album", context_artist=artist_name, 
                                 header_text=header_text, back_cmd=back_cmd, back_btn_text="⬅ BACK TO ARTISTS")

    # === ОБРОБКА КЛІКІВ (НАВІГАЦІЯ) ===
    def _handle_group_click(self, g_type, name, context_artist=None):
        if g_type == "artist":
            self.current_data_type = f"albums_by_{name}"
            self.refresh()
            
        elif g_type == "album":
            self.clear_content()
            
            if context_artist:
                back_cmd = lambda: self._handle_back_to_artist_albums(context_artist)
                back_text = f"⬅ BACK TO {context_artist.upper()}"
            else:
                back_cmd = lambda: self.set_data_type("albums")
                back_text = "⬅ BACK TO ALBUMS"

            btn_back = ctk.CTkButton(self, text=back_text, fg_color="darkred", hover_color="#800000", command=back_cmd)
            btn_back.pack(fill="x", pady=5)
            self.generated_widgets.append(btn_back)
            
            lbl = ctk.CTkLabel(self, text=f"Album: {name}", font=("Arial", 18, "bold"), text_color="#daa520")
            lbl.pack(pady=10)
            self.generated_widgets.append(lbl)
            
            # Отримуємо і малюємо треки
            tracks = self.logic.get_tracks_filtered("album", name)
            self._draw_list_mode(tracks)

    def _handle_back_to_artist_albums(self, artist_name):
        self.current_data_type = f"albums_by_{artist_name}"
        self.refresh()

    # ==========================================
    # РЕЖИМ ПЛИТКИ (GRID) - Для Альбомів/Артистів
    # ==========================================
    def _draw_grid_mode(self, items, type_g, context_artist=None, header_text=None, back_cmd=None, back_btn_text="BACK"):
        row_offset = 0

        # Кнопка "Назад"
        if back_cmd:
            btn = ctk.CTkButton(self, text=back_btn_text, fg_color="darkred", hover_color="#800000", command=back_cmd)
            btn.grid(row=row_offset, column=0, columnspan=self.columns_in_grid, sticky="ew", pady=5, padx=5)
            self.generated_widgets.append(btn)
            row_offset += 1

        # ЗАГОЛОВОК (Artist / Album / Etc)
        if header_text:
            lbl = ctk.CTkLabel(self, text=header_text, font=("Arial", 20, "bold"), text_color="#daa520")
            lbl.grid(row=row_offset, column=0, columnspan=self.columns_in_grid, pady=(10, 20))
            self.generated_widgets.append(lbl)
            row_offset += 1

        if not items:
            l = ctk.CTkLabel(self, text="No items found.", text_color="gray")
            l.grid(row=row_offset, column=0, columnspan=self.columns_in_grid, pady=20)
            self.generated_widgets.append(l)
            return

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
            
            cmd = lambda n=name, t=type_g: self._handle_group_click(t, n, context_artist)
            
            btn = ctk.CTkButton(self, text=label, image=icon, compound="top", width=150, height=160, 
                                fg_color="#2b2b40", hover_color="#3b3b55", command=cmd)
            
            btn.grid(row=row + row_offset, column=col, padx=10, pady=10)
            self.generated_widgets.append(btn)
            
            col += 1
            if col >= self.columns_in_grid: 
                col = 0; row += 1

    # ==========================================
    # РЕЖИМ СПИСКУ (LIST) - Для Треків
    # ==========================================
    def _draw_list_mode(self, tracks):
        if not tracks:
            l = ctk.CTkLabel(self, text="No tracks found.", text_color="gray")
            l.pack(pady=20)
            self.generated_widgets.append(l)
            return

        default_icon = ctk.CTkImage(Image.new("RGBA", (30, 30), (50, 50, 50, 0)), size=(30, 30))
        
        for i, t in enumerate(tracks):
            # t[1]=path, t[2]=title, t[3]=artist, t[4]=album, t[6]=duration, t[7]=rating
            path, title, artist = t[1], t[2], t[3]; album, rating = t[4], t[7]
            m, s = divmod(int(t[6]), 60)
            
            title_s = (title[:25] + '..') if len(title) > 25 else title
            artist_s = (artist[:18] + '..') if len(artist) > 18 else artist
            album_s = (album[:18] + '..') if len(album) > 18 else album 

            display_text = f"{artist_s:<20} | {title_s:<25} | {m:02}:{s:02} | {album_s:<20} | ⭐ {rating:.1f}"
            
            cmd = lambda playlist=tracks, idx=i: self.on_play_callback(playlist, idx)

            icon = default_icon
            try:
                d = self.logic.get_cover_data(path)
                if d: icon = ctk.CTkImage(Image.open(io.BytesIO(d)), size=(30, 30))
            except: pass

            btn = ctk.CTkButton(self, text=display_text, image=icon, compound="left", anchor="w", 
                                height=40, fg_color="transparent", hover_color="#3b3b55", 
                                font=("Consolas", 13), command=cmd)
            btn.pack(fill="x", padx=5)
            self.generated_widgets.append(btn)
            
            div = ctk.CTkFrame(self, height=1, fg_color="#333")
            div.pack(fill="x", padx=10)
            self.generated_widgets.append(div)

    # ==========================================
    # ТОП ЧАРТ (Завжди Список + Виправлення Таймера)
    # ==========================================
    def draw_top_chart(self, data, header):
        self.clear_content()
        
        l = ctk.CTkLabel(self, text=header, font=("Arial", 20, "bold"), text_color="#daa520")
        l.pack(pady=15)
        self.generated_widgets.append(l)
        
        if not data:
            l2 = ctk.CTkLabel(self, text="Not enough data yet.", font=("Arial", 14))
            l2.pack(pady=20)
            self.generated_widgets.append(l2)
            return

        converted_playlist = []
        for item in data:
            duration = 0
            try:
                audio = MP3(item['cover_path'])
                duration = audio.info.length
            except: pass

            track_tup = (
                0,                  # id
                item['cover_path'], # path
                item['name'],       # title
                item['secondary'],  # artist
                "-",                # album
                "Top Chart",        # genre
                duration,           # duration
                item['rating'],     # rating
                0,0,0,0,0,0,0       # details
            )
            converted_playlist.append(track_tup)

        for i, item in enumerate(data):
            title = item['name']
            artist = item['secondary']
            rating = item['rating']
            
            text = f"{i+1}. {artist} - {title} | ⭐ {rating:.1f}"
            
            cmd = lambda playlist=converted_playlist, idx=i: self.on_play_callback(playlist, idx)
            
            btn = ctk.CTkButton(self, text=text, anchor="w", height=45, fg_color="transparent", 
                                border_width=1, border_color="#444", font=("Arial", 13, "bold"), 
                                hover_color="#333", command=cmd)
            btn.pack(fill="x", padx=15, pady=2)
            self.generated_widgets.append(btn)