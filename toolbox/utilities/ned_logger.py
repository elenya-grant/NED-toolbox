import sys
import os
import logging
from datetime import datetime
from pathlib import Path

logging_level = logging.INFO
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
run_suffix = '_' + datetime.now().isoformat().replace(':', '.')
log_path = Path.cwd() / "ned_log"
if not os.path.isdir(log_path):
    os.mkdir(log_path)
log_path = log_path / ("ned_res" + run_suffix + ".log")
# print(log_path)
toolbox_logger = logging.getLogger('NedSim')
logging.basicConfig(level=logging_level,
                        datefmt='%m-%d %H:%M',
                        filename=str(log_path),
                        filemode='w')
# toolbox_logger.info("info: I'm Here")
# toolbox_logger.warning("warning: I'm Here")
# toolbox_logger.error("error: I'm Here")
# toolbox_logger.debug("debug: I'm Here")
handler = logging.FileHandler(str(log_path))
handler.setFormatter(formatter)
# toolbox_logger = logging.getLogger('NedSim')
# toolbox_logger.addHandler(handler)