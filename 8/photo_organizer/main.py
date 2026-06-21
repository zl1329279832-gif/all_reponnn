import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photo_organizer.ui.app import PhotoOrganizerApp


def main():
    app = PhotoOrganizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
