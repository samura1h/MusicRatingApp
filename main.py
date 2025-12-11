import customtkinter as ctk
from Backend.main_controller import MainController
from Frontend.main_window import MusicAppUI

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = MusicAppUI(MainController())
    app.mainloop()