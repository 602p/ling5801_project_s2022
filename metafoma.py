import sys, json
from foma import score_foma_code

def do_compute(x):
	return (score_foma_code('\n'.join(i.get_text() for i in x), queries, correct), x)

def do_permute(args, parts, options):
	while True:
		act = random.choice(args)
		if act == 'kleene' and parts:
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
			if random.choice((0, 1)) and len(parts) > options['minlen']:
				parts.remove(random.choice(parts))
				return
			elif len(parts) < options['maxlen']:
				parts.insert(random.randint(0, max(0, len(parts)-1)), random.choice(options['choices']))
				return
		elif act == 'order' and parts:
			shuf_a = random.randint(0, len(parts) - 1)
			shuf_b = random.randint(0, len(parts) - 1)
			if shuf_a != shuf_b:
				temp = parts[shuf_a]
				parts[shuf_a] = parts[shuf_b]
				parts[shuf_b] = temp
				return

def fixup_optargs(items, optargs):
	v = optargs.get('choices', ' '.join(items))
	optargs['choices'] = [x for x in v.split(' ') if x]

	v = optargs.get('minlen', 1)
	optargs['minlen'] = int(v)

	v = optargs.get('maxlen', len(items))
	optargs['maxlen'] = int(v)

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
	def __init__(self, lineno, args, optargs, lines):
		self.lineno = lineno
		self.lines = lines
		self.args = args
		self.optargs = optargs

	def permute(self):
		do_permute(self.args, self.lines, self.optargs)

	def get_text(self):
		return '\n'.join(self.lines)

	def copy(self):
		return PermuteLinesChunk(self.lineno, self.args, self.optargs, self.lines[:])

	def shortstr(self):
		return f"lines({', '.join(self.args)})"

	def dbgstate(self):
		return ' \\n '.join(x.strip() for x in self.lines)

	def __str__(self):
		return f"{self.shortstr()} of {len(self.lines)} lines at line {self.lineno}"

class PermuteExprsChunk:
	def __init__(self, lineno, args, optargs, lines, direct_exprs=None, direct_original=None):
		self.lineno = lineno

		if direct_exprs is None:
			lines = " ".join(lines).replace('\t', ' ')
			exprs = [x.strip() for x in lines.split(' ') if x.strip()]
			self.exprs = exprs
			self.original = tuple(exprs)
		else:
			self.exprs = direct_exprs
			self.original = direct_original

		self.args = args
		self.optargs = optargs

	def permute(self):
		do_permute(self.args, self.exprs, self.optargs)

	def get_text(self):
		return ' '.join(self.exprs)

	def shortstr(self):
		return f"exprs({', '.join(self.args)})"

	def dbgstate(self):
		return ' '.join(self.exprs)

	def copy(self):
		return PermuteExprsChunk(self.lineno, self.args, self.optargs, None,
			direct_exprs=self.exprs[:], direct_original=self.original)

	def __str__(self):
		return f"{self.shortstr()} of {len(self.exprs)} exprs at line {self.lineno}"

foma_file_name = 'finnish.metafoma3'

if '-h' in sys.argv:
    print(f"usage: python {sys.argv[0]} <metafoma_filename>")
    sys.exit()

for i in sys.argv[1:]:
	if not i.startswith('--'):
		foma_file_name = i

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
			fixup_optargs(current, optargs)
			template.append(constructor(lineno - len(current), tuple(args), optargs, current))
			current = []
		else:
			action, line = line.strip().split(' ', 1)
			line = line.strip()
			operator, line = line.split('(', 1)
			line = line.strip()
			args, line = line.split(')', 1)
			args = [x.strip() for x in args.split(',')]

			optargs = {}

			if line and line[0] == '[':
				options, line = line[1:].split(']', 1)
				stanzas = [x.strip() for x in options.split(',')]
				for item in stanzas:
					k, v = item.split('=', 1)
					optargs[k] = v

			if action == 'permute':
				assert line.strip() == '{'
				reading_normal = False
			elif action == 'test':
				with open(args[0], 'r') as fd:
					data = json.load(fd)

				queries.extend(data.keys())
				correct.extend(data.values())

				print(f" * Found test file({args[0]}) at line {lineno} and loaded {len(data.keys())} tests")

			template.append(LiteralChunk(lineno - len(current), current))
			current = []
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
param_mutation_count = param_population_size * 1.5

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

	print(f" o Generation {generation:3}: best score is {best[0][0]:2} wrong ({best[0][1]:2} Levenshtein; {best[0][2]:4} chars)")

	if best[0][0] == 0:
		break

	rest = scored[1:]

	if '--debug' in sys.argv:
		for item in best[1]:
			if type(item) != LiteralChunk:
				print(f"   d {item.shortstr()}@{item.lineno}: {item.dbgstate()}")

	generation += 1

	for _ in range(param_duplicate_best):
		rest.insert(0, [best[0], copytemplate(best[1])])

	rest = rest[:param_population_size]

	for item in rest:
		if item[0] == len(queries):
			# Has nothing going for it, shuffle
			item[1] = copytemplate(template)

	for _ in range(int(param_mutation_count)):
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
