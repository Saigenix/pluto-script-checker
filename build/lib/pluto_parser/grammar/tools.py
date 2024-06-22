import pathlib
import re
import os


def convert_ebnf_to_lark(
    ebnf_grammar,
    pre_replacements=None,
    rules_to_terminals=None,
    post_replacements=None,
):
    """Convert a given ISO EBNF grammar to a lark grammar and return that.

    (pre|post)_replacements is a list of tuples containing re.sub pattern/repl
    arguments. pre_replacements are applied before anything else, and
    post_replacements after all other operations.
    """
    res = ebnf_grammar
    if pre_replacements:
        for pattern, repl in pre_replacements:
            res = re.sub(pattern, repl, res, flags=re.MULTILINE)
    # replace "=" by ":" and remove newline after and spaces around ":"
    # Avoid catching "=" elsewhere, e.g. in strings
    res = re.sub(r"^([\w\s]+)=\s*[\n]?\s*", r"\1: ", res, flags=re.MULTILINE)
    # replace "," by " ", avoid replacing '","' by using negative lookahead
    res = re.sub(r'\s*,(?!")\s*', r" ", res)
    # Remove trailing ";"
    res = re.sub(r";$", r"", res, flags=re.MULTILINE)
    # Replace linebreak after |
    res = re.sub(r"\|\n[\s]*", r"| ", res, flags=re.MULTILINE)
    # convert { }- to ( )+ and { } to ( )*, but not "{" and "}"
    # this uses regex negative lookahead/lookbehind
    res = re.sub(r"}-", r")+", res)
    res = re.sub(r'}(?!")', r")*", res)  # no lookbehind, avoid false positives
    res = re.sub(r'(?<!"){', r"(", res)  # no lookahead, avoid false positives

    # lower-case and underscore_space all the rules (begin with longest)
    rules = re.findall(r"^[\w\s]+:", res, re.MULTILINE)
    # FIXME: this adds the \n in front of absolute time constant
    rules = sorted(
        [r.rstrip(" :") for r in rules], key=lambda s: len(s), reverse=True
    )
    for r in rules:
        res = res.replace(r, r.lower().replace(" ", "_"))

    # Make terminals UPPERCASE manually - no idea how to do this otherwise
    if rules_to_terminals:
        rules_to_terminals = sorted(
            rules_to_terminals, key=lambda s: len(s), reverse=True
        )
        for rule in sorted(
            rules_to_terminals, key=lambda s: len(s), reverse=True
        ):
            res = re.sub(r"\b" + rule + r"\b", rule.upper(), res)
    if post_replacements:
        for pattern, repl in post_replacements:
            res = re.sub(pattern, repl, res, re.MULTILINE)

    # Indent | to colon
    res = res.splitlines()
    for idx, line in enumerate(res):
        if line.lstrip(" ").startswith("|"):
            column = res[idx - 1].find(":")
            if column == -1:  # no colon found, maybe a pipe
                column = res[idx - 1].find("|")
            res[idx] = " " * column + line.lstrip(" ")

    res = "\n".join(res)
    return res


def ebnf_to_lark_file(
    ebnf_filepath,
    pre_replacements=None,
    rules_to_terminals=None,
    post_replacements=None,
):
    """Convert a given file containing an ISO EBNF grammar to a .lark file.

    The .lark file of the same name will be placed beside the EBNF file.
    (pre|post)_replacements is a list of tuples containing re.sub pattern/repl
    arguments. pre_replacements are applied before anything else, and
    post_replacements after all other operations.
    """
    with open(ebnf_filepath) as ebnf:
        contents = "".join(ebnf.readlines())
    res = convert_ebnf_to_lark(
        contents, pre_replacements, rules_to_terminals, post_replacements
    )
    targetpath = pathlib.Path(ebnf_filepath).with_suffix(".lark")
    with open(targetpath, "w") as t:
        t.write(res)


def convert_grammar_files():
    """Convert engineering_units.ebnf and pluto.ebnf to .lark files."""
    # FIXME: this needs to be able to import pluto, but if the grammar is bad \
    # we can't call this to fix it.
    full_path = os.path.dirname(os.path.abspath(__file__))
    ebnf_to_lark_file(
        os.path.join(full_path, "pluto.ebnf"),
        pluto_pre_replacements,
        pluto_rules_to_terminals,
        pluto_post_replacements,
    )
    ebnf_to_lark_file(
        os.path.join(full_path, "engineering_units.ebnf"),
        eng_units_pre_replacements,
        eng_units_rules_to_terminals,
        eng_units_post_replacements,
    )


eng_units_pre_replacements = [
    (r"\? Engineering Units \?", "Engineering Units"),
    (r"Unit Simple Factor  =", r"Unit Simple Factor ="),
]
eng_units_rules_to_terminals = [
    "decimal_submultiple_prefix",
    "decimal_multiple_prefix",
    "decimal_prefix",
    "binary_prefix",
    "multiple_and_submultiple_simple_unit",
    "submultiple_only_simple_unit",
    "multiple_only_simple_unit",
    "unsigned_integer",
]
eng_units_post_replacements = [
    (
        r"UNSIGNED_INTEGER : \(Digit \)\+",
        r"%import common.DIGIT\n%import common.INT -> UNSIGNED_INTEGER\n",
    ),
    # unit_factor had one unit_simple_factor too many compared
    # with its railroad diagram and B.2.g.7!
    (r"unit_simple_factor \(unit_simple_factor", r"(unit_simple_factor"),
    # Fix order in grammar terminal
    (r'\| "B" \| "Bd"', r'| "Bd" | "B"'),
    (
        r'"m" \| "g" \| "s" \| "A" \| "K" \| "mol"',
        r'"mol" | "Sv" | "Wb" | "m" | "g" | "s" | "A" | "K"',
    ),
    (r'"Gy" \| "Sv"', r'"Gy"'),
    (r'"Wb" \| "T"', r'"T"'),
    # Tree shaping. start with \b to make replacement function idempotent
    (r"\bengineering_units :", r"engineering_units :"),
    (r"\bunit_reference :", r"!?unit_reference :"),
    (r"\bunit_product :", r"!?unit_product :"),
    (r"\bunit_factor :", r"!?unit_factor :"),
    (r"\bunit_simple_factor :", r"!?unit_simple_factor :"),
    (r"\bunit_exponent :", r"!?unit_exponent :"),
]

# FIXME: Replacing '\"' by "\"" and '"' by "\"" is too hairy, do it in pluto.g
pluto_pre_replacements = [
    (r"\? Engineering Units \?", "engineering_units"),
    (
        '"in case", Expression, "is", Case Tag, ":", {Step Statement, ";"}-',
        '"in case", Expression, "is", Case Tag, ":", {Step Statement, ";"}-,',
    ),
    (r"([0-9]) \* Digit", r"Digit ~ \1"),
]

pluto_rules_to_terminals = [
    "absolute_time_constant",
    "activity_statement",
    "addition_operator",
    "argument_name",
    "characters",
    "confirmation_status",
    "day",
    "day_of_month",
    "days",
    "digit",
    "directive_name",
    "enumerated_constant",
    "event_name",
    "fraction_of_second",
    "hexadecimal_constant",
    "hexadecimal_digit",
    "hexadecimal_symbol",
    "hour",
    "hours",
    "identifier",
    "identifier_first_word",
    "identifier_subsequent_word",
    "letter",
    "minute",
    "minutes",
    "month",
    "multiplication_operator",
    "negation_boolean_operator",
    "nonstandard_function_name",
    "nonstandard_object_operation_name",
    "nonstandard_object_property_name",
    "object_name",
    "object_type",
    "relational_operator",
    "reporting_data_name",
    "second",
    "seconds",
    "set_name",
    "sign",
    "standard_function_name",
    "standard_object_property_name",
    "step_name",
    "string_constant",
    "variable_name",
    "year",
]

pluto_post_replacements = [
    (
        r"YEAR : DIGIT ~ 4",
        r'YEAR : DIGIT ~ 4\n%import .engineering_units.engineering_units\n%import common.WS\n%ignore WS\nCOMMENT  : ("/*" /([^\*])|(\* [^\/])/* "*/")\n         | ("//" /[^\n]*/ NEWLINE)\nNEWLINE : "\n"\n%ignore COMMENT\n',
    ),  # noqa
    (r"\(LETTER \| DIGIT \)\*", '(LETTER | DIGIT | "_")*'),
    ("boolean_constant :", "!boolean_constant :"),
    ("boolean_operator :", "!boolean_operator :"),
    ("relative_time_constant :", "!relative_time_constant :"),
]
