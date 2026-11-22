import time
import pytest
from game_engine.core.tamagotchi import Tamagotchi


def test_feed():
    tama = Tamagotchi("Tama")
    tama.satiety = 50

    result = tama.feed()

    assert result is True
    assert tama.satiety == 80


def test_play():
    tama = Tamagotchi("Tama")

    tama.play()

    assert tama.happiness == 70
    assert tama.satiety == 85
    assert tama.energy == 85


def test_sleep_and_wake():
    tama = Tamagotchi("Tama")
    tama.energy = 50

    result = tama.sleep()

    assert result is True
    assert tama.is_sleeping is True
    assert tama.sleep_end_time is not None

    # 깨우기
    wake_result = tama.wake()
    assert wake_result is True
    assert tama.is_sleeping is False
    assert tama.sleep_end_time is None


def test_cannot_feed_while_sleeping():
    tama = Tamagotchi("Tama")
    tama.sleep()

    assert tama.feed() is False


def test_dead_pet_behavior():
    tama = Tamagotchi("Tama")
    tama.satiety = 0
    tama._check_alive()

    assert tama.is_alive is False
    assert tama.feed() is False
    assert tama.play() is False
    assert tama.sleep() is False


def test_battle_profile():
    tama = Tamagotchi("Tama")

    profile = tama.get_battle_profile()

    assert profile["max_hp"] == 100
    assert profile["damage_multiplier"] == 1.1


def test_to_pet_dict_protocol_compliance():
    tama = Tamagotchi("Tama", pet_id="pet01")
    pet_data = tama.to_pet_dict()

    assert pet_data["pet_id"] == "pet01"
    assert pet_data["name"] == "Tama"
    assert isinstance(pet_data["satiety"], int)
    assert isinstance(pet_data["happiness"], int)
    assert isinstance(pet_data["energy"], int)
    assert pet_data["is_alive"] is True
    assert pet_data["is_sleeping"] is False
    assert pet_data["sleep_end_time"] is None
    assert isinstance(pet_data["last_update"], (int, float))
