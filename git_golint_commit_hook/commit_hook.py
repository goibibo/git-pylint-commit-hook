""" commit hook for golint """
import decimal
import os
import re
import sys
import subprocess
import collections
import ConfigParser


ExecutionResult = collections.namedtuple(
    'ExecutionResult',
    'status, stdout, stderr'
)


def _execute(cmd):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    status = process.poll()
    return ExecutionResult(status, stdout, stderr)


def _current_commit():
    if _execute('git rev-parse --verify HEAD'.split()).status:
        return '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
    else:
        return 'HEAD'


def _get_list_of_committed_go_files():
    """ Returns a list of files about to be commited. """
    files = []
    diff_index_cmd = 'git diff-index --cached %s' % _current_commit()
    output = subprocess.check_output(
        diff_index_cmd.split()
    )
    for result in output.split('\n'):
        if result != '':
            result = result.split()
            if result[4] in ['A', 'M']:
                if _is_go_file(result[5]):
                    files.append((result[5],None)) #None is initial score

    return files

def _get_user():
    """
    Returns user
    """
    get_user_cmd = "git var GIT_AUTHOR_IDENT "
    user = subprocess.check_output(
        get_user_cmd.split()
    )
    return user.split()[0]

def _is_go_file(filename):
    """Check if the input file looks like a Golang file.

    Returns True if the filename ends in ".go", False otherwise.
    """
    if filename.endswith('.go'):
        return True
    else:
        return False

def computeGoScore(warnings,totallines):
    """ Computes the score of a go file, 
        given golint's output and total number of lines in a go file.
    """
    maxScore = 10.0
    currentScore = (float(warnings) / float(totallines)) * maxScore
    currentScore = maxScore - currentScore
    return currentScore

def getNumberOfLines(file_n):
    """ Returns total number of lines in a file. """
    totalLines = 0
    with open(file_n) as gofile:
        for line in gofile:
                if line.strip():
                        totalLines += 1
    return totalLines

def runGolint(file_n,golint):
    """ Runs golint on a file, and returns its score. """
    totalLines = getNumberOfLines(file_n)
    try:
        command = [golint]
        penv = os.environ.copy()
        command.append(file_n)
        proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=penv)
        outp, _ = proc.communicate()
        warnings = 0
        for line in outp:
                if line=='\n':
                        warnings += 1
    except OSError:
            print("\nAn error occurred. Is golint installed?")
            sys.exit(1)
    score = computeGoScore(warnings,totalLines)
    return score

def check_repo(
        limit, golint='golint', datfile="/tmp/git.dat", scorefile="/tmp/scores.dat"):
    """ Main function doing the checks

    :type limit: float
    :param limit: Minimum score to pass the commit
    :type golint: str
    :param golint: Path to golint executable
    :type suppress_report: bool
    :param suppress_report: Suppress report if score is below limit
    """
    # List of checked files and their results
    go_files = _get_list_of_committed_go_files()

    # Set the exit code
    all_filed_passed = True

    total_score = 0.0

    # Don't do anything if there are Go files
    if len(go_files) == 0:
        sys.exit(0)

    # Golint files
    i = 1
    n_files = len(go_files)
    for filename, score in go_files:
        if os.stat(filename).st_size == 0:
        	print(
                    'Skipping lint on {} (empty file)..'
                    '\tSKIPPED'.format(filename))

                # Bump parsed files
                i += 1
                continue

        status = ""
        # Start golinting
        sys.stdout.write("Running golint on {} (file {}/{})..\t".format(filename, i, n_files ))
        sys.stdout.flush()    
        score = runGolint(filename,golint)
        # Verify the score
        if score >= float(limit):
            status = 'PASSED'
        else:
            status = 'FAILED'
            all_filed_passed = False

        total_score += score

        # Add some output
        print('{:.2}/10.00\t{}'.format(decimal.Decimal(score), status))
        # Bump parsed files
        i += 1

    user =  _get_user()
    score_fd = open(scorefile, "r+")
    prev_score = float(score_fd.read())

    if 'FAILED' in status:
        new_score = prev_score
        """
        print "IN FAILED @@", prev_score
        new_score =  (total_score + prev_score) / (n_files + 1)
        score_fd.seek(0)
        score_fd.write("%s" % str(new_score))
        """
    else:
        new_score =  (total_score + prev_score) / (n_files + 1)
        score_fd.seek(0)
        score_fd.write("%s" % str(new_score))

    impact = new_score - prev_score
    total_score = total_score / n_files
    score_fd.close()

    with open(datfile, "a+") as f:
        f.write('{:40s} COMMIT SCORE {:5.2f} IMPACT ON REPO {:5.2f}  AGAINST {} STATUS {} \n'.format(user, total_score, impact, _current_commit(), status))
        """
        f.seek(-56*2, os.SEEK_END)
        x = f.readlines()
        prev_score = float(x[0].split()[1])
        """
    print "\n\n\n"
    print "Total score ", str(total_score)
    print "Your score made an impact of ", str(impact)
    print "\n\n\n"
    return all_filed_passed
