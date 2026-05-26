#!/bin/bash

# Ensure the results directory exists
#mkdir -p /iridisfs/ddnb/affinity/experiments/pose2-vae-experiment/results/
# change the working directory to the correct experiment results directory
cd /iridisfs/ddnb/affinity/experiments/pose2-vae-experiment/results/
# print the working directory
echo working directory set to: `pwd`


# Define arrays for the parameters
limits=(20000)                         # values for --limit
betas=(0.005)                                     # values for --beta
depths=(4)                                    # values for --depth
channels=(1024)                        # values for --channels
latent_dims=(32)                 # values for --latent_dims
pose_dims=(1 2 3 4 8)       # values for --pose_dims
lrs=(0.00025)                          # values for --learning
batch=(256)                                       # values for --batch
epochs=(120)                                      # values for --epochs
gamma=(0.002 0.004 0.006 0.008 0.01)    # values for --affinity



# Print the number of jobs to be submitted
echo "Number of jobs to be submitted: $((${#betas[@]} * ${#depths[@]} * ${#channels[@]} * ${#latent_dims[@]} * ${#pose_dims[@]} * ${#limits[@]} * ${#batch[@]} * ${#epochs[@]} * ${#lrs[@]} * ${#gamma[@]}))"


# Iterate through the combinations of parameters
for beta in "${betas[@]}"; do
    for depth in "${depths[@]}"; do
        for channel in "${channels[@]}"; do
            for latent_dim in "${latent_dims[@]}"; do
                for pose_dim in "${pose_dims[@]}"; do
                    for limit in "${limits[@]}"; do
                        for b in "${batch[@]}"; do
                            for epoch in "${epochs[@]}"; do
                                for lr in "${lrs[@]}"; do
                                    for aff in "${gamma[@]}"; do
                                    # Construct a unique job name for each combination
                                    job_name="avae_b_${beta}_dep_${depth}_chan_${channel}_lat_${latent_dim}_pose_${pose_dim}_lim_${limit}_batch_${b}_ep_${epoch}_lr_${lr}_aff_${aff}"
                                    
                                    # Submit the job with the current combination of parameters
                                    sbatch <<- EOF
#!/bin/bash
#SBATCH --job-name=${job_name}
#SBATCH --partition=scavenger_l4
#SBATCH --nodes=1
#SBATCH --gres=gpu:1 
#SBATCH --ntasks=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --mail-type=NONE
#SBATCH --mail-user=mtn1n22@soton.ac.uk
#SBATCH --output=/iridisfs/ddnb/affinity/experiments/pose2-vae-experiment/slurm_outputs/run/%j.out

source /iridisfs/ixsoftware/conda/miniconda-py3/etc/profile.d/conda.sh
source activate affinity

# print the conda active environment
echo "conda environment \" "$CONDA_DEFAULT_ENV" \" is active."

# print starting message
echo "Starting affinity-vae-omics script with parameters: beta=${beta}, depth=${depth}, channels=${channel}, latent_dims=${latent_dim}, pose_dims=${pose_dim}, limit=${limit}, batch=${b}, epochs=${epoch}, lr=${lr}, gamma=${aff}...."

# run the affinity-vae-omics script.
python /iridisfs/ddnb/affinity/affinity-vae-omics/run.py \
    --config_file /home/mtn1n22/affinity/experiments/pose2-vae-experiment/config.yml \
    --datafile /home/mtn1n22/affinity/experiments/pose2-vae-experiment/data/ScaleBioPBMC_qc.h5ad \
    --affinity /iridisfs/ddnb/affinity/experiments/pose2-vae-experiment/affinity_tf_scaled.csv \
    --new_out \
    --beta ${beta} \
    --depth ${depth} \
    --channels ${channel} \
    --latent_dims ${latent_dim} \
    --pose_dims ${pose_dim} \
    --limit ${limit} \
    --batch ${b} \
    --epochs ${epoch} \
    --learning ${lr} \
    --gamma ${aff} \
    --gpu
EOF
                                    done
                                done
                            done
                        done
                    done
                done
            done
        done
    done
done