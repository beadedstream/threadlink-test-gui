import re


class InvalidLimit(Exception):
    pass


class ValueNotSet(Exception):
    pass


class Model:
    """The model class for storing test limits and other relevant data and 
    checking recorded values against the limits.

    Instance variables:
    limits        --  Test variable ranges and limits.
    tac           --  Tac Ids, lead length and other values.
    internal_5v   --  Internally measured 5 V supply voltage.
    input_v       --  Externally measured supply voltage.

    Instance methods:
    compare_to_limit   --  Compare value against limits and return result.
    """

    def __init__(self):
        self.limits = {
            "i_input_min": 1.0,
            "i_input_max": 10.0,
            "5v_min": 0.833,
            "5v_max": 0.921,
            "2p5v_min": 2.38,
            "2p5v_max": 2.62,
            "1p8v_min": 1.73,
            "1p8v_max": 1.87
        }
        self.tac = {
            "tac1": None,
            "tac2": None,
            "tac3": None,
            "tac4": None,
            "lead": 80,
            "1": 0.000,
            "2": 0.250,
            "3": 0.500
        }

    def compare_to_limit(self, limit: str, value: float):
        """Compare input value against limit and return the result as a bool."""

        if limit == "input_i":
            return (value >= self.limits["i_input_min"] and
                    value <= self.limits["i_input_max"])

        elif limit == "5v_supply":
            return (value >= self.limits["5v_min"] and
                    value <= self.limits["5v_max"])

        elif limit == "2p5v":
            return (value >= self.limits["2p5v_min"] and
                    value <= self.limits["2p5v_max"])

        elif limit == "1p8v":
            return (value >= self.limits["1p8v_min"] and
                    value <= self.limits["1p8v_max"])

        else:
            raise InvalidLimit
