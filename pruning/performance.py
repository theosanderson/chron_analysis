import os
import pandas as pd
import tqdm
import time

output_file = open("performance.tsv", "wt")

number_of_tips = [4**x for x in range(2, 12)]

metadata = pd.read_csv("../public-2021-09-15.metadata.tsv.gz", sep="\t")

for num_tips in tqdm.tqdm(number_of_tips):
    os.system(
        f"gzcat ../public-2021-09-15.all.nwk.gz | gotree prune --random {num_tips} --revert > tree.{num_tips}.nwk"
    )
    os.system(
        f"cat tree.{num_tips}.nwk | gotree labels --tips > tips.{num_tips}.txt"
    )

    # scale branch lengths down by 30000 times to per-site
    scale_factor = 1 / 30_000
    os.system(
        f"cat tree.{num_tips}.nwk| gotree brlen scale --factor {scale_factor} > tree_scaled.{num_tips}.nwk"
    )

    tip_names = open(f"tips.{num_tips}.txt").read().splitlines()

    # Create metadata filtered to strain in tip_names
    filtered_metadata = metadata[metadata['strain'].isin(tip_names)]
    filtered_metadata.to_csv(f"metadata.{num_tips}.tsv", sep="\t", index=False)

    #Time the treetime call:
    start_time = time.time()
    command = f"treetime clock --dates metadata.{num_tips}.tsv --tree tree_scaled.{num_tips}.nwk --sequence-length 30000  --keep-root"
    os.system(command)
    print(command)
    end_time = time.time()
    output_file.write(f"{num_tips}\t{end_time-start_time}\n")
    output_file.flush()
