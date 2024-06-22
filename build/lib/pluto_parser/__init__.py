import pathlib
import sys

from .parser import PlutoParser
from .transformer import PlutoTransformer


parse = PlutoParser.parse


def pluto_tree(pluto_file=None):
    """Print the parse tree."""
    if pluto_file is None:
        if len(sys.argv) != 2:
            raise Exception("Please provide .pluto file as an argument")
        pluto_file = sys.argv[1]
    with open(pluto_file) as f:
        contents = f.read()
        tree = PlutoParser.parse(contents)
        print(tree.pretty())


def pluto_parse(pluto_string, procedure_name="noname", debug=False):
    """Convert a string containing a PLUTO procedure into Python source.

    Having this as a separate method enables doing this without
    touching the file system.

    The procedure_name is needed to set the name of the generated
    Python class.
    If debug is True, return the transformed output and the tree.
    """
    tree = PlutoParser.parse(pluto_string)
    transformer = PlutoTransformer(procedure_name=procedure_name)
    transformed = transformer.transform(tree)
    if not debug:
        return transformed
    else:
        return transformed, tree


def pluto_parse_file(pluto_file=None):
    """Convert a .pluto file into a Python file at the same location.

    The file location can be passed as an argument to the function or
    as an argument to the registered console_script entrypoint.
    """
    if pluto_file is None:
        if len(sys.argv) != 2:
            raise Exception("Please provide .pluto file as an argument")
        pluto_file = sys.argv[1]

    with open(pluto_file) as f:
        contents = f.read()
    pluto_file_path = pathlib.Path(pluto_file)
    proc_name = pluto_file_path.stem
    python_source = pluto_parse(contents, procedure_name=proc_name)
    py_filename = pluto_file_path.with_suffix(".py")
    with open(py_filename, "w") as py:
        py.write(python_source)
