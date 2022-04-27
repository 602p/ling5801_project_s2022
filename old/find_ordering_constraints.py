import shutil, subprocess, os, sys

foma_path = shutil.which('foma')
if foma_path is None:
	raise Exception("No foma found")

def run_batch(foma_input, test_cases):
	queries = "\n".join(test_cases)
	r, w = os.pipe()
	os.write(w, foma_input.encode('utf8'))
	os.close(w)

	with subprocess.Popen([foma_path, '-p'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, pass_fds=[r]) as proc:
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
        sys.exit()

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

import multiprocessing

param_nproc = 16

pool = multiprocessing.Pool(param_nproc)

scored = list(pool.imap_unordered(do_compute, allpossible, int(len(allpossible)/param_nproc)))
print(len(scored), len([x for x in scored if x[0] == 0]))

# scored = [(0, ('         .o. RealizePartMarker', '         .o. VowelLowering', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. RealizePartMarker', '         .o. VowelLowering', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. RealizePartMarker', '         .o. VowelShortening', '         .o. VowelLowering', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelLowering', '         .o. RealizePartMarker', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelLowering', '         .o. VowelShortening', '         .o. RealizePartMarker', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePartMarker', '         .o. VowelLowering', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. VowelLowering', '         .o. RealizePartMarker', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelLowering', '         .o. VowelRounding', '         .o. RealizePartMarker', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelLowering', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePartMarker', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelLowering', '         .o. VowelDropping', '         .o. RealizePartMarker', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. RealizePartMarker', '         .o. VowelLowering', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. RealizePartMarker', '         .o. VowelRounding', '         .o. VowelLowering', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. RealizePartMarker', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. VowelLowering', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelDropping', '         .o. VowelLowering', '         .o. RealizePartMarker', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. RealizePartMarker', '         .o. VowelDropping', '         .o. VowelLowering', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. RealizePartMarker', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelLowering', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. RealizePartMarker', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. VowelLowering', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelLowering', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. RealizePartMarker', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelLowering', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePartMarker', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries')), (0, ('         .o. VowelLowering', '         .o. RealizePartMarker', '         .o. VowelDropping', '         .o. VowelRounding', '         .o. VowelShortening', '         .o. RealizePluralMarker', '         .o. DeleteBoundaries'))]
valid_orderings = [[i.split(' ')[-1] for i in x[1]] for x in scored if x[0]==0]

possible_orderings = []
for rule in rules:
	for other in rules:
		if rule != other:
			possible_orderings.append((rule.split(' ')[-1], other.split(' ')[-1])) # rule BEFORE other

for valid in valid_orderings:
	invalidated = []
	for possible_ordering in possible_orderings:
		if valid.index(possible_ordering[0]) > valid.index(possible_ordering[1]):
			invalidated.append(possible_ordering)
	for i in invalidated:
		possible_orderings.remove(i)

print("\n".join(map(str, sorted(possible_orderings))))

with open('constraints.dot', 'w') as fd:
	fd.write("digraph {\n")
	for item in possible_orderings:
		fd.write(item[0] + " -> " + item[1] + ";\n")
	fd.write("}\n")


# Interesting thing to do: try all permutations, find which relative ordering constraints
# actually matter and which don't, e.g. in finnish case.
