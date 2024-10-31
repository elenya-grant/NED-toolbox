#!/bin/bash                                                                                                             
#SBATCH --job-name=rerunjobname
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=100
#SBATCH --time=4:00:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
conda activate /scratch/egrant/ned_tools
module load cray-mpich
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 8 --ntasks-per-node=100 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/finance_reruns/rerun_simplex_new_costs_mpi.py costfilename.yaml
