""" Commit hook for pylint """
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


def _get_list_of_committed_python_files():
    """ Returns a list of files about to be commited. """
    files = []
    # pylint: disable=E1103
    diff_index_cmd = 'git diff-index --cached %s' % _current_commit()
    output = subprocess.check_output(
        diff_index_cmd.split()
    )
    for result in output.split('\n'):
        if result != '':
            result = result.split()
            if result[4] in ['A', 'M']:
                if _is_python_file(result[5]):
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

def _is_python_file(filename):
    """Check if the input file looks like a Python script

    Returns True if the filename ends in ".py" or if the first line
    contains "python" and "#!", returns False otherwise.

    """
    if filename.endswith('.py'):
        return True
    else:
        with open(filename, 'r') as file_handle:
            first_line = file_handle.readline()
        return 'python' in first_line and '#!' in first_line


_SCORE_REGEXP = re.compile(
    r'^Your\ code\ has\ been\ rated\ at\ (\-?[0-9\.]+)/10')


def _parse_score(pylint_output):
    """Parse the score out of pylint's output as a float

    If the score is not found, return 0.0.

    """
    for line in pylint_output.splitlines():
        print line
        match = re.match(_SCORE_REGEXP, line)
        if match:
            print "MATCHn\n\n\n"
            return float(match.group(1))
    return 0.0


def check_repo(
        limit, pylint='pylint', pylintrc='.pylintrc', pylint_params=None,
        suppress_report=False, datfile="/tmp/git.dat", scorefile="/tmp/scores.dat"):
    """ Main function doing the checks

    :type limit: float
    :param limit: Minimum score to pass the commit
    :type pylint: str
    :param pylint: Path to pylint executable
    :type pylintrc: str
    :param pylintrc: Path to pylintrc file
    :type pylint_params: str
    :param pylint_params: Custom pylint parameters to add to the pylint command
    :type suppress_report: bool
    :param suppress_report: Suppress report if score is below limit
    """
    # List of checked files and their results
    python_files = _get_list_of_committed_python_files()

    # Set the exit code
    all_filed_passed = True

    total_score = 0.0

    # Don't do anything if there are no Python files
    if len(python_files) == 0:
        sys.exit(0)

    # Load any pre-commit-hooks options from a .pylintrc file (if there is one)
    if os.path.exists(pylintrc):
        conf = ConfigParser.SafeConfigParser()
        conf.read(pylintrc)
        if conf.has_option('pre-commit-hook', 'command'):
            pylint = conf.get('pre-commit-hook', 'command')
        if conf.has_option('pre-commit-hook', 'params'):
            pylint_params += ' ' + conf.get('pre-commit-hook', 'params')
        if conf.has_option('pre-commit-hook', 'limit'):
            limit = float(conf.get('pre-commit-hook', 'limit'))

    # Pylint Python files
    i = 1
    n_files = len(python_files)
    for python_file, score in python_files:
        # Allow __init__.py files to be completely empty
        if os.path.basename(python_file) == '__init__.py':
            if os.stat(python_file).st_size == 0:
                print(
                    'Skipping pylint on {} (empty __init__.py)..'
                    '\tSKIPPED'.format(python_file))

                # Bump parsed files
                i += 1
                continue

        # Start pylinting
        sys.stdout.write("Running pylint on {} (file {}/{})..\t".format(
            python_file, i, n_files ))
        sys.stdout.flush()
        try:
            command = [pylint]

            penv = os.environ.copy()
            penv["LANG"]="it_IT.UTF-8"
            penv["LC_CTYPE"]="it_IT.UTF-8"
            penv["LC_COLLATE"]="it_IT.UTF-8"

            """
            if pylint_params:
                command += pylint_params.split()
                if '--rcfile' not in pylint_params:
                    command.append('--rcfile={}'.format(pylintrc))
            else:
                command.append('--rcfile={}'.format(pylintrc))
            """

            command.append(python_file)



            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=penv)
            out, _ = proc.communicate()
            print "DONE"
        except OSError:
            print("\nAn error occurred. Is pylint installed?")
            sys.exit(1)

        # Verify the score
        score = _parse_score(out)
        if score >= float(limit):
            status = 'PASSED'
        else:
            status = 'FAILED'
            all_filed_passed = False

        total_score += score

        # Add some output
        print('{:.2}/10.00\t{}'.format(decimal.Decimal(score), status))
        if 'FAILED' in status:
            if suppress_report:
                command.append('--reports=n')
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                out, _ = proc.communicate()
            print out


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
