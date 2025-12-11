import ctypes
from ctypes import *
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

class TrackData(Structure):
    _fields_ = [
        ("id", c_int),
        ("path", c_char * 256),
        ("title", c_char * 256),
        ("artist", c_char * 256),
        ("album", c_char * 256),
        ("genre", c_char * 100),
        ("duration", c_double),
        ("rating", c_double),
        ("rate_melody", c_int), ("rate_rhythm", c_int),
        ("rate_vocals", c_int), ("rate_lyrics", c_int),
        ("rate_arrange", c_int), ("has_vocals", c_int), ("has_lyrics", c_int)
    ]

class DatabaseClient:
    def __init__(self):
        dll_path = os.path.join(os.path.dirname(__file__), "cpp_src", "music_db.dll")
        try:
            self.clib = CDLL(dll_path)
            self.clib.init_db()
            self.clib.add_track_cpp.argtypes = [POINTER(TrackData)]
            self.clib.add_track_cpp.restype = c_bool
            self.clib.fetch_next_track.argtypes = [POINTER(TrackData)]
            self.clib.fetch_next_track.restype = c_bool
            self.clib.get_avg_rating_cpp.restype = c_double
        except Exception as e:
            print(f"Error loading DB DLL: {e}")
            self.clib = None

    def scan_directory(self, folder):
        if not self.clib: return 0
        count = 0
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith('.mp3'):
                    if self._add_track(os.path.join(root, f)): count += 1
        return count

    def _add_track(self, path):
        meta = self._get_meta(path)
        t = TrackData()
        t.path = meta["path"].encode('mbcs', 'ignore')
        t.title = meta["title"].encode('mbcs', 'ignore')
        t.artist = meta["artist"].encode('mbcs', 'ignore')
        t.album = meta["album"].encode('mbcs', 'ignore')
        t.genre = meta["genre"].encode('mbcs', 'ignore')
        t.duration = meta["duration"]
        return self.clib.add_track_cpp(byref(t))

    def _get_meta(self, path):
        try:
            a = MP3(path, ID3=ID3)
            tags = a.tags or ID3()
            return {
                "path": path,
                "title": str(tags.get('TIT2', os.path.basename(path))),
                "artist": str(tags.get('TPE1', 'Unknown')),
                "album": str(tags.get('TALB', 'Unknown')),
                "genre": str(tags.get('TCON', 'Unknown')),
                "duration": a.info.length
            }
        except: return {"path": path, "title": os.path.basename(path), "artist": "Err", "album": "-", "genre": "-", "duration": 0}

    def get_tracks(self, sort_by="artist"):
        if not self.clib: return []
        order = "DESC" if sort_by == "rating" else "ASC"
        self.clib.prepare_query(sort_by.encode(), order.encode())
        res = []
        t = TrackData()
        while self.clib.fetch_next_track(byref(t)):
            res.append((t.id, t.path.decode('mbcs'), t.title.decode('mbcs'), t.artist.decode('mbcs'),
                        t.album.decode('mbcs'), t.genre.decode('mbcs'), t.duration, t.rating))
        return res

    def update_rating(self, path, avg, r):
        self.clib.update_rating_cpp(path.encode('mbcs'), c_double(avg), 
            r['melody'], r['rhythm'], r['vocals'], r['lyrics'], r['arrange'], r['has_vocals'], r['has_lyrics'])

    def get_artist_rating(self, artist):
        return round(self.clib.get_avg_rating_cpp(artist.encode('mbcs')), 2)

    def delete_track(self, path):
        self.clib.delete_track_cpp(path.encode('mbcs'))