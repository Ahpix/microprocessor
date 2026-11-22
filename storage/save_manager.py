import json
import os
from typing import Optional

from game_engine.core.tamagotchi import Tamagotchi


SAVE_PATH = "data/save.json"


def has_save() -> bool:
    """저장 파일 존재 여부 확인"""
    return os.path.exists(SAVE_PATH)


def save_game(tamagotchi: Tamagotchi) -> None:
    """다마고치 상태를 JSON 파일로 저장"""
    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)

    data = tamagotchi.to_dict()

    with open(SAVE_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_game() -> Optional[Tamagotchi]:
    """JSON 파일에서 다마고치 상태 불러오기"""
    if not has_save():
        return None

    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return Tamagotchi.from_dict(data)
    except Exception:
        return None
