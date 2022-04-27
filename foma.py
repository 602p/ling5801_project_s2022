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

def score_foma_code(foma_input, queries, correct):
	answers = run_batch(foma_input, queries)

	wrong = 0
	wrong_lev = 0
	for i in range(len(queries)):
		l = lev(correct[i], answers[i])
		if l != 0:
			wrong += 1
			wrong_lev += l

	return (wrong, wrong_lev, len(foma_input))
