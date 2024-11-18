#!/bin/bash                                                                                                             
#SBATCH --job-name=optimalparam_job_desc
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=standard
####SBATCH --nodes=20
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=20
####SBATCH --time=48:00:00
#SBATCH --time=1:00:00
#SBATCH --account=hopp
#SBATCH --mail-user egrant@nrel.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
conda activate /scratch/egrant/ned_tools
module load cray-mpich
export TMPDIR=/scratch/egrant/sc_tmp/
srun -N 1 --ntasks-per-node=20 /scratch/egrant/ned_tools/bin/python /scratch/egrant/NED-toolbox/toolbox/postprocessing/param_sweep_auto/01b_combine_optimal_site_files_to_multifile.py e_capex_version atb_year fin_case