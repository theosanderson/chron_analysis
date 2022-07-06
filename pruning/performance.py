import os
import pandas as pd
import tqdm
import time
import subprocess
import argparse
#create an argparser to get a single argument called mode
#mode can be either "treetime" or "chronumental"

parser = argparse.ArgumentParser(description='Get perf')
parser.add_argument('--mode',
                    type=str,
                    default='treetime',
                    help='Mode to run in. Can be treetime or chronumental',
                    choices=['treetime', 'chronumental'])

parser.add_argument('--gpu', action='store_true', help='Use GPU')

args = parser.parse_args()

output_file = open(
    f"performance{'' if args.mode=='treetime' else '_chron'}{'' if not args.gpu else '_gpu'}.tsv",
    "wt")
output_file.write("num_tips\ttime\tmemory\n")

number_of_tips = [3**x for x in range(4, 40)]

metadata = pd.read_csv("../public-2021-09-15.metadata.tsv.gz", sep="\t")


def run_process_and_return_stderr_and_stdout(command):
    """
    Run a command and return stdout and stderr.
    """
    print(command)
    process = subprocess.run(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True,
                             shell=True)
    return process.stdout, process.stderr


def run_command_and_get_time_and_memory_usage(command):
    """
    We use /usr/bin/time to get this. Need to use stderr.
    """
    start_time = time.time()

    stdout, stderr = run_process_and_return_stderr_and_stdout(
        ("/usr/bin/time -f %M " + command + ""))

    print(stdout)
    print(stderr)
    print(command)
    # extract memory usage, which is maximum resident set size
    lines = stderr.split("\n")
    #get last line
    mem = lines[-2]
    print(f"Got memory {mem}")

    end_time = time.time()
    return end_time - start_time, mem


def main():
    for num_tips in tqdm.tqdm(number_of_tips):
        os.system(
            f"zcat ../public-2021-09-15.all.nwk.gz | gotree prune --random {num_tips} --revert > working/tree.{num_tips}.nwk"
        )
        os.system(
            f"cat working/tree.{num_tips}.nwk | gotree labels --tips > working/tips.{num_tips}.txt"
        )

        # scale branch lengths down by 30000 times to per-site
        scale_factor = 1 / 30_000
        os.system(
            f"cat working/tree.{num_tips}.nwk| gotree brlen scale --factor {scale_factor} > working/tree_scaled.{num_tips}.nwk"
        )

        tip_names = open(f"working/tips.{num_tips}.txt").read().splitlines()

        # Create metadata filtered to strain in tip_names
        filtered_metadata = metadata[metadata['strain'].isin(tip_names)]
        filtered_metadata.to_csv(f"working/metadata.{num_tips}.tsv",
                                 sep="\t",
                                 index=False)

        #Time the treetime call:
        start_time = time.time()
        if args.mode == 'treetime':
            command = f"treetime --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --sequence-length 30000  --keep-root --outdir ./working/"
        elif args.gpu:
            command = f"chronumental --treat_mutation_units_as_normalised_to_genome_size 30000 --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --tree_out /dev/null --dates_out /dev/null --use_gpu --steps 1000"
        else:
            command = f"chronumental --treat_mutation_units_as_normalised_to_genome_size 30000 --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --tree_out /dev/null --dates_out /dev/null --steps 1000"
        timing, mem = run_command_and_get_time_and_memory_usage(command)
        output_file.write(f"{num_tips}\t{timing}\t{mem}\n")
        output_file.flush()


if __name__ == "__main__":
    main()
