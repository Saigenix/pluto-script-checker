"""Transformers that turn a parsed tree of PLUTO code into Python source.

IMPLEMENTATION NOTES:
* Every rule in the grammar needs a method in the respective transformer.
* In the docstring of the method, note the relevant section of the standard
  defining the logic. The PLUTO standard (ECSS‐E‐ST‐70‐32C, shorthand: E32) is
  assumed by default, if referencing ECSS-E-ST-70-31C, prefix E31.
* In implementation code, where appropriate note the relevant section in the
  standard (e.g. A.3.9.34-Definition)
* If the implementation remains incomplete or otherwise not adhering to the
  standard, leave a "TODO:" or "FIXME:" comment.
* Skeleton implementations are there. Modify the list of parameters. You can
  use Lark's `@va_inline` decorator if wanted.
* Hint: It's probably easiest to start from the leaves of the tree and work
  towards the root.
* The method needs to be tested. Add tests in `test_[Pluto|Unit]Transformer.py`
  as appropriate. Name rule tests as `test_<rulename>_<some_postfix>`.
* You can use `pluto_parser` test fixture, which accepts a `start` kwarg. This
  way, you can create a tree that starts at the rule under question, which
  simplifies the PLUTO code you have to feed to the parser to test. See
  the already existing tests.
* Test all configurations, edge cases, and also erroneous examples ( using
  e.g. `pytest.raises`) if possible.
"""

from collections import OrderedDict
from textwrap import indent

from lark import Transformer, v_args, Token


# Python source snippets
PREAMBLE = """\
# This is auto-generated code from the source Pluto file. Do not modify!
"""


class UnitsTransformer(Transformer):
    """Transformer for the engineering units grammar."""

    def engineering_units(self, args):
        """Parse and return unit strings."""
        return "".join(args)

    def unit_reference(self, args):
        return "".join(args)

    def unit_product(self, args):
        return "".join(args)

    def unit_factor(self, args):
        return "".join(args)

    def unit_simple_factor(self, args):
        return "".join(args)

    def unit_exponent(self, args):
        return "".join(args)


class PlutoTransformer(UnitsTransformer):
    """Transformer for the PLUTO grammar.

    The rule implementations return strings fit for assembling a Python script.
    Methods and attributes which are not Rules implementations are prefixed
    with _ to avoid name collisions.
    """

    def __init__(self, procedure_name="noname"):
        """Constructor to make the UnitsTransformer methods available."""
        # FIXME: This is hacky, did not see another way to achieve this in Lark
        # Make sure the namespaced rules from the engineering units grammar get
        # picked up
        for k in UnitsTransformer.__dict__.keys():
            if not k.startswith("__"):
                setattr(self, "engineering_units__" + k, getattr(self, k))
        self._procedure_name = procedure_name

        # Initialize the generated python source string
        self._root_items = OrderedDict()
        self._root_items["preamble"] = str(PREAMBLE)
        self._root_items["procedure"] = ""  # a placeholder for correct order

    def _indented(self, text, level=0):
        """Conveniently indent string by an indentation level."""
        return indent(text, " " * level * 4)

    @v_args(inline=True)
    def activity_call(self, activity_reference, *args):
        text = ""
        text += "arguments = OrderedDict()\n"
        text += "directives = OrderedDict()\n"

        record = []

        def process_args(args):
            nonlocal text
            nonlocal record
            if type(args) == list or type(args) == tuple:
                for arg in args:
                    process_args(arg)
            elif type(args) == dict:
                for key, value in args.items():
                    text += f"arguments['{key}'] = dict()\n"
                    record.append(key)
                    process_args(value)
                record.pop()
            else:
                if record:
                    key_text = "arguments['" + "']['".join(record) + "']"
                    text += args.replace("arguments", key_text)
                else:
                    text += args

        process_args(args)

        text += "activity_call = create_activity_call(caller, '{}', arguments, directives)\n".format(
            activity_reference
        )
        return Token("activity_call", text)

    @v_args(inline=True)
    def activity_reference(self, object_reference):
        return Token("activity_reference", object_reference)

    @v_args(inline=True)
    def argument_reference(self, obj_ref):
        source = "get_variable(caller, '{}').value".format(obj_ref)
        return Token("argument_reference", source)

    def arguments(self, args):
        return args

    def array_argument(self):
        raise NotImplementedError

    @v_args(meta=True)
    def assignment_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        var_ref = args[0]
        expression = args[1]
        func = "def {}(caller):\n".format(
            stmt
        ) + "    caller.assignement('{}', {})\n".format(var_ref, expression)
        self._root_items[stmt] = func
        return Token("assignment_statement", stmt)

    @v_args(inline=True)
    def boolean_constant(self, cons):
        # TODO: Convert back to terminal as soon as Lark can transform
        # terminals (#389)
        source = "True" if cons.value == "TRUE" else "False"
        return Token("boolean_constant", source)

    def boolean_operator(self, args):
        source = "{}".format(args[0].lower())
        return Token("boolean_operator", source)

    def case_statement(self):
        raise NotImplementedError

    def case_tag(self):
        raise NotImplementedError

    def comparative_expression(self, args):
        source = "".join(args)
        return Token("comparative_expression", source)

    def confirmation_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.confirmation.append({})\n".format(stmt)
        return Token("confirmation_body", source)

    @v_args(inline=True)
    def constant(self, value):
        # TODO: Incomplete
        if value.type == "ABSOLUTE_TIME_CONSTANT":
            time_cons = value
            date, time = time_cons[0:-1].split("T")
            year, month, day = date.split("-")
            hour, minute, sec = time.split(":")
            second, microsec = sec.split(".")
            source = "datetime({}, {}, {}, {}, {}, {}, {})".format(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second),
                int(microsec),
            )
        else:
            source = value
        return Token("constant", source)

    @v_args(inline=True)
    def continuation_action(self, action):
        if action.type == "raise_event":
            event = action.value
            res = ":".join(["raise event", event])
        else:
            res = "{}".format(action)
        return Token("continuation_action", res)

    def continuation_test(self, args):
        source = ""
        source += "continuation = OrderedDict()\n"
        source += "raise_event = None\n"
        for i in range(0, len(args), 2):
            confirmation_status = args[i]
            if confirmation_status == "confirmed":
                confirmation_status = "ConfirmationStatus.CONFIRMED"
            elif confirmation_status == "not confirmed":
                confirmation_status = "ConfirmationStatus.NOT_CONFIRMED"
            elif confirmation_status == "aborted":
                confirmation_status = "ConfirmationStatus.ABORTED"
            else:
                raise ValueError()
            continuation_action = args[i + 1]
            if continuation_action.startswith("raise event"):
                event_name = args[i + 1].split(":")[1]
                source += "raise_event = '{}'\n".format(event_name)
                source += "continuation[{}] = {}\n".format(
                    confirmation_status, "ContinuationAction.RAISE_EVENT"
                )
            else:
                if continuation_action == "resume":
                    continuation_action = "ContinuationAction.RESUME"
                elif continuation_action == "abort":
                    continuation_action = "ContinuationAction.ABORT"
                elif continuation_action == "restart":
                    continuation_action = "ContinuationAction.RESTART"
                elif continuation_action == "ask user":
                    continuation_action = "ContinuationAction.ASK_USER"
                elif continuation_action == "continue":
                    continuation_action = "ContinuationAction.CONTINUE"
                elif continuation_action == "terminate":
                    continuation_action = "ContinuationAction.TERMINATE"
                else:
                    raise ValueError()
                source += "continuation[{}] = {}\n".format(
                    confirmation_status, continuation_action
                )
        return Token("continuation_test", source)

    @v_args(inline=True)
    def description(self, string_constant):
        source = string_constant
        return Token("description", source)

    def directives(self, args):
        source = ""
        for i in range(0, len(args), 2):
            source += "directives['{}'] = {}\n".format(args[i], args[i + 1])
        return Token("directives", source)

    def enumerated_set_declaration(self):
        raise NotImplementedError

    def enumerated_set_reference(self):
        raise NotImplementedError

    @v_args(meta=True)
    def event_declaration(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        event_name = args[0]
        event_description = args[1] if len(args) > 1 else None
        event_args = "'{}'".format(event_name)
        if event_description:
            event_args += ", {}".format(event_description)
        func = "def {}(caller):\n".format(
            stmt
        ) + "    caller.event_declaration({})\n".format(event_args)
        self._root_items[stmt] = func
        return Token("event_declaration", stmt)

    @v_args(inline=True)
    def event_reference(self, event):
        return Token("event_reference", event)

    def expression(self, args):
        if len(args) == 1:
            source = "lambda x: {}".format(args[0])
        elif len(args) == 3 and args[0].type == "relational_expression":
            source = "lambda x: {} {} {}".format(
                args[0], args[1], args[2].replace("lambda x: ", "")
            )
        else:
            raise NotImplementedError
        return Token("expression", source)

    @v_args(inline=True)
    def factor(self, value):
        if value.type == "simple_factor":
            source = value
        else:
            raise NotImplementedError
        return Token("factor", source)

    @v_args(inline=True)
    def flow_control_statement(self, stmt):
        return Token("flow_control_statement", stmt)

    def for_statement(self):
        raise NotImplementedError

    def function(self, args):
        source = "".join(args)
        return Token("function", source)

    @v_args(meta=True)
    def if_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        if (
            args[0].type != "IF"
            or args[1].type != "expression"
            or args[2].type != "THEN"
        ):
            raise ValueError()
        expression = args[1]
        if_stmts = []
        else_stmts = []
        i = 3
        while i < len(args) and args[i].type == "step_statement":
            if_stmts.append(args[i].value)
            i += 1
        if_stmts = ", ".join(if_stmts)
        i += 1
        while i < len(args) and args[i].type == "step_statement":
            else_stmts.append(args[i].value)
            i += 1
        else_stmts = ", ".join(else_stmts)
        func = (
            "def {}(caller):\n".format(stmt)
            + "    expression = {}\n".format(expression)
            + "    if_stmts = ["
            + if_stmts
            + "]\n"
            + "    else_stmts = ["
            + else_stmts
            + "]\n"
            + "    caller.if_statement(expression, if_stmts, else_stmts)\n"
        )
        self._root_items[stmt] = func
        return Token("if_statement", stmt)

    def inform_user_statement(self, args):
        raise NotImplementedError

    @v_args(meta=True)
    def initiate_activity_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        parameters = args[0]
        if len(args) > 1:
            func = "def {}(caller):\n".format(stmt) + self._indented(
                parameters
                + f"caller.refer_by['{args[1]}'] = caller.initiate_activity(activity_call)\n",
                1,
            )
        else:
            func = "def {}(caller):\n".format(stmt) + self._indented(
                parameters + "caller.initiate_activity(activity_call)\n", 1
            )
        self._root_items[stmt] = func
        return Token("initiate_activity_statement", stmt)

    @v_args(meta=True)
    def initiate_and_confirm_activity_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        parameters = args[0]
        refer_by = None
        continuation_test = None

        if len(args) == 3:
            refer_by = args[1]
            continuation_test = args[2]
        elif len(args) == 2:
            if args[1].type == "continuation_test":
                continuation_test = args[1]
            else:
                refer_by = args[1]

        # need to provide empyt parameters if no continuation test provided
        if not continuation_test:
            continuation_test = ""
            continuation_test += "continuation = OrderedDict()\n"
            continuation_test += "raise_event = None\n"
        if refer_by:
            func = (
                "def {}(caller):\n".format(stmt)
                + self._indented(parameters, 1)
                + self._indented(continuation_test, 1)
                + f"    caller.refer_by['{refer_by}'] = caller.initiate_and_confirm_activity"
                + "(activity_call, continuation, raise_event)\n"
            )
        else:
            func = (
                "def {}(caller):\n".format(stmt)
                + self._indented(parameters, 1)
                + self._indented(continuation_test, 1)
                + "    caller.initiate_and_confirm_activity"
                + "(activity_call, continuation, raise_event)\n"
            )
        self._root_items[stmt] = func
        return Token("initiate_and_confirm_activity_statement", stmt)

    @v_args(meta=True)
    def initiate_and_confirm_step_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        step_name = args[0]
        step_definition = args[1]
        continuation_test = args[2] if len(args) > 2 else None
        # need to provide empyt parameters if no continuation test provided
        if not continuation_test:
            continuation_test = ""
            continuation_test += "continuation = OrderedDict()\n"
            continuation_test += "raise_event = None\n"
        func = "def {}(caller):\n".format(stmt) + self._indented(
            "step = Step_{}(caller)\n".format(stmt)
            + continuation_test
            + "caller.initiate_and_confirm_step"
            "(step, continuation, raise_event)\n",
            1,
        )
        self._root_items[stmt] = func
        step_class = (
            "class Step_{}(Step):\n\n".format(stmt)
            + "    def __init__(self, caller):\n"
            + "        super().__init__(caller)\n"
            + step_definition
        )
        self._root_items[step_name] = step_class
        return Token("initiate_and_confirm_step_statement", stmt)

    @v_args(meta=True)
    def initiate_and_confirm_step_statement_watchdog(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        step_name = args[0]
        step_definition = args[1]
        continuation_test = args[2] if len(args) > 2 else None
        # need to provide empyt parameters if no continuation test provided
        if not continuation_test:
            continuation_test = ""
            continuation_test += "continuation = OrderedDict()\n"
            continuation_test += "raise_event = None\n"
        func = "def {}(caller):\n".format(stmt) + self._indented(
            "step = Step_{}(caller)\n".format(stmt)
            + "caller.watchdogs['Step_{}'] = step\n".format(stmt)
            + continuation_test
            + "caller.initiate_and_confirm_step"
            "(step, continuation, raise_event)\n",
            1,
        )
        self._root_items[stmt] = func
        step_class = (
            "class Step_{}(Step):\n\n".format(stmt)
            + "    def __init__(self, caller):\n"
            + "        super().__init__(caller)\n"
            + step_definition
        )
        self._root_items[step_name] = step_class
        return Token("initiate_and_confirm_step_statement_watchdog", stmt)

    def initiate_in_parallel_statement(self):
        raise NotImplementedError

    def integer_constant(self, args):
        if args[0].type == "HEXADECIMAL_CONSTANT":
            source = "int('{}', 16)".format(args[0])
        else:
            source = "ureg('{}')".format("".join(args))
        return Token("integer_constant", source)

    @v_args(meta=True)
    def log_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        text = []
        for arg in args:
            if arg.type != "COMMA":
                text.append("{}".format(arg))
        text = ", ".join(text)
        func = "def {}(caller):\n".format(stmt) + "    caller.log({})\n".format(text)
        self._root_items[stmt] = func
        return Token("log_statement", stmt)

    def object_operation(self, args):
        raise NotImplementedError

    def object_operation_request_statement(self, args):
        raise NotImplementedError

    def object_property(self, args):
        source = "/".join(reversed(args))
        return Token("object_property", source)

    @v_args(inline=True)
    def object_property_request(self, object_property, object_reference=None):
        if object_reference:
            # a ReportingData element
            source = "/".join([object_reference, object_property])
            source = f"get_reporting_data(caller, '{source}')"
        else:
            # a variable
            source = "get_variable(caller, '{}').value".format(object_property)
        return Token("object_property_request", source)

    def standard_object_property_name(self, args):
        source = ".".join(args[::-1])
        return Token("standard_object_property_name", source)

    def nonstandard_object_property_name(self, args):
        source = ".".join(args[::-1])
        return Token("nonstandard_object_property_name", source)

    def object_reference(self, args):
        source = "/".join(reversed(args))
        return Token("object_reference", source)

    def preconditions_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.preconditions.append({})\n".format(stmt)
        return Token("preconditions_body", source)

    @v_args(inline=True)
    def predefined_type(self, arg):
        datatype = arg.type if not arg.type.startswith("__ANON") else arg.value
        if datatype == "BOOLEAN":
            source = "bool()"
        elif datatype in ["unsigned integer", "signed integer"]:
            source = "int()"
        elif datatype == "Boolean":
            source = "bool()"
        elif datatype == "REAL":
            source = "float()"
        elif datatype == "STRING":
            source = "str()"
        elif datatype == "absolute time":
            source = "datetime.utcnow()"
        elif datatype == "relative time":
            source = "timedelta()"
        else:
            raise NotImplementedError
        return Token("predefined_type", source)

    def predefined_value_set_reference(self):
        raise NotImplementedError

    def procedure_declaration_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.declaration.append({})\n".format(stmt)
        return Token("procedure_declaration_body", source)

    @v_args(meta=True)
    def procedure_definition(self, args, meta):
        proc = (
            "class Procedure_(Procedure):\n\n"
            + "    def __init__(self, **kwargs):\n"
            + "        super().__init__(**kwargs)\n"
        )
        for token in args:
            proc += self._indented(token, 1)
        self._root_items["procedure"] = proc
        source = "\n\n".join(self._root_items.values())
        return Token("procedure_definition", source)

    def procedure_main_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.main_body.append({})\n".format(stmt)
        return Token("procedure_main_body", source)

    @v_args(inline=True)
    def procedure_statement(self, stmt):
        return Token("procedure_statement", stmt)

    def product(self, args):
        source = "".join(args)
        return Token("product", source)

    def property_data_type(self, args):
        raise NotImplementedError

    def property_value_set(self, args):
        raise NotImplementedError

    @v_args(inline=True)
    def raise_event(self, event):
        return Token("raise_event", event)

    def real_constant(self, args):
        source = "ureg('{}')".format("".join(args))
        return Token("real_constant", source)

    def record_argument(self, args):
        return {args[0]: args[1]}

    def relational_expression(self, args):
        source = "".join(args)
        return Token("relational_expression", source)

    @v_args(inline=True)
    def relational_operator(self, operator):
        if operator == "=":
            source = " == "
        else:
            source = " {} ".format(operator)
        return Token("relational_operator", source)

    def relative_time_constant(self, args):
        parts = []
        for i in range(0, len(args), 2):
            magnitude = args[i]
            unit = args[i + 1]
            parts.append("ureg('{}{}')".format(magnitude, unit))
        source = "+".join(parts)
        return Token("relative_time_constant", source)

    def repeat_statement(self, args):
        raise NotImplementedError

    def reporting_data_reference(self, args):
        raise NotImplementedError

    def save_context(self, args):
        raise NotImplementedError

    def save_context_statement(self, args):
        raise NotImplementedError

    def set_procedure_context_statement(self, args):
        raise NotImplementedError

    def set_step_context_statement(self, args):
        raise NotImplementedError

    def step_declaration_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.declaration.append({})\n".format(stmt)
        return Token("step_declaration_body", source)

    def step_definition(self, bodies):
        source = ""
        for body in bodies:
            source += self._indented(body, 1)
        return Token("step_definition", source)

    @v_args(inline=True)
    def simple_argument(self, argument_name, value):
        text = "arguments['{}'] = {}\n".format(argument_name, value)
        return Token("simple_argument", text)

    def simple_factor(self, args):
        if args[0].type in [
            "constant",
            "variable_reference",
            "argument_reference",
            "object_reference",
            "object_property_request",
            "function",
        ]:
            source = args[0]
        elif args.type == "SIGN":
            source = "".join(args)
        else:
            raise NotImplementedError
        return Token("simple_factor", source)

    def step_main_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.main_body.append({})\n".format(stmt)
        return Token("step_main_body", source)

    @v_args(inline=True)
    def step_statement(self, stmt):
        return Token("step_statement", stmt)

    def system_element_reference(self):
        raise NotImplementedError

    def term(self, args):
        source = "".join(args)
        return Token("term", source)

    @v_args(inline=True)
    def timeout(self, expression, raise_event=None):
        source = "timeout={}".format(expression)
        if raise_event:
            source += ", raise_event='{}'".format(raise_event)
        return Token("timeout", source)

    @v_args(meta=True)
    def variable_declaration(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        var_name = args[0]
        var_type = args[1]
        func = "def {}(caller):\n".format(
            stmt
        ) + "    caller.variable_declaration('{}', {})\n".format(var_name, var_type)
        self._root_items[stmt] = func
        return Token("variable_declaration", stmt)

    @v_args(inline=True)
    def variable_reference(self, var_reference):
        return Token("variable_reference", var_reference)

    @v_args(inline=True)
    def wait_statement(self, stmt):
        return Token("wait_statement", stmt)

    @v_args(meta=True)
    def wait_for_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        expression = args[0]
        func = "def {}(caller):\n".format(
            stmt
        ) + "    caller.wait_for_relative_time({})\n".format(expression)
        self._root_items[stmt] = func
        return Token("wait_for_statement", stmt)

    @v_args(meta=True)
    def wait_for_event_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        event_reference = args[0]
        timeout = args[1] if len(args) > 1 else None
        if not timeout:
            timeout = "timeout=None"
        func = (
            "def {}(caller):\n".format(stmt)
            + f"    caller.wait_for_event(get_event(caller, '{event_reference}'), {timeout})\n"
        )
        self._root_items[stmt] = func
        return Token("wait_for_event_statement", stmt)

    @v_args(meta=True)
    def wait_until_statement(self, args, meta):
        stmt = f"stmt_pos_{meta.start_pos}"
        expression = args[0]
        timeout = args[1] if len(args) > 1 else None
        if not timeout:
            timeout = "timeout=None"
        func = "def {}(caller):\n".format(
            stmt
        ) + "    caller.wait_until_expression({})\n".format(
            ", ".join([expression, timeout])
        )
        self._root_items[stmt] = func
        return Token("wait_until_statement", stmt)

    def watchdog_body(self, stmts):
        source = ""
        for stmt in stmts:
            source += "    self.watchdog_body.append({})\n".format(stmt)
        return Token("watchdog_body", source)

    def while_statement(self):
        raise NotImplementedError
