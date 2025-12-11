#include <iostream>
#include <windows.h> 
#include <string>
#include <vector>
#include <ctime>
#include <algorithm>
#include <stdio.h> 
#include "sqlite3.h"

#pragma comment(lib, "winmm.lib")
#define EXPORT __declspec(dllexport)

// ==========================================
// СТРУКТУРИ ДАНИХ (Data Structures)
// ==========================================
struct TrackData {
    int id;
    char path[256];
    char title[256];
    char artist[256];
    char album[256];
    char genre[100];
    double duration;
    double rating;
    int rate_melody; int rate_rhythm; int rate_vocals; 
    int rate_lyrics; int rate_arrange;
    int has_vocals; int has_lyrics;
};

struct GroupData {
    char name[256];      
    char secondary[256]; 
    int count;           
    char cover_path[256];
};

struct TopItemData {
    char name[256];
    char secondary[256];
    double rating;
    char cover_path[256];
    int type; // 0=Track, 1=Album, 2=Artist
};

// ==========================================
// 1. АБСТРАКЦІЯ (Аудіо Інтерфейс)
// ==========================================
class IAudioPlayer {
public:
    virtual void play(const char* path) = 0;
    virtual void pause() = 0;
    virtual bool isPlaying() = 0;
    virtual double getPosition() = 0;
    virtual void setPosition(const char* path, double seconds) = 0;
    virtual ~IAudioPlayer() {}
};

// ==========================================
// 2. РЕАЛІЗАЦІЯ (Windows MCI)
// ==========================================
class WindowsAudioPlayer : public IAudioPlayer {
public:
    void play(const char* path) override {
        // Закриваємо попередній файл перед відкриттям нового
        mciSendStringA("close mp3", NULL, 0, NULL);
        
        std::string cmd = "open \"" + std::string(path) + "\" type mpegvideo alias mp3";
        mciSendStringA(cmd.c_str(), NULL, 0, NULL);
        
        // ВАЖЛИВО: Задаємо формат часу в мілісекундах, щоб уникнути багів з позицією
        mciSendStringA("set mp3 time format milliseconds", NULL, 0, NULL);
        mciSendStringA("play mp3", NULL, 0, NULL);
    }

    void pause() override {
        static bool paused = false;
        if (paused) {
            mciSendStringA("resume mp3", NULL, 0, NULL);
            paused = false;
        } else {
            mciSendStringA("pause mp3", NULL, 0, NULL);
            paused = true;
        }
    }

    bool isPlaying() override {
        char buf[128];
        mciSendStringA("status mp3 mode", buf, 128, NULL);
        return (strcmp(buf, "playing") == 0);
    }

    double getPosition() override {
        char buf[128];
        // Гарантуємо формат перед зчитуванням
        mciSendStringA("set mp3 time format milliseconds", NULL, 0, NULL);
        mciSendStringA("status mp3 position", buf, 128, NULL);
        return atof(buf) / 1000.0; // Повертаємо секунди
    }

    void setPosition(const char* path, double seconds) override {
        // Гарантуємо формат часу
        mciSendStringA("set mp3 time format milliseconds", NULL, 0, NULL);
        
        char cmd[256];
        long ms = (long)(seconds * 1000);
        
        // Використовуємо SEEK, а потім PLAY - це найнадійніший метод
        sprintf(cmd, "seek mp3 to %ld", ms);
        mciSendStringA(cmd, NULL, 0, NULL);
        
        mciSendStringA("play mp3", NULL, 0, NULL);
    }
};

// ==========================================
// 3. ІНКАПСУЛЯЦІЯ (Менеджер бібліотеки)
// ==========================================
class LibraryManager {
private:
    sqlite3* db;
    sqlite3_stmt* cursor_stmt;
    sqlite3_stmt* group_stmt;
    sqlite3_stmt* top_stmt;
    
    bool is_shuffle;
    bool is_repeat;
    
    IAudioPlayer* player; // Поліморфний вказівник

public:
    LibraryManager() : db(nullptr), cursor_stmt(nullptr), group_stmt(nullptr), top_stmt(nullptr), is_shuffle(false), is_repeat(false) {
        player = new WindowsAudioPlayer();
        initDB();
    }

    ~LibraryManager() {
        if (db) sqlite3_close(db);
        delete player;
    }

    // --- Робота з Базою Даних ---
    void initDB() {
        if (sqlite3_open("music_library.db", &db)) return;
        
        const char* sql = 
            "CREATE TABLE IF NOT EXISTS tracks ("
            "id INTEGER PRIMARY KEY, path TEXT UNIQUE, title TEXT, artist TEXT, "
            "album TEXT, genre TEXT, duration REAL, rating REAL DEFAULT 0, "
            "rate_melody INTEGER DEFAULT 0, rate_rhythm INTEGER DEFAULT 0, "
            "rate_vocals INTEGER DEFAULT 0, rate_lyrics INTEGER DEFAULT 0, "
            "rate_arrange INTEGER DEFAULT 0, has_vocals INTEGER DEFAULT 1, has_lyrics INTEGER DEFAULT 1)";
        
        char* errMsg;
        sqlite3_exec(db, sql, 0, 0, &errMsg);
        srand(time(0));
    }

    void clearDatabase() {
        if (!db) return;
        char* errMsg;
        sqlite3_exec(db, "DELETE FROM tracks", 0, 0, &errMsg);
        sqlite3_exec(db, "VACUUM", 0, 0, &errMsg);
    }

    bool addTrack(TrackData* t) {
        if (!db) return false;
        const char* sql = "INSERT OR IGNORE INTO tracks (path, title, artist, album, genre, duration) VALUES (?, ?, ?, ?, ?, ?)";
        sqlite3_stmt* stmt;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) == SQLITE_OK) {
            sqlite3_bind_text(stmt, 1, t->path, -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 2, t->title, -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 3, t->artist, -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 4, t->album, -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 5, t->genre, -1, SQLITE_STATIC);
            sqlite3_bind_double(stmt, 6, t->duration);
            sqlite3_step(stmt);
            sqlite3_finalize(stmt);
            return true;
        }
        return false;
    }

    // --- Запити (Сортування, Фільтрація, Пошук) ---
    void prepareQuery(char* sort_col, char* order, char* filter_col, char* filter_val) {
        if (!db) return;
        if (cursor_stmt) sqlite3_finalize(cursor_stmt);
        
        std::string sql = "SELECT * FROM tracks";
        
        // Фільтрація (Artist/Album)
        if (filter_col != NULL && strlen(filter_col) > 0) {
            sql += " WHERE ";
            sql += filter_col;
            sql += " = ?";
        }
        
        sql += " ORDER BY ";
        sql += sort_col;
        sql += " ";
        sql += order;
        
        if (sqlite3_prepare_v2(db, sql.c_str(), -1, &cursor_stmt, 0) == SQLITE_OK) {
            if (filter_col != NULL && strlen(filter_col) > 0) {
                sqlite3_bind_text(cursor_stmt, 1, filter_val, -1, SQLITE_STATIC);
            }
        }
    }

    void prepareSearch(const char* query) {
        if (!db) return;
        if (cursor_stmt) sqlite3_finalize(cursor_stmt);
        
        std::string sql = "SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ?";
        
        if (sqlite3_prepare_v2(db, sql.c_str(), -1, &cursor_stmt, 0) == SQLITE_OK) {
            std::string q_str = "%" + std::string(query) + "%";
            sqlite3_bind_text(cursor_stmt, 1, q_str.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(cursor_stmt, 2, q_str.c_str(), -1, SQLITE_TRANSIENT);
        }
    }

    bool fetchNextTrack(TrackData* t) {
        if (!cursor_stmt) return false;
        if (sqlite3_step(cursor_stmt) == SQLITE_ROW) {
            t->id = sqlite3_column_int(cursor_stmt, 0);
            strcpy(t->path, (const char*)sqlite3_column_text(cursor_stmt, 1));
            strcpy(t->title, (const char*)sqlite3_column_text(cursor_stmt, 2));
            strcpy(t->artist, (const char*)sqlite3_column_text(cursor_stmt, 3));
            strcpy(t->album, (const char*)sqlite3_column_text(cursor_stmt, 4));
            strcpy(t->genre, (const char*)sqlite3_column_text(cursor_stmt, 5));
            t->duration = sqlite3_column_double(cursor_stmt, 6);
            t->rating = sqlite3_column_double(cursor_stmt, 7);
            
            t->rate_melody = sqlite3_column_int(cursor_stmt, 8);
            t->rate_rhythm = sqlite3_column_int(cursor_stmt, 9);
            t->rate_vocals = sqlite3_column_int(cursor_stmt, 10);
            t->rate_lyrics = sqlite3_column_int(cursor_stmt, 11);
            t->rate_arrange = sqlite3_column_int(cursor_stmt, 12);
            t->has_vocals = sqlite3_column_int(cursor_stmt, 13);
            t->has_lyrics = sqlite3_column_int(cursor_stmt, 14);
            return true;
        }
        return false;
    }

    // --- Advanced Tops (Треки, Альбоми, Артисти) ---
    void prepareAdvancedTop(int entity_type, int order_mode) {
        if (!db) return;
        if (top_stmt) sqlite3_finalize(top_stmt);
        
        std::string sql;
        std::string order = (order_mode == 1) ? "DESC" : "ASC"; // 1=Best
        
        if (entity_type == 0) { // TRACKS
            sql = "SELECT title, artist, rating, path, 0 FROM tracks WHERE rating > 0 ORDER BY rating " + order + " LIMIT 10";
        } else if (entity_type == 1) { // ALBUMS
            sql = "SELECT album, artist, AVG(rating), MIN(path), 1 FROM tracks WHERE rating > 0 GROUP BY album ORDER BY AVG(rating) " + order + " LIMIT 10";
        } else if (entity_type == 2) { // ARTISTS
            sql = "SELECT artist, '', AVG(rating), MIN(path), 2 FROM tracks WHERE rating > 0 GROUP BY artist ORDER BY AVG(rating) " + order + " LIMIT 10";
        }
        sqlite3_prepare_v2(db, sql.c_str(), -1, &top_stmt, 0);
    }

    bool fetchTopItem(TopItemData* item) {
        if (!top_stmt) return false;
        if (sqlite3_step(top_stmt) == SQLITE_ROW) {
            strcpy(item->name, (const char*)sqlite3_column_text(top_stmt, 0));
            strcpy(item->secondary, (const char*)sqlite3_column_text(top_stmt, 1));
            item->rating = sqlite3_column_double(top_stmt, 2);
            strcpy(item->cover_path, (const char*)sqlite3_column_text(top_stmt, 3));
            item->type = sqlite3_column_int(top_stmt, 4);
            return true;
        }
        return false;
    }

    // --- Групування (Browser) ---
    void prepareGroupQuery(int mode) {
        if (!db) return;
        if (group_stmt) sqlite3_finalize(group_stmt);
        
        std::string sql;
        if (mode == 1) sql = "SELECT artist, '', COUNT(*), MIN(path) FROM tracks GROUP BY artist ORDER BY artist";
        else sql = "SELECT album, artist, COUNT(*), MIN(path) FROM tracks GROUP BY album ORDER BY album";
        
        sqlite3_prepare_v2(db, sql.c_str(), -1, &group_stmt, 0);
    }

    // Заміни стару функцію fetchGroupItem на цю:
    bool fetchGroupItem(GroupData* g) {
        if (!group_stmt) return false;
        if (sqlite3_step(group_stmt) == SQLITE_ROW) {
            // Безпечне зчитування (перевірка на NULL)
            const char* val_name = (const char*)sqlite3_column_text(group_stmt, 0);
            const char* val_sec = (const char*)sqlite3_column_text(group_stmt, 1);
            const char* val_path = (const char*)sqlite3_column_text(group_stmt, 3);

            // Якщо поле пусте, записуємо "Unknown" або пустий рядок
            strcpy(g->name, val_name ? val_name : "Unknown");
            strcpy(g->secondary, val_sec ? val_sec : "");
            g->count = sqlite3_column_int(group_stmt, 2);
            strcpy(g->cover_path, val_path ? val_path : "");
            
            return true;
        }
        return false;
    }

    // --- Рейтинг ---
    bool updateRating(char* path, double avg, int mel, int rhy, int voc, int lyr, int arr, int h_voc, int h_lyr) {
        if (!db) return false;
        sqlite3_stmt* st;
        if (sqlite3_prepare_v2(db, "UPDATE tracks SET rating=?, rate_melody=?, rate_rhythm=?, rate_vocals=?, rate_lyrics=?, rate_arrange=?, has_vocals=?, has_lyrics=? WHERE path=?", -1, &st, 0) == SQLITE_OK) {
            sqlite3_bind_double(st, 1, avg);
            sqlite3_bind_int(st, 2, mel); sqlite3_bind_int(st, 3, rhy);
            sqlite3_bind_int(st, 4, voc); sqlite3_bind_int(st, 5, lyr);
            sqlite3_bind_int(st, 6, arr); sqlite3_bind_int(st, 7, h_voc);
            sqlite3_bind_int(st, 8, h_lyr);
            sqlite3_bind_text(st, 9, path, -1, SQLITE_STATIC);
            sqlite3_step(st);
            sqlite3_finalize(st);
            return true;
        }
        return false;
    }

    // --- Управління плеєром ---
    void audioPlay(const char* path) { player->play(path); }
    void audioPause() { player->pause(); }
    bool audioIsPlaying() { return player->isPlaying(); }
    double audioGetPos() { return player->getPosition(); }
    void audioSetPos(const char* path, double s) { player->setPosition(path, s); }

    // --- Логіка відтворення ---
    void toggleShuffle() { is_shuffle = !is_shuffle; if(is_shuffle) srand(time(0)); }
    void toggleRepeat() { is_repeat = !is_repeat; }
    bool getShuffle() { return is_shuffle; }
    bool getRepeat() { return is_repeat; }
    
    int getNextIndex(int current, int total) {
        if (total <= 0) return -1;
        if (is_shuffle) return rand() % total;
        if (current + 1 >= total) return is_repeat ? 0 : -1;
        return current + 1;
    }
    
    int getPrevIndex(int current, int total) {
        if (total <= 0) return -1;
        if (current - 1 < 0) return is_repeat ? total - 1 : 0;
        return current - 1;
    }
};

// Глобальний менеджер (Singleton в контексті DLL)
LibraryManager* manager = nullptr;

// ==========================================
// C-INTERFACE (BRIDGE TO PYTHON)
// ==========================================
extern "C" {
    EXPORT void init_system() { if (!manager) manager = new LibraryManager(); }
    EXPORT void logic_clear_database() { if (manager) manager->clearDatabase(); }
    EXPORT bool logic_add_track(TrackData* t) { return manager ? manager->addTrack(t) : false; }
    
    EXPORT void logic_prepare_query(char* s, char* o, char* fc, char* fv) { if (manager) manager->prepareQuery(s, o, fc, fv); }
    EXPORT void logic_search_tracks(char* q) { if (manager) manager->prepareSearch(q); } // Пошук
    EXPORT bool logic_fetch_next(TrackData* t) { return manager ? manager->fetchNextTrack(t) : false; }
    
    EXPORT void logic_prepare_advanced_top(int e, int m) { if (manager) manager->prepareAdvancedTop(e, m); }
    EXPORT bool logic_fetch_top_item(TopItemData* i) { return manager ? manager->fetchTopItem(i) : false; }
    
    EXPORT void logic_prepare_group_query(int m) { if (manager) manager->prepareGroupQuery(m); }
    EXPORT bool logic_fetch_next_group(GroupData* g) { return manager ? manager->fetchGroupItem(g) : false; }
    
    EXPORT bool logic_update_rating(char* p, double a, int m, int r, int v, int l, int ar, int hv, int hl) { return manager ? manager->updateRating(p, a, m, r, v, l, ar, hv, hl) : false; }
    
    EXPORT void audio_play(char* path) { if(manager) manager->audioPlay(path); }
    EXPORT void audio_pause() { if(manager) manager->audioPause(); }
    EXPORT bool audio_is_playing() { return manager ? manager->audioIsPlaying() : false; }
    EXPORT double audio_get_pos() { return manager ? manager->audioGetPos() : 0.0; }
    EXPORT void audio_set_pos(char* path, double s) { if(manager) manager->audioSetPos(path, s); }
    
    // Повертають bool для правильної зміни кольору кнопок
    EXPORT bool logic_toggle_shuffle() { if(manager) { manager->toggleShuffle(); return manager->getShuffle(); } return false; }
    EXPORT bool logic_toggle_repeat() { if(manager) { manager->toggleRepeat(); return manager->getRepeat(); } return false; }
    
    EXPORT bool logic_get_shuffle_state() { return manager ? manager->getShuffle() : false; }
    EXPORT bool logic_get_repeat_state() { return manager ? manager->getRepeat() : false; }
    EXPORT int logic_get_next_index(int c, int t) { return manager ? manager->getNextIndex(c, t) : -1; }
    EXPORT int logic_get_prev_index(int c, int t) { return manager ? manager->getPrevIndex(c, t) : -1; }
}