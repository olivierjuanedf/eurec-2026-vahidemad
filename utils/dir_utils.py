import logging
import os
from pathlib import Path


def check_file_existence(file: str, file_descr: str = None):
    """
    Check existence of a given file before doing some operations on it (e.g., reading it)

    :param file: file whose existence must be checked
    :param file_descr: description of this file, used in error msg if missing
    """
    if not os.path.isfile(file):
        msg_prefix = 'File' if file_descr is None else f'{file_descr} file'
        raise Exception(f'{msg_prefix} {file} does not exist -> STOP')


def uniformize_path_os(path_str: str) -> str:
    return os.path.normpath(path_str)


def make_dir(full_path: str, with_warning: bool = False):
    if os.path.exists(full_path):
        if with_warning:
            logging.warning(f'Directory {full_path} already exists -> not created again')
    else:
        Path(full_path).mkdir(parents=True)


def delete_files(directory: str, str_in_file: str = None, suffix: str = None):
    path = Path(directory)
    str_search = f'*{suffix}' if suffix is not None else str_in_file
    for file in path.rglob(str_search):
        if file.is_file():
            logging.debug(f"Deleting: {file}")
            file.unlink()
