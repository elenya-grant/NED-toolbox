# NED-toolbox
project code for GreenHEART scaled to the national scale
- [Install on Local Machine](#install-on-local-machine)
- [Install on HPC](#install-on-hpc)
- [Quick Tour](#quick-tour)

## Install on Local Machine
1. navigate to local target directory and clone the repository, then navigate to NED-toolbox
    ```
    cd /path/to/target/dir
    git clone https://github.com/elenya-grant/NED-toolbox.git
    cd NED-toolbox
    ```

2. Create and activate conda environment (named `ned_tools`)
    ```
    conda create --name ned_tools python=3.8 -y
    conda activate ned_tools
    ```
3. Install dependencies
    ```
    conda install -c conda-forge mpi4py petsc4py
    pip install -r requirements.txt
    ```
4. (option 1) install greenheart using pip 
    ```
    pip install -r requirements-dev.txt
    ```
4. (option 2) install greenheart using git
    ```
    git clone -b feature/ned https://github.com/elenya-grant/HOPP.git
    cd HOPP
    conda install -c conda-forge coin-or-cbc=2.10.8 -y
    conda install -c conda-forge glpk -y
    pip install -r requirements.txt
    pip install -e .
    cd
    cd /path/to/target/dir/NED-toolbox
    ```

5. Install NED-toolbox
    ```
    pip install -e .
    ```

6. Set environment for aggregated results folder used for preprocessing optimization runs. In the root directory, make a file titled ".env" and add the line `MAIN_RESULTS_FOLDER=/path/to/where/results/are`.

## Optional: install GreenHEART more locally
```
do something
```
<!-- ## Optional: replace certain HOPP files if pip installed hopp
1. navigate to NED-toolbox/toolbox/utilities
```
cd toolbox/utilities
```
2. if wanting to replace hopp resource.py, then run:
```
python customize_hopp_setup.py replace_resource
```

3. if wanting to replace hopp log.py, then run:
```
python customize_hopp_setup.py replace_log
``` -->

## Install on HPC
- setup github ssh on the HPC to use these instructions

### Install NED-toolbox
1. navigate to HPC target directory (such as /scratch/) and clone the repository (or your fork of NED-toolbox), then navigate to NED-toolbox
```
cd ../../scratch/<user>
git clone git@github.com:elenya-grant/NED-toolbox.git
cd NED-toolbox
```

2. Create and activate conda environment
```
module load conda
export CONDA_PKGS_DIRS=/scratch/<user>/.conda-pkgs
conda create --prefix /scratch/<user>/ned_tools python=3.8
conda activate /scratch/<user>/ned_tools
```
<!-- 3. install mpi4py
```
module load openmpi/4.1.6-gcc gcc-stdalone/13.1.0
python -m pip install mpi4py
``` -->
3. install mpi4py
    ```
    module load cray-mpich
    ```
    - check the mpicc, following command should return ``/opt/cray/pe/mpich/8.1.28/ofi/crayclang/16.0/bin/mpicc``
        ```
        which mpicc
        ```
    - install mpi4py
        ```
        python -m pip install mpi4py
        ```
4. install dependencies
```
pip install -r requirements.txt
```
5. install GreenHEART (see options in local install)
6. finalize setup
```
pip install -e .
```

## Quick Tour
<!-- ```
pip install HOPP git+https://github.com/elenya-grant/HOPP.git@feature/ned
``` -->
<!-- https://www.geeksforgeeks.org/how-to-install-a-python-package-from-a-github-repository/ -->
<!-- pip install git+file///path/to/your/git/project/
#Example: pip install git+file:///Users/ahmetdal/workspace/celery/ -->
<!-- /Users/egrant/opt/anaconda3/envs/ned_tools/lib/python3.8/site-packages/hopp/simulation/technologies/resource -->


