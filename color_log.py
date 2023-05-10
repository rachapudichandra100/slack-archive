import logging

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(programname,file):
    # Create top level logger
    log = logging.getLogger(programname)

    # Add console handler using our custom ColoredFormatter
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    #cf = CustomFormatter("[%(name)s][%(levelname)s]  %(message)s (%(filename)s:%(lineno)d)")
    ch.setFormatter(CustomFormatter())
    log.addHandler(ch)

    # Add file handler
    fh = logging.FileHandler(file)
    fh.setLevel(logging.INFO)
    ff = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(ff)
    log.addHandler(fh)
    return log


def get_logger1(logger_name, logger_file, log_level=logging.DEBUG):
    """ Setup the logger and return it. """
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
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
