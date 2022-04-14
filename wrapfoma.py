import shutil, subprocess, os

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

import json
with open('dataset_finnish.json', 'r') as fd:
	data = json.load(fd)

queries = list(data.keys())
correct = list(data.values())

with open('finnish.metafoma', 'r') as fd:
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

def try_option(rules):
	foma_input = '\n'.join(before + rules + after)
	answers = run_batch(foma_input, queries)

	ok = True
	for i, query in enumerate(queries):
		if correct[i] != answers[i]:
			# print(f"Item {query:15} wrong: should be {correct[i]:10}, was {answers[i]:10}")
			ok = False

	if ok:
		print("Success! Ordering:")
		print("\n".join(" > " + x for x in rules))

from multiprocessing import Pool
with Pool() as p:
	res = list(p.imap_unordered(try_option, allpossible))
