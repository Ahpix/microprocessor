import pytest

import storage.save_manager as save_manager
from game_engine.core.tamagotchi import Tamagotchi


def test_save_and_load(tmp_path, monkeypatch):
    # 테스트 전용 임시 저장 경로
    save_path = tmp_path / "save.json"

    monkeypatch.setattr(
        save_manager, "SAVE_PATH", str(save_path)
    )

    tama = Tamagotchi("Tama")

    tama.satiety = 70
    tama.happiness = 80
    tama.energy = 60

    # 저장
    save_manager.save_game(tama)

    assert save_manager.has_save() is True

    # 불러오기
    loaded = save_manager.load_game()

    assert loaded.name == "Tama"
    assert loaded.satiety == pytest.approx(70, abs=0.01)
    assert loaded.happiness == pytest.approx(80, abs=0.01)
    assert loaded.energy == pytest.approx(60, abs=0.01)


def test_load_without_save(tmp_path, monkeypatch):
    # 존재하지 않는 임시 경로 사용
    save_path = tmp_path / "empty.json"

    monkeypatch.setattr(
        save_manager, "SAVE_PATH", str(save_path)
    )

    assert save_manager.has_save() is False
    assert save_manager.load_game() is None
