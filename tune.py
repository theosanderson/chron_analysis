
argument = 0.5
filename = f"metadata_subset_{argument}.tsv"

import os
for vd in [0.1,0.3,0.9]:
    if vd == 0.1:
        continue
    for vb in [0.5,1,2]:
        if vd == 0.3 and vb!=2:
            continue
        command = f"chronumental --tree  public-2021-09-15.all.nwk.gz --dates {filename} --steps 2000 --dates_out tune_{vb}_{vd}.out.tsv --tree_out tune_{vb}_{vd}.out.nwk -variance_dates {vd} -variance_branch_length {vb}"
        os.system(command)
