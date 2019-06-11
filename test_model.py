import model

m = model.Model()

tac_ids = {
    "tac1": "aaa1 1234 bbbb 5c6d 7e8f",
    "tac2": "aaa2 1234 bbbb 5c6d 7e8f",
    "tac3": "aaa3 1234 bbbb 5c6d 7e8f",
    "tac4": "aaa4 1234 bbbb 5c6d 7e8f",
}

good_vi_values = {
    "input_i": 4.0,
    "5v_supply": 0.9,
    "2p5v": 2.5,
    "1p8v": 1.8
}

bad_vi_values = {
    "input_i": 10.7,
    "5v_supply": 0.8,
    "2p5v": 2.7,
    "1p8v": 1.71
}


def test_limits():
    for key, value in good_vi_values.items():
        assert m.compare_to_limit(key, value)

    for key, value in bad_vi_values.items():
        assert not m.compare_to_limit(key, value)
