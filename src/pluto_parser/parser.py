from functools import partial

from lark import Lark

from .grammar import pluto_grammar_file, engineering_units_grammar_file


# Enable instantiation with different (e.g. start) arguments in tests
partial_parser = partial(
    Lark.open,
    pluto_grammar_file,
    start="procedure_definition",
    parser="earley",
    debug=False,
    keep_all_tokens=False,
    propagate_positions=True,
)

# Enable instantiation with different (e.g. parser) arguments in tests
partial_eng_units_parser = partial(
    Lark.open,
    engineering_units_grammar_file,
    start="engineering_units",
    parser="earley",
    debug=False,
)

PlutoParser = partial_parser()
EngineeringUnitsParser = partial_eng_units_parser()
