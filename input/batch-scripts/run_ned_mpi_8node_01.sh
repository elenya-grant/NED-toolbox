#!/bin/bash                                                                                                             
#SBATCH --job-name=ned_8node_01
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
####SBATCH --nodes=20
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=104
####SBATCH --time=48:00:00
#SBATCH --time=8:00:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
conda activate /scratch/egrant/ned_tools
module load cray-mpich
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 8 --ntasks-per-node=104 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/simulation/run_offgrid_onshore_baseline_mpi.py 6656 5320
