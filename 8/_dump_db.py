from photo_organizer.database import get_connection, get_all_photos
conn = get_connection()
rows = get_all_photos(conn)
print(f"Total DB rows: {len(rows)}")
for r in sorted(rows, key=lambda r: r.get("filename", "")):
    print(f"  {r.get('filename','?'):20s} camera={r.get('camera_model',''):20s} cap={r.get('capture_time','')} title='{r.get('title','')}' notes='{r.get('notes','')}'")
conn.close()
