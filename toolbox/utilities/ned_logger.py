import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from toolbox import ROOT_DIR

LOG_DIR = os.path.join(str(ROOT_DIR),"dbg_log")
if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR,exist_ok=True)

log_description = "optimization_runs"
todays_date = datetime.now().strftime("%x").replace("/","-")
fname_log = os.path.join(LOG_DIR,"ned_debug--{}_{}.log".format(log_description,todays_date))

logging_level = logging.INFO
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s',datefmt='%m/%d/%Y %I:%M:%S %p')

logging.basicConfig(level=logging_level,
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            filename=fname_log,
                            filemode='a')

handler = logging.FileHandler(fname_log)
handler.setFormatter(formatter)

mpi_logger = logging.getLogger("MPI_LOGGER")

mpi_logger.setLevel(logging_level)
mpi_logger.addHandler(handler)
logging.getLogger("MPI_LOGGER").propagate = False

site_logger = logging.getLogger("SITE_LOGGER")
site_logger.setLevel(logging_level)
site_logger.addHandler(handler)
logging.getLogger("SITE_LOGGER").propagate = False

main_logger = logging.getLogger("MAIN")
main_logger.setLevel(logging_level)
main_logger.addHandler(handler)
logging.getLogger("MAIN").propagate = False

opt_logger = logging.getLogger("OPTIMIZATION")
opt_logger.setLevel(logging_level)
opt_logger.addHandler(handler)
logging.getLogger("OPTIMIZATION").propagate = False

# deep_bug_logger = logging.getLogger("DEEP BUGS")
# deep_bug_logger.setLevel(logging.DEBUG)
# deep_bug_logger.addHandler(handler)
# logging.getLogger("DEEP BUGS").propagate = False
# toolbox_logger = logging.getLogger('NedSim')
# toolbox_logger.addHandler(handler)