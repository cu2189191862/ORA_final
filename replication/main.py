import numpy as np
from datetime import datetime
from model import Model

output_path = "./solution.txt"
replications = 1


with open(output_path, 'a') as f:
    f.write("{}\n".format(str(datetime.now())))

for r in range(replications):
    np.random.seed(r)

    with open(output_path, 'a') as f:
        f.write("r: {}\n".format(r))

    model = Model()
    model.optimize()
    # model.log_params()
    # model.log_sol()
    model.dump_results(output_path=output_path)
    with open(output_path, 'a') as f:
        f.write("----------------------------\n")

with open(output_path, 'a') as f:
    f.write("====================================\n")