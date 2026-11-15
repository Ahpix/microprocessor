
from core.tamagotchi import Tamagotchi


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


def test_sleep():
    tama = Tamagotchi("Tama")
    tama.energy = 50

    result = tama.sleep()

    assert result is True
    assert tama.is_sleeping is True


def test_cannot_feed_while_sleeping():
    tama = Tamagotchi("Tama")
    tama.sleep()

    assert tama.feed() is False


def test_battle_profile():
    tama = Tamagotchi("Tama")

    profile = tama.get_battle_profile()

    assert profile["max_hp"] == 100
    assert profile["damage_multiplier"] == 1.1


if __name__ == "__main__":
    test_feed()
    test_play()
    test_sleep()
    test_cannot_feed_while_sleeping()
    test_battle_profile()

    print("모든 테스트 통과!")
