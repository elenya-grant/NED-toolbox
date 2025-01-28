#!/bin/bash                                                                                                             
#SBATCH --job-name=post_process_lcoh_iedo
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
####SBATCH --nodes=20
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=20
####SBATCH --time=48:00:00
#SBATCH --time=1:30:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
conda activate /scratch/egrant/ned_tools
module load cray-mpich
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 1 --ntasks-per-node=20 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/postprocessing/param_sweep_custom/get_best_lcoh_mpi.py
