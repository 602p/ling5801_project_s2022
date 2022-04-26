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

	print(stdout, lines)

	return lines

def try_option(rules):
	foma_input = '\n'.join((*before, *rules, *after))
	answers = run_batch(foma_input, queries)

	wrong = 0
	for i in range(len(queries)):
		if correct[i] != answers[i]:
			print("Q:", queries[i], "C:", correct[i], "A:", answers[i])
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

print(do_compute(rules)[0])
