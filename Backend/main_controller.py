import ctypes
from ctypes import *
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

# ... (Структури TrackData, GroupData, TopItemData ТІ САМІ) ...
class TrackData(Structure):
    _fields_ = [("id", c_int), ("path", c_char * 256), ("title", c_char * 256), ("artist", c_char * 256), ("album", c_char * 256), ("genre", c_char * 100), ("duration", c_double), ("rating", c_double), ("rate_melody", c_int), ("rate_rhythm", c_int), ("rate_vocals", c_int), ("rate_lyrics", c_int), ("rate_arrange", c_int), ("has_vocals", c_int), ("has_lyrics", c_int)]
class GroupData(Structure):
    _fields_ = [("name", c_char * 256), ("secondary", c_char * 256), ("count", c_int), ("cover_path", c_char * 256)]
class TopItemData(Structure):
    _fields_ = [("name", c_char * 256), ("secondary", c_char * 256), ("rating", c_double), ("cover_path", c_char * 256), ("type", c_int)]

class MainController:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dll_path = os.path.join(self.base_path, "Backend", "Database", "cpp_src", "backend.dll")
        self.lib = None
        
        # === ЗМІННІ ДЛЯ СОРТУВАННЯ ===
        self.current_sort_col = "artist"
        self.current_sort_order = "ASC"
        
        self._load_dll()

    def _load_dll(self):
        if not os.path.exists(self.dll_path): return
        try:
            self.lib = CDLL(self.dll_path)
            self.lib.init_system()
            
            # --- ЛОГІКА БАЗИ ДАНИХ ---
            self.lib.logic_add_track.argtypes = [POINTER(TrackData)]; self.lib.logic_add_track.restype = c_bool
            self.lib.logic_fetch_next.argtypes = [POINTER(TrackData)]; self.lib.logic_fetch_next.restype = c_bool
            self.lib.logic_prepare_query.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
            
            # --- АУДІО (ЦЕ КРИТИЧНО ДЛЯ СЛАЙДЕРА!) ---
            # 1. audio_get_pos повертає double, треба це вказати явно:
            if hasattr(self.lib, 'audio_get_pos'):
                self.lib.audio_get_pos.argtypes = []
                self.lib.audio_get_pos.restype = c_double  # <--- ОСЬ ЦЬОГО НЕ ВИСТАЧАЛО

            # 2. audio_is_playing повертає bool:
            if hasattr(self.lib, 'audio_is_playing'):
                self.lib.audio_is_playing.argtypes = []
                self.lib.audio_is_playing.restype = c_bool

            # 3. audio_set_pos приймає шлях і double:
            if hasattr(self.lib, 'audio_set_pos'):
                self.lib.audio_set_pos.argtypes = [c_char_p, c_double]
                self.lib.audio_set_pos.restype = None

            # --- Інші налаштування (рейтинг, пошук і т.д.) ---
            self.lib.logic_update_rating.argtypes = [c_char_p, c_double, c_int, c_int, c_int, c_int, c_int, c_int, c_int]
            self.lib.logic_update_rating.restype = c_bool

            if hasattr(self.lib, 'logic_prepare_advanced_top'): 
                self.lib.logic_prepare_advanced_top.argtypes = [c_int, c_int]
                self.lib.logic_fetch_top_item.argtypes = [POINTER(TopItemData)]
                self.lib.logic_fetch_top_item.restype = c_bool

            if hasattr(self.lib, 'logic_prepare_group_query'):
                self.lib.logic_prepare_group_query.argtypes = [c_int]
                self.lib.logic_fetch_next_group.argtypes = [POINTER(GroupData)]
                self.lib.logic_fetch_next_group.restype = c_bool
                
            if hasattr(self.lib, 'logic_search_tracks'):
                 self.lib.logic_search_tracks.argtypes = [c_char_p]

            if hasattr(self.lib, 'logic_toggle_shuffle'):
                self.lib.logic_toggle_shuffle.restype = c_bool
            if hasattr(self.lib, 'logic_toggle_repeat'):
                self.lib.logic_toggle_repeat.restype = c_bool

            print("✅ C++ Backend loaded correctly.")
        except Exception as e: print(f"❌ Error loading DLL: {e}")

    # === DATABASE ===
    def clear_database(self):
        if self.lib: self.lib.logic_clear_database()

    def scan_directory(self, folder_path):
        if not self.lib: return 0
        count = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):
                    if self._add_track(os.path.join(root, file)): count += 1
        return count

    def _add_track(self, path):
        try:
            audio = MP3(path, ID3=ID3); tags = audio.tags or ID3(); t = TrackData()
            t.path = path.encode('mbcs'); t.title = str(tags.get('TIT2', os.path.basename(path))).encode('mbcs')
            t.artist = str(tags.get('TPE1', 'Unknown Artist')).encode('mbcs'); t.album = str(tags.get('TALB', '-')).encode('mbcs')
            t.genre = str(tags.get('TCON', '-')).encode('mbcs'); t.duration = audio.info.length
            return self.lib.logic_add_track(byref(t))
        except: return False

    # === FETCH WITH SORT TOGGLE ===
    def get_playlist(self, sort_by=None):
        # Якщо передали новий стовпець - сортуємо ASC
        # Якщо той самий - міняємо порядок (ASC <-> DESC)
        if sort_by:
            if sort_by == self.current_sort_col:
                self.current_sort_order = "DESC" if self.current_sort_order == "ASC" else "ASC"
            else:
                self.current_sort_col = sort_by
                self.current_sort_order = "ASC" # Новий стовпець завжди починаємо з ASC
        
        return self._fetch_tracks(self.current_sort_col, self.current_sort_order, None, None)

    def get_tracks_filtered(self, f_type, f_val): return self._fetch_tracks("title", "ASC", f_type, f_val)
    def search_tracks(self, query):
        if not self.lib: return []
        self.lib.logic_search_tracks(query.encode('utf-8'))
        return self._fetch_all_raw()

    def _fetch_tracks(self, sort, order, f_col, f_val):
        if not self.lib: return []
        f_col_p = f_col.encode('utf-8') if f_col else None
        f_val_p = f_val.encode('utf-8') if f_val else None
        self.lib.logic_prepare_query(sort.encode('utf-8'), order.encode('utf-8'), f_col_p, f_val_p)
        return self._fetch_all_raw()

    def _fetch_all_raw(self):
        res = []
        t = TrackData()
        while self.lib.logic_fetch_next(byref(t)):
            res.append((t.id, t.path.decode('mbcs', 'ignore'), t.title.decode('mbcs', 'ignore'), t.artist.decode('mbcs', 'ignore'), t.album.decode('mbcs', 'ignore'), t.genre.decode('mbcs', 'ignore'), t.duration, t.rating, t.rate_melody, t.rate_rhythm, t.rate_vocals, t.rate_lyrics, t.rate_arrange, t.has_vocals, t.has_lyrics))
        return res

    def get_advanced_top(self, entity, mode):
        if not self.lib: return []
        e_code = 0; 
        if entity == "albums": e_code = 1
        elif entity == "artists": e_code = 2
        m_code = 1 if mode == "best" else 2
        self.lib.logic_prepare_advanced_top(e_code, m_code)
        res = []
        item = TopItemData()
        while self.lib.logic_fetch_top_item(byref(item)):
            res.append({"name": item.name.decode('mbcs', 'ignore'), "secondary": item.secondary.decode('mbcs', 'ignore'), "rating": item.rating, "cover_path": item.cover_path.decode('mbcs', 'ignore'), "type": item.type})
        return res

    def get_artists(self): return self._fetch_groups(1)
    def get_albums(self): return self._fetch_groups(2)
    def _fetch_groups(self, mode):
        if not self.lib: return []
        self.lib.logic_prepare_group_query(mode)
        res = []
        g = GroupData()
        while self.lib.logic_fetch_next_group(byref(g)):
            res.append((g.name.decode('mbcs', 'ignore'), g.secondary.decode('mbcs', 'ignore'), g.count, g.cover_path.decode('mbcs', 'ignore')))
        return res

    def calculate_save_rating(self, path, data):
        if not self.lib: return False
        total = (data['melody'] + data['rhythm'] + data['arrange']); count = 3
        if data['has_vocals']: total += data['vocals']; count += 1
        if data['has_lyrics']: total += data['lyrics']; count += 1
        avg = total / count if count > 0 else 0
        return self.lib.logic_update_rating(path.encode('mbcs'), c_double(avg), c_int(data['melody']), c_int(data['rhythm']), c_int(data['vocals']), c_int(data['lyrics']), c_int(data['arrange']), c_int(data.get('has_vocals', 1)), c_int(data.get('has_lyrics', 1)))

    def get_cover_data(self, path):
        try:
            audio = MP3(path, ID3=ID3)
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC): return tag.data
        except: pass
        return None

    def play_file(self, path): 
        if self.lib: self.lib.audio_play(path.encode('mbcs'))
    def toggle_pause(self): self.lib.audio_pause()
    def is_playing(self): return self.lib.audio_is_playing() if self.lib else False
    def get_audio_time(self): return self.lib.audio_get_pos() if self.lib else 0.0
    def set_time(self, path, s): self.lib.audio_set_pos(path.encode('mbcs'), c_double(s))
    
    def toggle_shuffle(self): return self.lib.logic_toggle_shuffle() if self.lib else False
    def toggle_repeat(self): return self.lib.logic_toggle_repeat() if self.lib else False
    
    def get_next_index(self, c, t): return self.lib.logic_get_next_index(c, t) if self.lib else -1
    def get_prev_index(self, c, t): return self.lib.logic_get_prev_index(c, t) if self.lib else -1