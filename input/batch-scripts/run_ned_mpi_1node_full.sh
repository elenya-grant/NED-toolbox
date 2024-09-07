#!/bin/bash                                                                                                             
#SBATCH --job-name=ned-1noderun_full
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
####SBATCH --nodes=20
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=104
####SBATCH --time=48:00:00
#SBATCH --time=1:00:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
conda activate /scratch/egrant/ned_tools
module load cray-mpich
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 1 --ntasks-per-node=104 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/simulation/run_offgrid_onshore_baseline_mpi.py 104 16