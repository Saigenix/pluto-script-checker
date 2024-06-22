import os


_full_path = os.path.dirname(os.path.abspath(__file__))

pluto_grammar_file = os.path.join(_full_path, "pluto.lark")
engineering_units_grammar_file = os.path.join(
    _full_path, "engineering_units.lark"
)


with open(pluto_grammar_file) as f:
    pluto_grammar = "".join(f.readlines())

with open(engineering_units_grammar_file) as f:
    engineering_units_grammar = "".join(f.readlines())
