import shutil, subprocess, os, sys
from Levenshtein import distance as lev

foma_path = shutil.which('foma')
if foma_path is None:
	raise Exception("No foma found")

def run_batch(foma_input, test_cases):
	queries = "\n".join(test_cases)
	r, w = os.pipe()
	os.write(w, foma_input.encode('utf8'))
	os.close(w)

	with subprocess.Popen([foma_path, '-p'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, pass_fds=[r]) as proc:
		stdout, _ = proc.communicate('source /dev/fd/'+str(r)+'\necho --READY--\ndown\n' + queries + "\nEND;\nexit\n", 1)
		lines = stdout.split('\n')[-2-(len(test_cases)*2):-3:2]

	os.close(r)

	return lines

def try_option(rules):
	foma_input = '\n'.join('\n'.join(x[-2]) for x in rules)
	answers = run_batch(foma_input, queries)

	wrong = 0
	wrong_lev = 0
	for i in range(len(queries)):
		l = lev(correct[i], answers[i])
		if l != 0:
			wrong += 1
			wrong_lev += l

	return (wrong, wrong_lev, len(foma_input))

def do_compute(x):
	return (try_option(x), x)

if __name__ != '__main__':
	sys.exit()

json_file_name = 'dataset_finnish.json'
foma_file_name = 'finnish.metafoma2'

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

template = []

current = []

reading_normal = True

lineno = 1

for line in contents:
	if line.startswith("#%%"):
		line = line[3:].strip()

		if line.strip() == "}":
			reading_normal = True
			template.append([lineno - len(current), operator, tuple(args), current])
			current = []
		else:
			_, line = line.split('permute')
			line = line.strip()
			operator, line = line.split('(', 1)
			line = line.strip()
			args, line = line.split(')', 1)
			args = [x.strip() for x in args.split(',')]
			assert line.strip() == "{"

			# print("Metafoma line: operator=", repr(operator), "args=", repr(args))
			reading_normal = False
			template.append([lineno - len(current), 'literal', (), current])
			current = []
	else:
		current.append(line)
	lineno += 1

assert reading_normal
template.append([lineno - len(current), 'literal', (), current])

def prepare_exprs(args, lines):
	lines = " ".join(lines).replace('\t', ' ')
	exprs = [x.strip() for x in lines.split(' ') if x.strip()]
	return exprs, exprs

def permute(args, parts, aux):
	while True:
		act = random.choice(args)
		if act == 'kleene':
			while True:
				item = random.randint(0, len(parts) - 1)
				fragment = parts[item]
				stripped = fragment.strip('*+')
				if stripped.isalpha() or stripped == '?':
					already = "" if stripped == fragment else fragment[-1]
					new = ["", "*", "+"]
					new.remove(already)
					parts[item] = stripped + random.choice(new)
					return
		elif act == 'presence':
			if random.choice((0, 1)):
				if len(parts) > 1:
					parts.remove(random.choice(parts))
					return
			else:
				if len(parts) < len(aux):
					parts.insert(random.randint(0, len(parts)-1), random.choice(aux))
					return
		elif act == 'order':
			shuf_a = random.randint(0, len(parts) - 1)
			shuf_b = random.randint(0, len(parts) - 1)
			if shuf_a == shuf_b:
				return
			temp = parts[shuf_a]
			parts[shuf_a] = parts[shuf_b]
			parts[shuf_b] = temp

def prepare_lines(args, lines):
	return lines, []

def prepare_literal(args, lines):
	return lines, []

for item in template:
	item[3:4] = eval('prepare_' + item[1])(item[2], item[3])

literals = []
for item in template:
	if item[1] == 'literal':
		literals.append(item)
	else:
		print(f" * Found {item[1]}({', '.join(item[2])}) of {len(item[3])} {item[1]} at line {item[0]}")

print(f" * Also found {len(literals)} literals of {sum(len(item[3]) for item in literals)} lines (total)")

# print('\n'.join(map(repr, template)))

import random, itertools, math, multiprocessing

param_nproc = multiprocessing.cpu_count() * 2
param_population_size = param_nproc * 24
param_duplicate_best = 8
param_mutation_count = param_population_size

def copytemplate(t):
	new = []
	for item in t:
		new.append((*item[:-2], list(item[-2]), item[-1]))
	return new

population = [copytemplate(template) for _ in range(param_population_size)]

generation = 0

pool = multiprocessing.Pool(param_nproc)

print(f" # Searching with {param_nproc} tasks ({multiprocessing.cpu_count()} cores) and a population size of {param_population_size}")
print()

while True:
	scored = list(pool.imap_unordered(do_compute, population, int(param_population_size/param_nproc)))
	scored.sort(key = lambda x: x[0])
	best = scored[0]

	if best[0][0] == 0:
		break

	rest = scored[1:]

	print(f" o Generation {generation:3}: best score is {best[0][0]:2} wrong ({best[0][1]:2} Levenshtein; {best[0][2]:4} chars foma)")

	if '--debug' in sys.argv:
		for item in best[1]:
			if item[1] != 'literal':
				print(f"   d {item[1]}({', '.join(item[2])})@{item[0]}: {' '.join(x.strip() for x in item[3])}")

	generation += 1

	for _ in range(param_duplicate_best):
		rest.insert(0, [best[0], copytemplate(best[1])])

	rest = rest[:param_population_size]

	for item in rest:
		if item[0] == len(queries):
			# Has nothing going for it, shuffle
			item[1] = copytemplate(template)

	for _ in range(param_mutation_count):
		victim = random.choice(rest)[1]
		while True:
			item = random.choice(victim)
			if item[1] != 'literal':
				break
		permute(item[2], item[3], item[4])

	population = [best[1]] + [x[1] for x in rest]

print()
print(" # Success!")
for item in best[1]:
	if item[1] != 'literal':
		print(f" * Solved {item[1]}({', '.join(item[2])}) of {len(item[3])} {item[1]} at line {item[0]}: ")
		if item[1] == 'lines':
			for line in item[3]:
				print("\t" + line.strip())
		else:
			print("\t" + " ".join(item[3]))
