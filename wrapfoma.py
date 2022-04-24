import shutil, subprocess, os, sys

foma_path = shutil.which('foma')
if foma_path is None:
	raise Exception("No foma found")

def run_batch(foma_input, test_cases):
	queries = "\n".join(test_cases)
	r, w = os.pipe()
	os.write(w, foma_input.encode('utf8'))
	os.close(w)

	with subprocess.Popen([foma_path, '-p'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, pass_fds=[r]) as proc:
		stdout, _ = proc.communicate('source /dev/fd/'+str(r)+'\necho --READY--\ndown\n' + queries + "\nEND;\nexit\n", 0.5)
		lines = stdout.split('\n')[-2-(len(test_cases)*2):-3:2]

	return lines

def try_option(rules):
	foma_input = '\n'.join((*before, *rules, *after))
	answers = run_batch(foma_input, queries)

	wrong = 0
	for i in range(len(queries)):
		if correct[i] != answers[i]:
			wrong += 1

	return wrong

def do_compute(x):
	return (try_option(x), x)

if __name__ != '__main__':
	sys.exit()

json_file_name = 'dataset_finnish.json'
foma_file_name = 'finnish.metafoma'
if len(sys.argv) == 2:
    if sys.argv[1] == "-h":
        print(f"usage: python {sys.argv[0]} (json_test_data_filename) (metafoma_filename)")
if len(sys.argv) >= 3:
	json_file_name = sys.argv[1]
	foma_file_name = sys.argv[2]

import json
with open(json_file_name, 'r') as fd:
	data = json.load(fd)

queries = list(data.keys())
correct = list(data.values())

with open(foma_file_name, 'r') as fd:
	contents = fd.read().split('\n')

p_start = contents.index('#%%METAFOMA begin permute rules%%#')
p_end = contents.index('#%%METAFOMA end permute rules%%#')

before = tuple(contents[:p_start])
after = tuple(contents[p_end+1:])
rules = contents[p_start+1:p_end]

import random, itertools, math

random.shuffle(rules)

allpossible = list(itertools.permutations(rules, len(rules)))

print(f"Searching for an optimal feed/bleed order amongst {len(rules)} rules ({len(allpossible)} orderings)")

param_nproc = 12
param_population_size = param_nproc * 8
param_duplicate_best = 8
param_mutation_count = param_population_size

population = [list(rules) for _ in range(param_population_size)]
for x in population:
	random.shuffle(x)

import multiprocessing

generation = 0

pool = multiprocessing.Pool(param_nproc)

while True:
	scored = list(pool.imap_unordered(do_compute, population, int(param_population_size/param_nproc)))
	scored.sort(key = lambda x: x[0])
	best = scored[0]

	if best[0] == 0:
		print("Success! Ordering:")
		print("\n".join(" > " + x for x in best[1]))
		break

	rest = scored[1:]

	print(f"Generation {generation:3}: best score {best[0]}")
	# print(f"Scores: {[x[0] for x in scored]}")
	generation += 1

	for _ in range(param_duplicate_best):
		rest.insert(0, [best[0], list(best[1])])

	rest = rest[:param_population_size]

	for item in rest:
		if item[0] == len(queries):
			# Has nothing going for it, shuffle
			random.shuffle(item[1])

	for _ in range(param_mutation_count):
		victim = random.choice(rest)[1]
		shuf_a = random.randint(0, len(victim) - 1)
		shuf_b = random.randint(0, len(victim) - 1)
		if shuf_a == shuf_b:
			continue
		temp = victim[shuf_a]
		victim[shuf_a] = victim[shuf_b]
		victim[shuf_b] = temp

	population = [best[1]] + [x[1] for x in rest]


# Interesting thing to do: try all permutations, find which relative ordering constraints
# actually matter and which don't, e.g. in finnish case.
