import json


def json_dump(data: dict, filepath: str, options: dict = None):
    """
    :param data: to be written
    :param filepath: JSON file
    :param options: to format obtained JSON file. See, e.g.,
    https://www.geeksforgeeks.org/python/how-to-convert-python-dictionary-to-json/ for some useful examples
    """
    if options is None:
        options = {}
    with open(filepath, "w") as f:
        json.dump(data, f, **options)
