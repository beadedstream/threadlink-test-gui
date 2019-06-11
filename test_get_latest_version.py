from avr import FlashThreadlink


def test_version():
    filenames = ["main-app 1.1a",
                 "main-app 1.1b",
                 "main-app 1.1c",
                 "main-app 1.1v"
                 ]

    assert FlashThreadlink.get_latest_version(filenames) == "main-app 1.1v"

    filenames = ["main-app 1.2a",
                 "main-app 1.3a",
                 "main-app 1.2j",
                 "main-app 1.1z"
                 ]

    assert FlashThreadlink.get_latest_version(filenames) == "main-app 1.3a"

    filenames = ["main-app 1.1a",
                 "main-app 2.1z",
                 "main-app 3.1a",
                 "main-app 3.0z",
                 "main-app 2.7z"
                 ]

    assert FlashThreadlink.get_latest_version(filenames) == "main-app 3.1a"