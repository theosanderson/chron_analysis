import os
import pandas as pd
import tqdm
import time
import subprocess
import argparse
import datetime as dt
#create an argparser to get a single argument called mode
#mode can be either "treetime" or "chronumental"

parser = argparse.ArgumentParser(description='Get perf')
parser.add_argument('--mode',
                    type=str,
                    default='treetime',
                    help='Mode to run in. Can be treetime or chronumental',
                    choices=['treetime', 'chronumental', 'lsd'])

parser.add_argument('--gpu', action='store_true', help='Use GPU')

parser.add_argument('--lsdF', action='store_true', help='Disable temporal constraints')

args = parser.parse_args()

output_file = open(
    f"performance_{args.mode}_{'nogpu' if not args.gpu else '_gpu'}{'_F' if args.lsdF else ''}.tsv",
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

def dateToFloatYear(string):
    """
    Convert a date string to a float year.
    2021-09-15 -> 2021.7
    """
    string = string.strip()
    node, dates = string.split("\t")
    #print(string)
    try: 
        date = dt.datetime.strptime(dates, "%Y-%m-%d")
        return node + "\t" + f"{date.year + (date.timetuple().tm_yday - 1) / 365.25}\n"
    except ValueError as e:
        print(f"Could not parse date {dates} - {e}")
        return None


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

        # open the newick file and add an outgroup called "out"
        with open(f"working/tree_scaled.{num_tips}.nwk", "rt") as f:
            tree = f.read()
            # remove last semi-colon
            tree = tree[:-1]
        with open(f"working/tree_scaled.{num_tips}.nwk", "wt") as f:
            rooted_tree = f"{tree}:0.0, out:0.0;"
            f.write(rooted_tree)

        tip_names = open(f"working/tips.{num_tips}.txt").read().splitlines()

        # Create metadata filtered to strain in tip_names
        filtered_metadata = metadata[metadata['strain'].isin(tip_names)]
        filtered_metadata = filtered_metadata[['strain', 'date']]
        # filter out date "?"
        filtered_metadata = filtered_metadata[filtered_metadata['date'] != "?"]

        # 
        filtered_metadata.to_csv(f"working/metadata.{num_tips}.tsv",
                                 sep="\t",
                                 index=False)

        # if mode is "lsd" then add the metadata num rows as the first line
        if args.mode == 'lsd':
            f = open(f"working/metadata.{num_tips}.tsv", "rt")
            lines = f.readlines()
            f.close()
            f = open(f"working/metadata.{num_tips}.tsv", "wt")
            
            # remove the first line
            lines = lines[1:]
            #lines = [dateToFloatYear(x) for x in lines]
            lines = [x  for x in lines if x is not None]
            f.write(f"{len(lines)}\n")

            f.writelines(lines)
            f.close()

        #Time the treetime call:
        start_time = time.time()
        if args.mode == 'treetime':
            command = f"treetime --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --sequence-length 30000  --keep-root --outdir ./working/"
        elif args.mode == 'lsd':
            command = f"lsd2 -i working/tree_scaled.{num_tips}.nwk -d working/metadata.{num_tips}.tsv -s 30000 -g outgroup_file -G {'-F' if args.lsdF else ''}"
        elif args.gpu:
            command = f"chronumental --treat_mutation_units_as_normalised_to_genome_size 30000 --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --tree_out /dev/null --dates_out /dev/null --use_gpu --steps 1000"
        else:
            command = f"chronumental --treat_mutation_units_as_normalised_to_genome_size 30000 --dates working/metadata.{num_tips}.tsv --tree working/tree_scaled.{num_tips}.nwk --tree_out /dev/null --dates_out /dev/null --steps 1000"
        timing, mem = run_command_and_get_time_and_memory_usage(command)
        output_file.write(f"{num_tips}\t{timing}\t{mem}\n")
        output_file.flush()


if __name__ == "__main__":
    main()
