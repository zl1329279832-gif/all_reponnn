"""
测试数据生成脚本 - 用于验收存档管理器
运行后会在 test_data/ 目录下创建 60 条测试存档
"""

import os
import json
import random
import shutil
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_ROOT = os.path.join(BASE_DIR, "test_data")

GAME_NAMES = [
    "Elden Ring", "Baldurs Gate 3", "The Witcher 3", "Cyberpunk 2077",
    "Skyrim", "Fallout 4", "Dark Souls 3", "Sekiro", "Hollow Knight",
    "Stardew Valley", "Persona 5", "Final Fantasy 16", "Chrono Trigger",
    "Dragon Age Inquisition", "Mass Effect 2", "Divinity Original Sin 2",
]


def generate_json_save(game_dir: str, slot_num: int, char_name: str, level: int, chapter: str, playtime: str) -> str:
    saves_dir = os.path.join(game_dir, "saves")
    os.makedirs(saves_dir, exist_ok=True)
    data = {
        "player_name": char_name,
        "character_level": level,
        "current_chapter": chapter,
        "playtime_hours": playtime,
        "inventory": {"gold": random.randint(100, 10000), "items": ["sword", "shield", "potion"]},
        "stats": {"hp": random.randint(100, 500), "mp": random.randint(50, 300)},
        "last_save_time": time.time(),
    }
    path = os.path.join(saves_dir, f"slot{slot_num}.save.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def generate_ini_save(game_dir: str, slot_num: int, char_name: str, level: int, chapter: str, playtime: str) -> str:
    saves_dir = os.path.join(game_dir, "SaveGames")
    os.makedirs(saves_dir, exist_ok=True)
    content = f"""[General]
SaveVersion=1.0
CharacterName={char_name}
Level={level}
Chapter={chapter}
PlayTime={playtime}

[PlayerStats]
Health={random.randint(100, 500)}
Mana={random.randint(50, 300)}
Strength={random.randint(10, 50)}
Intelligence={random.randint(10, 50)}

[Progress]
QuestsCompleted={random.randint(5, 50)}
LocationsDiscovered={random.randint(10, 100)}
"""
    path = os.path.join(saves_dir, f"save{slot_num}.ini")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def generate_bin_save(game_dir: str, slot_num: int) -> str:
    saves_dir = os.path.join(game_dir, "save")
    os.makedirs(saves_dir, exist_ok=True)
    path = os.path.join(saves_dir, f"game_save_{slot_num}.dat")
    with open(path, "wb") as f:
        f.write(os.urandom(256))
        f.write(b"SAVE_HEADER_v1.0")
        f.write(os.urandom(512))
    return path


def generate_note_save(game_dir: str, slot_num: int, char_name: str, level: int) -> str:
    saves_dir = os.path.join(game_dir, "存档")
    os.makedirs(saves_dir, exist_ok=True)
    data = {
        "name": char_name,
        "lv": level,
        "game_time": f"{random.randint(1, 100)}小时",
        "position": "新手村",
        "存档时间": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = os.path.join(saves_dir, f"存档_{slot_num}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def generate_cache_junk(game_dir: str) -> None:
    cache_dir = os.path.join(game_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    for i in range(20):
        with open(os.path.join(cache_dir, f"cache_{i}.tmp"), "w") as f:
            f.write("this is cache, should NOT be scanned")
    logs_dir = os.path.join(game_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    for i in range(10):
        with open(os.path.join(logs_dir, f"log_{i}.log"), "w") as f:
            f.write("this is log, should NOT be scanned")
    bin_dir = os.path.join(game_dir, "Binaries")
    os.makedirs(bin_dir, exist_ok=True)
    for i in range(30):
        with open(os.path.join(bin_dir, f"asset_{i}.pak"), "wb") as f:
            f.write(os.urandom(1024))


def main():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)
    os.makedirs(TEST_ROOT, exist_ok=True)

    char_names = ["勇者阿瑞斯", "魔法师梅林", "刺客伊芙琳", "骑士兰斯洛特", "弓手艾琳娜", "牧师塞拉斯"]
    chapters = ["第一章: 启程", "第二章: 迷雾森林", "第三章: 王城危机", "第四章: 暗黑地下城", "第五章: 最终决战"]

    total = 0

    for i in range(20):
        game_name = GAME_NAMES[i % len(GAME_NAMES)]
        game_dir = os.path.join(TEST_ROOT, f"Game_{i:03d}_{game_name.replace(' ', '_')}")
        char = char_names[i % len(char_names)]
        lvl = random.randint(1, 99)
        chap = chapters[i % len(chapters)]
        playtime = f"{random.randint(5, 200)}小时{random.randint(0, 59)}分"
        generate_json_save(game_dir, i + 1, char, lvl, chap, playtime)
        generate_cache_junk(game_dir)
        total += 1

    for i in range(20):
        game_name = GAME_NAMES[(i + 20) % len(GAME_NAMES)]
        game_dir = os.path.join(TEST_ROOT, f"Game_{i + 20:03d}_{game_name.replace(' ', '_')}")
        char = char_names[(i + 2) % len(char_names)]
        lvl = random.randint(1, 99)
        chap = chapters[(i + 2) % len(chapters)]
        playtime = f"{random.randint(5, 200)}小时{random.randint(0, 59)}分"
        generate_ini_save(game_dir, i + 1, char, lvl, chap, playtime)
        generate_cache_junk(game_dir)
        total += 1

    for i in range(10):
        game_name = GAME_NAMES[(i + 40) % len(GAME_NAMES)]
        game_dir = os.path.join(TEST_ROOT, f"Game_{i + 40:03d}_{game_name.replace(' ', '_')}")
        generate_bin_save(game_dir, i + 1)
        generate_cache_junk(game_dir)
        total += 1

    for i in range(10):
        game_name = GAME_NAMES[(i + 50) % len(GAME_NAMES)]
        game_dir = os.path.join(TEST_ROOT, f"Game_{i + 50:03d}_{game_name.replace(' ', '_')}")
        char = char_names[(i + 4) % len(char_names)]
        lvl = random.randint(1, 99)
        generate_note_save(game_dir, i + 1, char, lvl)
        generate_cache_junk(game_dir)
        total += 1

    print(f"测试数据生成完成！共 {total} 条存档")
    print(f"测试根目录: {TEST_ROOT}")
    print("\n目录结构示意:")
    print("test_data/")
    print("  ├── Game_000_Elden_Ring/")
    print("  │   ├── saves/           <- 会被扫描到")
    print("  │   │   └── slot1.save.json")
    print("  │   ├── cache/           <- 会被正确忽略")
    print("  │   ├── logs/            <- 会被正确忽略")
    print("  │   └── Binaries/        <- 会被正确忽略")
    print("  ├── Game_020_Baldurs_Gate_3/")
    print("  │   └── SaveGames/       <- 会被扫描到")
    print("  ├── ...")
    print("\n验收步骤:")
    print("1. 运行 python main.py")
    print("2. 点击「添加扫描路径」，选择 test_data/ 目录")
    print("3. 点击「重新扫描」，应该只扫描到 60 条存档（不会扫到 cache/logs/Binaries）")
    print("4. 测试搜索、排序、滚动")
    print("5. 分别点选 JSON、INI、二进制、中文目录的存档验证预览")
    print("6. 测试备份和还原流程")


if __name__ == "__main__":
    main()
