import customtkinter as ctk

class RatingWindow(ctk.CTkToplevel):
    def __init__(self, master, logic_controller, track_path, current_data=None, on_close_callback=None):
        super().__init__(master)
        self.logic = logic_controller
        self.track_path = track_path
        self.on_close_callback = on_close_callback
        
        self.title("Rate Track")
        self.geometry("450x650") 
        self.attributes("-topmost", True)
        
        if not current_data:
            current_data = { 'melody': 5, 'rhythm': 5, 'arrange': 5, 'vocals': 5, 'lyrics': 5, 'has_vocals': 1, 'has_lyrics': 1 }

        self.sliders = {}
        self.checks = {}
        self.check_vars = {}
        self.value_labels = {} 

        ctk.CTkLabel(self, text="Rate this Track", font=("Arial", 22, "bold")).pack(pady=20)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=5)

        # === MUSIC COMPOSITION ===
        ctk.CTkLabel(self.scroll, text="Music Composition", font=("Arial", 16, "bold"), text_color="#1f538d").pack(pady=(10, 15), anchor="w")
        
        self.add_slider('melody', "Melody", current_data['melody'])
        self.add_slider('rhythm', "Rhythm", current_data['rhythm'])
        self.add_slider('arrange', "Arrangement", current_data['arrange'])
        
        # === VOCALS & LYRICS ===
        ctk.CTkLabel(self.scroll, text="Vocals & Lyrics", font=("Arial", 16, "bold"), text_color="#1f538d").pack(pady=(25, 15), anchor="w")
        
        self.add_check_slider('vocals', "Vocals", current_data['has_vocals'], current_data['vocals'])
        self.add_check_slider('lyrics', "Lyrics", current_data['has_lyrics'], current_data['lyrics'])
        
        # === SAVE BUTTON ===
        ctk.CTkButton(self, text="SAVE RATING", height=45, font=("Arial", 15, "bold"), 
                      fg_color="#daa520", hover_color="#b8860b", text_color="black", 
                      command=self.save).pack(pady=20, padx=30, fill="x")

    def add_slider(self, key, title, val):
        # Рядок-контейнер
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=8)

        # Назва (зліва)
        ctk.CTkLabel(row, text=title, width=100, anchor="w", font=("Arial", 14)).pack(side="left")

        # Цифра (справа) - створюємо її ДО слайдера, щоб передати посилання
        val_lbl = ctk.CTkLabel(row, text=str(val), width=30, font=("Arial", 16, "bold"), text_color="#daa520")
        val_lbl.pack(side="right", padx=10)
        self.value_labels[key] = val_lbl

        # Слайдер (по центру)
        # command=... оновлює лейбл при кожному русі
        sl = ctk.CTkSlider(row, from_=0, to=10, number_of_steps=10, 
                           command=lambda v, k=key: self.update_label(k, v))
        sl.set(val)
        sl.pack(side="right", fill="x", expand=True, padx=10)
        self.sliders[key] = sl

    def add_check_slider(self, key, title, is_active, val):
        # Рядок 1: Чекбокс
        row_check = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row_check.pack(fill="x", pady=(10, 0))
        
        var = ctk.IntVar(value=is_active)
        cb = ctk.CTkCheckBox(row_check, text=f"Has {title}?", variable=var, font=("Arial", 13, "bold"), 
                             command=lambda k=key: self.toggle_slider(k))
        cb.pack(side="left")
        self.check_vars[key] = var

        # Рядок 2: Слайдер (з відступом)
        row_slider = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row_slider.pack(fill="x", pady=(5, 10))
        
        # Пустий лейбл для відступу зліва
        ctk.CTkLabel(row_slider, text="", width=30).pack(side="left")

        # Цифра
        val_lbl = ctk.CTkLabel(row_slider, text=str(val), width=30, font=("Arial", 16, "bold"), text_color="#daa520")
        val_lbl.pack(side="right", padx=10)
        self.value_labels[key] = val_lbl

        # Слайдер
        sl = ctk.CTkSlider(row_slider, from_=0, to=10, number_of_steps=10,
                           command=lambda v, k=key: self.update_label(k, v))
        sl.set(val)
        
        if not is_active:
            sl.configure(state="disabled")
            val_lbl.configure(text_color="gray")
            
        sl.pack(side="right", fill="x", expand=True, padx=10)
        self.sliders[key] = sl

    def update_label(self, key, value):
        int_val = int(value)
        self.value_labels[key].configure(text=str(int_val))

    def toggle_slider(self, key):
        is_on = self.check_vars[key].get() == 1
        state = "normal" if is_on else "disabled"
        color = "#daa520" if is_on else "gray"
        
        self.sliders[key].configure(state=state)
        self.value_labels[key].configure(text_color=color)

    def save(self):
        data = {
            "melody": int(self.sliders['melody'].get()),
            "rhythm": int(self.sliders['rhythm'].get()),
            "arrange": int(self.sliders['arrange'].get()),
            "vocals": int(self.sliders['vocals'].get()),
            "lyrics": int(self.sliders['lyrics'].get()),
            "has_vocals": self.check_vars['vocals'].get(),
            "has_lyrics": self.check_vars['lyrics'].get()
        }
        self.logic.calculate_save_rating(self.track_path, data)
        if self.on_close_callback: self.on_close_callback()
        self.destroy()