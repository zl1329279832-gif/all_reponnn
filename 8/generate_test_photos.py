import os
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta
import random

OUT_DIR = r"c:\Users\13292\Desktop\solocode\all_reponnn\8\test_photos"
for p in os.listdir(OUT_DIR) if os.path.exists(OUT_DIR) else []:
    os.remove(os.path.join(OUT_DIR, p))
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = [
    (255, 70, 70), (70, 70, 255), (70, 200, 70),
    (255, 210, 50), (170, 70, 200), (255, 140, 60),
    (60, 170, 255), (255, 140, 140), (180, 180, 40),
    (40, 40, 40),
]

MODELS = ["Canon EOS R5", "Sony ILCE-7M4", "Nikon Z 7II", "iPhone 15 Pro"]

tag_map = {v: k for k, v in TAGS.items()}


def make_image(path, color, date_dt, model):
    img = Image.new("RGB", (800, 600), color)
    try:
        exif = img.getexif()
        date_str = date_dt.strftime("%Y:%m:%d %H:%M:%S")
        exif[tag_map["Model"]] = model
        exif[tag_map["Make"]] = model.split()[0]
        exif[tag_map["DateTimeOriginal"]] = date_str
        exif[tag_map["DateTime"]] = date_str
        img.save(path, "JPEG", exif=exif, quality=85)
    except Exception:
        img.save(path, "JPEG", quality=85)
    print(f"created {os.path.basename(path)} ({model}, {date_dt.date()})")


now = datetime(2025, 5, 1, 10, 0)
for i in range(8):
    dt = now + timedelta(days=i * 7, hours=random.randint(0, 12), minutes=random.randint(0, 59))
    path = os.path.join(OUT_DIR, f"photo_{i+1:03d}.jpg")
    model = MODELS[i % len(MODELS)]
    make_image(path, COLORS[i], dt, model)

for i in range(2):
    dt = datetime(2025, 6, i + 10, 15, 0)
    path = os.path.join(OUT_DIR, f"vacation_{i+1:02d}.jpg")
    make_image(path, COLORS[i + 8], dt, "GoPro HERO12")

png_img = Image.new("RGB", (640, 480), (50, 50, 50))
png_path = os.path.join(OUT_DIR, "screenshot.png")
png_img.save(png_path, "PNG")
print(f"created screenshot.png (no EXIF)")

corrupt_path = os.path.join(OUT_DIR, "corrupt.jpg")
with open(corrupt_path, "wb") as f:
    f.write(b"this is not a real jpeg file \x00\x01\x02 garbage data")
print(f"created corrupt.jpg (坏图)")

print(f"\n=== total: {len(os.listdir(OUT_DIR))} files in {OUT_DIR}")
