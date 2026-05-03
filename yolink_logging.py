import logging


OFFLINE = 35
BUSY = 25


def _log_for_level(logger, level, message, *args, **kwargs):
    if logger.isEnabledFor(level):
        logger._log(level, message, args, **kwargs)


def install_custom_log_levels():
    if logging.getLevelName(OFFLINE) != 'OFFLINE':
        logging.addLevelName(OFFLINE, 'OFFLINE')
    if logging.getLevelName(BUSY) != 'BUSY':
        logging.addLevelName(BUSY, 'BUSY')

    if not hasattr(logging, 'OFFLINE'):
        logging.OFFLINE = OFFLINE
    if not hasattr(logging, 'BUSY'):
        logging.BUSY = BUSY

    if not hasattr(logging.Logger, 'offline'):
        def offline(self, message, *args, **kwargs):
            _log_for_level(self, OFFLINE, message, *args, **kwargs)

        logging.Logger.offline = offline

    if not hasattr(logging.Logger, 'busy'):
        def busy(self, message, *args, **kwargs):
            _log_for_level(self, BUSY, message, *args, **kwargs)

        logging.Logger.busy = busy

    if not hasattr(logging, 'offline'):
        def offline(message, *args, **kwargs):
            logging.log(OFFLINE, message, *args, **kwargs)

        logging.offline = offline

    if not hasattr(logging, 'busy'):
        def busy(message, *args, **kwargs):
            logging.log(BUSY, message, *args, **kwargs)

        logging.busy = busy


def resolve_log_level(level_value):
    if isinstance(level_value, str):
        normalized = level_value.strip().upper()
        if normalized == 'OFFLINE':
            return OFFLINE
        if normalized == 'BUSY':
            return BUSY
        return getattr(logging, normalized, level_value)

    return level_value


install_custom_log_levels()