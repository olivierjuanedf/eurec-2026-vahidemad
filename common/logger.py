import os
import sys
import traceback
import logging
import warnings
from logging.handlers import RotatingFileHandler


LOG_LEVEL_STR_TO_INT = {name: value for name, value in vars(logging).items() if
                        isinstance(value, int) and name.isupper()}
TITLE_LOG_SEP = 6 * '#'


def deactivate_verbose_warnings(deact_deprecation_warn: bool = False):
    # deactivate some annoying and useless warnings in pypsa/pandas
    warnings.simplefilter(action='ignore', category=FutureWarning)
    warnings.simplefilter(action='ignore', category=UserWarning)
    # Suppress matplotlib specific DeprecationWarning from Pillow
    if deact_deprecation_warn:
        warnings.simplefilter(action="ignore", category=DeprecationWarning)


def init_logger(logger_dir: str, logger_name: str, log_level: str) -> logging.Logger:
    """
    Initialize logger
    Args:
        logger_dir (str): full path to directory in which log file must be saved
        logger_name (str): name of the logger file
        log_level (str): logger level to be used for current run

    Returns:
        logging.logger: the logger used for current run
    """

    try:
        if not os.path.isdir(logger_dir):
            os.makedirs(logger_dir, exist_ok=True)

        logger_path = os.path.join(logger_dir, logger_name)
        logger = setup_logger(log_file_name=logger_path, log_level_str=log_level)
    except Exception:
        print(traceback.print_exc())
        sys.exit('ERROR: an error occurred while creating the logger')
    return logger


def setup_logger(log_file_name: str, log_level_str: str) -> logging.Logger:
    """
    Create a logger to produce a log file or console display.

    Parameters:
    log_file_name (str): name of the log file
    log_level_str (str): log level as string input parameter ("DEBUG | INFO | WARNING .")
    Returns:
        logger (logging.Logger): logger Instance.
    """
    if os.path.isfile(log_file_name):
        os.remove(log_file_name)

    log = logging.getLogger()

    # Clear any default or previously added handlers
    for handler in log.handlers[:]:
        log.removeHandler(handler)
    
    # log file
    formatter_log = logging.Formatter('%(asctime)s -- general -- %(filename)s '
                                      '-- %(levelname)s -- %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(log_file_name,
                                                        maxBytes=1024 * 1024, backupCount=1, encoding='utf-8')
    file_handler.setFormatter(formatter_log)

    # log console
    formatter_console = logging.Formatter('[%(levelname)s]\t%(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter_console)

    log_level = LOG_LEVEL_STR_TO_INT.get(log_level_str.upper(), logging.INFO)
    log.setLevel(log_level)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)

    return log


def stop_logger():
    # End tracking process
    # Write execution report
    logger = logging.getLogger()

    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)
