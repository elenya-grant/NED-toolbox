from pathlib import Path
from setuptools import setup, find_packages
import re


# Package meta-data.
NAME = "NED-Toolbox"
DESCRIPTION = "National Sweep GreenHEART Toolbox"
URL = "'https://github.com/elenya-grant/NED-toolbox"
EMAIL = "elenya.grant@nrel.gov"
AUTHOR = "elenya"
# REQUIRES_PYTHON = ">=3.9.0"
REQUIRES_PYTHON = ">=3.8.0"
VERSION = 0.0
ROOT = Path(__file__).parent

# Get package data
base_path = Path("toolbox")
package_data_files = []

package_data = {
    "toolbox": [],
    "ProFAST":[],
}

setup(
    name=NAME,
    version=VERSION,
    url=URL,
    description=DESCRIPTION,
    license='Apache Version 2.0',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(),
    package_data=package_data,
    include_package_data=True,
    install_requires=(base_path.parent / "requirements.txt").read_text().splitlines(),
    # tests_require=['pytest', 'pytest-subtests', 'responses']
)
