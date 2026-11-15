import json
import os

from core.tamagotchi import Tamagotchi


SAVE_PATH = "data/save.json"


def has_save():
    """저장 파일 존재 여부 확인"""
    return os.path.exists(SAVE_PATH)


def save_game(tamagotchi):
    """다마고치 상태를 JSON 파일로 저장"""

    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)

    data = tamagotchi.to_dict()

    with open(SAVE_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_game():
    """JSON 파일에서 다마고치 상태 불러오기"""

    if not has_save():
        return None

    with open(SAVE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return Tamagotchi.from_dict(data)
