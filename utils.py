#!/usr/bin/env python

import logging

class CustomFormatter(logging.Formatter):

    debugcolor = "\x1b[37;20m" #white
    infocolor = "\x1b[36;20m" #cyan
    warncolor = "\x1b[33;20m" #yellow
    errorcolor = "\x1b[31;1m" #bold_red
    criticalcolor = "\x1b[41;1m" # white on red bg
    
    reset = "\x1b[0m"
    #format = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s() | %(message)s | (%(filename)s:%(lineno)d)"
    format = "%(name)s | %(levelname)s | %(funcName)s() | %(message)s | (%(filename)s:%(lineno)d)"
    FORMATS = {
        logging.DEBUG: debugcolor + format + reset,
        logging.INFO: infocolor + format + reset,
        logging.WARNING: warncolor + format + reset,
        logging.ERROR: errorcolor + format + reset,
        logging.CRITICAL: criticalcolor + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    

def get_logger(logger_name, logger_file, log_level=logging.INFO):
    """ Setup the logger and return it. """
    log_format = "%(name)s | %(levelname)s | %(funcName)s() | %(message)s | (%(filename)s:%(lineno)d)"
    logging.basicConfig(level=log_level,
                        format=log_format,
                        datefmt='%y-%m-%d_%H:%M',
                        filename=logger_file,
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(log_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter(log_format)
    # tell the handler to use this format
    console.setFormatter(CustomFormatter())
    # add the handler to the root logger
    logging.getLogger(logger_name).addHandler(console)

    return logging.getLogger(logger_name)
