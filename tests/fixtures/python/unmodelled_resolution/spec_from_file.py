import importlib.util


def load(name: str, path: str):
    return importlib.util.spec_from_file_location(name, path)
