from math_tools import calculate

def test_calculate_basic():
    assert calculate("1+2*3") == "7"

def test_calculate_parentheses():
    assert calculate("(1+2)*3") == "9"

def test_calculate_div_zero():
    assert calculate("1/0").startswith("ERROR:")

def test_calculate_power_limit():
    assert calculate("2**100").startswith("ERROR:")

def test_calculate_invalid():
    assert calculate("__import__('os').system('dir')").startswith("ERROR:")