import customtkinter as ctk
import time
from Frontend.rating_window import RatingWindow

class PlayerFrame(ctk.CTkFrame):
    def __init__(self, master, logic_controller, on_rate_callback, on_delete_callback):
        super().__init__(master)
        self.logic = logic_controller
        self.on_rate_callback = on_rate_callback
        self.on_delete_callback = on_delete_callback
        
        self.playlist = []      
        self.current_index = -1   
        self.current_track = None
        
        self.is_dragging = False
        self.last_seek_time = 0      
        self.seek_target_value = 0  
        
        self._setup_ui()
        self.update_progress()

    def _setup_ui(self):
        self.top = ctk.CTkFrame(self, fg_color="transparent")
        self.top.pack(fill="x", pady=5)
        
        self.lbl_title = ctk.CTkLabel(self.top, text="No Track", font=("Arial", 14, "bold"))
        self.lbl_title.pack()
        self.lbl_artist = ctk.CTkLabel(self.top, text="", text_color="gray")
        self.lbl_artist.pack()

        self.seek = ctk.CTkSlider(self, from_=0, to=100, command=self.on_seek)
        self.seek.bind("<ButtonRelease-1>", self.on_release)
        self.seek.set(0)
        self.seek.pack(fill="x", padx=20, pady=5)
        
        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_time.pack()

        self.ctrl = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl.pack(pady=5)

        self.btn_shuf = ctk.CTkButton(self.ctrl, text="🔀", width=40, fg_color="transparent", border_width=1, command=self.act_shuffle)
        self.btn_shuf.pack(side="left", padx=5)
        
        ctk.CTkButton(self.ctrl, text="⏮", width=40, command=self.act_prev, font=("Arial", 16)).pack(side="left", padx=5)
        
        self.btn_play = ctk.CTkButton(self.ctrl, text="▶", width=60, command=self.act_play_pause, font=("Arial", 16))
        self.btn_play.pack(side="left", padx=10)
        
        ctk.CTkButton(self.ctrl, text="⏭", width=40, command=self.act_next, font=("Arial", 16)).pack(side="left", padx=5)
        
        self.btn_rep = ctk.CTkButton(self.ctrl, text="🔁", width=40, fg_color="transparent", border_width=1, command=self.act_repeat)
        self.btn_rep.pack(side="left", padx=5)
        
        ctk.CTkButton(self, text="⭐ RATE", height=25, fg_color="#daa520", text_color="black", command=self.open_rate).pack(pady=5)

    def load_playlist(self, tracks, start_index=0):
        self.playlist = tracks
        self.play_index(start_index)

    def play_index(self, index):
        if 0 <= index < len(self.playlist):
            new_track = self.playlist[index]
            if self.current_track and self.current_track[1] == new_track[1] and self.logic.is_playing():
                self.current_index = index
                return

            self.current_index = index
            self.current_track = new_track
            
            self.lbl_title.configure(text=self.current_track[2] if self.current_track[2] else "Unknown")
            self.lbl_artist.configure(text=self.current_track[3] if self.current_track[3] else "Unknown")
            
            duration = self.current_track[6]
            if duration <= 0: duration = 100
            
            self.seek.configure(to=duration) 
            self.seek.set(0)
            
            self.logic.play_file(self.current_track[1])
            self.btn_play.configure(text="⏸")

    def update_progress(self):
        try:
            if self.logic.is_playing() and not self.is_dragging and self.current_track:
                real_pos = self.logic.get_audio_time()
                dur = self.current_track[6]

                time_since_seek = time.time() - self.last_seek_time
                # Плавність після перемотки
                if time_since_seek < 1.5:
                    current_pos = self.seek_target_value + time_since_seek
                else:
                    if real_pos == 0 and self.seek.get() > 2:
                        current_pos = self.seek.get() + 1
                    else:
                        current_pos = real_pos

                self.seek.set(current_pos)

                m, s = divmod(int(current_pos), 60)
                tm, ts = divmod(int(dur), 60)
                self.lbl_time.configure(text=f"{m:02}:{s:02} / {tm:02}:{ts:02}")
                
                # Автоперемикання
                if dur > 0 and current_pos >= dur - 0.5:
                    self.act_next()

        except Exception as e:
            print(f"Error in UI update: {e}")
        finally:
            self.after(1000, self.update_progress)

    def on_seek(self, val):
        self.is_dragging = True

    def on_release(self, e):
        if self.current_track:
            target_time = self.seek.get()
            self.logic.set_time(self.current_track[1], target_time)
            self.last_seek_time = time.time()
            self.seek_target_value = target_time
            
            dur = self.current_track[6]
            m, s = divmod(int(target_time), 60); tm, ts = divmod(int(dur), 60)
            self.lbl_time.configure(text=f"{m:02}:{s:02} / {tm:02}:{ts:02}")
        self.is_dragging = False

    def act_play_pause(self):
        self.logic.toggle_pause()
        self.btn_play.configure(text="⏸" if self.logic.is_playing() else "▶")

    def act_shuffle(self):
        st = self.logic.toggle_shuffle()
        self.btn_shuf.configure(fg_color="#1f538d" if st else "transparent")

    def act_repeat(self):
        st = self.logic.toggle_repeat()
        self.btn_rep.configure(fg_color="#1f538d" if st else "transparent")

    def act_next(self):
        if not self.playlist: return
        idx = self.logic.get_next_index(self.current_index, len(self.playlist))
        if idx != -1: self.play_index(idx)

    def act_prev(self):
        if not self.playlist: return
        idx = self.logic.get_prev_index(self.current_index, len(self.playlist))
        self.play_index(idx)

    def open_rate(self):
        if not self.current_track: return
        try:
            current_data = {
                'melody': self.current_track[8], 'rhythm': self.current_track[9],
                'vocals': self.current_track[10], 'lyrics': self.current_track[11],
                'arrange': self.current_track[12], 'has_vocals': self.current_track[13],
                'has_lyrics': self.current_track[14]
            }
        except: current_data = None
        RatingWindow(self, self.logic, self.current_track[1], current_data, self.on_rate_callback)