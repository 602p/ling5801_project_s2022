import sys, json
from foma import score_foma_code

def do_compute(x):
	return (score_foma_code('\n'.join(i.get_text() for i in x), queries, correct), x)

def do_permute(args, parts, aux):
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

class LiteralChunk:
	def __init__(self, lineno, lines):
		self.lineno = lineno
		self.linecount = len(lines)
		self.text = '\n'.join(x.split('#')[0].strip() for x in lines)

	def permute(self):
		pass

	def get_text(self):
		return self.text

	def copy(self):
		return self

class PermuteLinesChunk:
	def __init__(self, lineno, args, lines):
		self.lineno = lineno
		self.lines = lines
		self.args = args

	def permute(self):
		do_permute(self.args, self.lines, self.lines)

	def get_text(self):
		return '\n'.join(self.lines)

	def copy(self):
		return PermuteLinesChunk(self.lineno, self.args, self.lines[:])

	def __str__(self):
		return f"lines({', '.join(self.args)}) of {len(self.lines)} lines at line {self.lineno}"

class PermuteExprsChunk:
	def __init__(self, lineno, args, lines, direct_exprs=None, direct_original=None):
		self.lineno = lineno

		if not direct_exprs:
			lines = " ".join(lines).replace('\t', ' ')
			exprs = [x.strip() for x in lines.split(' ') if x.strip()]
			self.exprs = exprs
			self.original = tuple(exprs)
		else:
			self.exprs = direct_exprs
			self.original = direct_original

		self.args = args

	def permute(self):
		do_permute(self.args, self.exprs, self.original)

	def get_text(self):
		return ' '.join(self.exprs)

	def copy(self):
		return PermuteExprsChunk(self.lineno, self.args, None,
			direct_exprs=self.exprs[:], direct_original=self.original)

	def __str__(self):
		return f"exprs({', '.join(self.args)}) of {len(self.exprs)} exprs at line {self.lineno}"

foma_file_name = 'finnish.metafoma3'

if '-h' in sys.argv:
    print(f"usage: python {sys.argv[0]} <metafoma_filename>")
    sys.exit()

with open(foma_file_name, 'r') as fd:
	contents = fd.read().split('\n')

queries = []
correct = []

template = []
current = []
reading_normal = True
lineno = 1

for line in contents:
	if line.startswith("#%%"):
		line = line[3:].strip()

		if line.strip() == "}":
			reading_normal = True
			constructor = PermuteExprsChunk if operator=='exprs' else PermuteLinesChunk
			template.append(constructor(lineno - len(current), tuple(args), current))
			current = []
		else:
			action, line = line.strip().split(' ', 1)
			line = line.strip()
			operator, line = line.split('(', 1)
			line = line.strip()
			args, line = line.split(')', 1)
			args = [x.strip() for x in args.split(',')]

			if action == 'permute':
				assert line.strip() == "{"
				reading_normal = False
				template.append(LiteralChunk(lineno - len(current), current))
				current = []
			elif action == 'test':
				with open(args[0], 'r') as fd:
					data = json.load(fd)

				queries.extend(data.keys())
				correct.extend(data.values())

				print(f" * Found test file({args[0]}) at line {lineno} and loaded {len(data.keys())} tests")
	else:
		current.append(line)
	lineno += 1

assert reading_normal
template.append(LiteralChunk(lineno - len(current), current))

literals = []
for item in template:
	if type(item) == LiteralChunk:
		literals.append(item)
	else:
		print(f" * Found permute {item}")

print(f" * Also found {len(literals)} literals of {sum(item.linecount for item in literals)} lines (total)")

# print('\n'.join(map(repr, template)))

import random, itertools, math, multiprocessing

param_nproc = multiprocessing.cpu_count() * 2
param_population_size = param_nproc * 24
param_duplicate_best = 8
param_mutation_count = param_population_size

def copytemplate(t):
	return [x.copy() for x in t]

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

	print(f" o Generation {generation:3}: best score is {best[0][0]:2} wrong ({best[0][1]:2} Levenshtein; {best[0][2]:4} chars)")

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
			if type(item) != LiteralChunk:
				break
		item.permute()

	population = [best[1]] + [x[1] for x in rest]

print()
print(" # Success!")
for item in best[1]:
	if type(item) != LiteralChunk:
		print(f" * Solved permute {item}: ")
		if type(item) == PermuteLinesChunk:
			for line in item.lines:
				print("\t" + line.strip())
		else:
			print("\t" + " ".join(item.exprs))
