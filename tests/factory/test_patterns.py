from pyKomorebi.factory import api_factory


def test_option_pattern_long_and_short():
    matched = api_factory.OPTION_PATTERN.match("  -h, --help")
    assert matched is not None
    short_option = matched.group("short")
    assert short_option == "-h"
    long_option = matched.group("name")
    assert long_option == "--help"


def test_option_pattern_long():
    matched = api_factory.OPTION_PATTERN.match("  --help")
    assert matched is not None
    short_option = matched.group("short")
    assert short_option is None
    long_option = matched.group("name")
    assert long_option == "--help"


def test_option_pattern_short():
    matched = api_factory.OPTION_PATTERN.match("  -h")
    assert matched is not None
    short_option = matched.group("short")
    assert short_option == "-h"
    long_option = matched.group("name")
    assert long_option is None


OPTION_ARG_VALUE = """ -c, --config <CONFIG>
          Path to a static configuration JSON file"""


def test_options_with_argument():
    matched = api_factory.OPTION_PATTERN.match(OPTION_ARG_VALUE)
    assert matched is not None
    assert matched.group("short") == "-c"
    assert matched.group("name") == "--config"
    assert matched.group("arg") == "<CONFIG>"


def test_default_value():
    matched = api_factory.DEFAULT_PATTERN.match("          [default: single]")
    assert matched is not None
    value = matched.group("default")
    assert value == "single"


def test_constants():
    matched = api_factory.CONSTANTS_PATTERN.match(
        "   [possible values: single, stack, monocle, unfocused, floating]"
    )
    assert matched is not None
    constants = matched.group("values")
    assert constants == "single, stack, monocle, unfocused, floating"


MULTILINE_DOCSTRING = """          Desired ease function for animation

          [default: linear]
          [possible values: linear, ease-in-sine, ease-out-sine, ease-in-out-sine, ease-in-quad, ease-out-quad, ease-in-out-quad, ease-in-cubic, ease-in-out-cubic, ease-in-quart, ease-out-quart, ease-in-out-quart, ease-in-quint, ease-out-quint, ease-in-out-quint, ease-in-expo, ease-out-expo,
          ease-in-out-expo, ease-in-circ, ease-out-circ, ease-in-out-circ, ease-in-back, ease-out-back, ease-in-out-back, ease-in-elastic, ease-out-elastic, ease-in-out-elastic, ease-in-bounce, ease-out-bounce, ease-in-out-bounce]"""


def test_multiline_default_value():
    matched = api_factory.DEFAULT_PATTERN.match(MULTILINE_DOCSTRING)
    assert matched is not None
    value = matched.group("default")
    assert value == "linear"


def test_multiline_constants():
    matched = api_factory.CONSTANTS_PATTERN.match(MULTILINE_DOCSTRING)
    assert matched is not None
    constants = matched.group("values")
    assert (
        constants
        == """linear, ease-in-sine, ease-out-sine, ease-in-out-sine, ease-in-quad, ease-out-quad, ease-in-out-quad, ease-in-cubic, ease-in-out-cubic, ease-in-quart, ease-out-quart, ease-in-out-quart, ease-in-quint, ease-out-quint, ease-in-out-quint, ease-in-expo, ease-out-expo,
 ease-in-out-expo, ease-in-circ, ease-out-circ, ease-in-out-circ, ease-in-back, ease-out-back, ease-in-out-back, ease-in-elastic, ease-out-elastic, ease-in-out-elastic, ease-in-bounce, ease-out-bounce, ease-in-out-bounce"""
    )
