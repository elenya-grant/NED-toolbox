#!/bin/bash                                                                                                             
#SBATCH --job-name=ned-2noderun_208
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
####SBATCH --nodes=20
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=104
####SBATCH --time=48:00:00
#SBATCH --time=1:00:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load openmpi/4.1.6-gcc gcc-stdalone/13.1.0
module load conda
conda activate /scratch/egrant/ned_tools
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 2 --ntasks-per-node=104 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/simulation/run_offgrid_onshore_baseline_mpi.py 208 0