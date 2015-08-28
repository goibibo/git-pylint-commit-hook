#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Commit hook for pylint """

import decimal
import os
import re
import sys
import subprocess
import collections
import ConfigParser
import json
import urllib2

ExecutionResult = collections.namedtuple('ExecutionResult',
        'status, stdout, stderr')


def _execute(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    (stdout, stderr) = process.communicate()
    status = process.poll()
    return ExecutionResult(status, stdout, stderr)


def _current_commit():
    """
        Getting current Commit
    """
    if _execute('git rev-parse --verify HEAD'.split()).status:
        return '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
    else:
        return 'HEAD'


def _get_list_of_committed_python_files():
    """ Returns a list of files about to be commited. """

    files = []

    # pylint: disable=E1103

    diff_index_cmd = 'git diff-index %s' % _current_commit()
    output = subprocess.check_output(diff_index_cmd.split())
    for result in output.split('\n'):
        if result != '':
            result = result.split()
            if result[4] in ['A', 'M']:
                if _is_python_file(result[5]):
                    files.append((result[5], None))  # None is initial score

    return files


def _get_user():
    """
    Returns user
    """

    get_user_cmd = 'git var GIT_AUTHOR_IDENT '
    user = subprocess.check_output(get_user_cmd.split())
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


_SCORE_REGEXP = \
    re.compile(r'^Your\ code\ has\ been\ rated\ at\ (\-?[0-9\.]+)/10')


def _parse_score(pylint_output):
    """Parse the score out of pylint's output as a float

    If the score is not found, return 0.0.

    """

    for line in pylint_output.splitlines():
        match = re.match(_SCORE_REGEXP, line)
        if match:
            return float(match.group(1))
    return 0.0


def _get_git_previous_commit():
    """
    Getting last commit SHA
    """

    diff_index_cmd = 'git log -n 1 --pretty=format:%h'
    output = subprocess.check_output(diff_index_cmd.split())
    return output


_GIT_PYLINT_MINIMUM_SCORE = 4


def _get_prev_score(pylint, python_files, commit_sha='HEAD~1'):
    """
        Getting prev commit file score
    """

    total_score = 0
    checked_pylint_files = 0
    avg_score = 0
    for (python_file, score) in python_files:
        if is_empty_file(python_file):
            continue
        git_commit_file = create_specfic_commit_git_file(python_file,
                commit_sha)
        (out, _) = _run_pylint(pylint, git_commit_file)
        os.remove(git_commit_file)
        if _parse_score(out):
            score = _parse_score(out)
            total_score += score
            checked_pylint_files += 1
    if checked_pylint_files:
        avg_score = total_score / checked_pylint_files
    if avg_score == 0:
        avg_score = _GIT_PYLINT_MINIMUM_SCORE
    return avg_score


def get_pylint_score(lint, git_commit_file):
    """
        It is giving pylint_score of the file.
    """

    (out, _) = _run_pylint(lint, git_commit_file)
    return _parse_score(out)


def _run_pylint(pylint, python_file, suppress_report=False):
    """
        Run pylint on python_file
    """
    try:
        command = [pylint]

        penv = os.environ.copy()
        penv['LANG'] = 'it_IT.UTF-8'
        penv['LC_CTYPE'] = 'it_IT.UTF-8'
        penv['LC_COLLATE'] = 'it_IT.UTF-8'

        command.append(python_file)

        if suppress_report:
            command.append('--reports=n')
        proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=penv)
        (out, _value) = proc.communicate()
    except OSError:
        print '\nAn error occurred. Is pylint installed?'
        sys.exit(1)
    return (out, _value)


def _process_git_log_data(git_log_data):
    """
    parse and process git log data 
    """

    git_log_commit = []
    for each_commit in git_log_data.split('\n'):
        git_log_commit.append(json.loads(each_commit))
    return git_log_commit


def _get_lint_type(filename):
    """
        Getting type of lint e.g. pylint or golint
    """

    file_ext = filename.split('.')[-1]
    lint_type = {'py': 'pylint'}
    return lint_type.get(file_ext, '')


def _get_lint_score(lint, git_commit_file):
    """
        Returning lint function.
    """

    file_ext = git_commit_file.split('.')[-1]
    lint_types = {'py': get_pylint_score, 'other': ''}  # 'go' : _get_golint_score
    return lint_types.get(file_ext, 'other')(lint, git_commit_file)


def _get_file_score(lint, lint_file, commit_sha='HEAD~1'):
    """
        Get file score
    """
    score = 0.0
    git_commit_file = create_specfic_commit_git_file(lint_file,
            commit_sha)
    score = _get_lint_score(lint, git_commit_file)
    os.remove(git_commit_file)
    return score


def _get_status(commit_score):
    """
        Get Status of file  
    """
    if commit_score >= 0:
        return 'PASSED'
    else:
        return 'FAILED'


def _get_impact(commit_score):
    """
        Get changed in score
    """
    return str(commit_score * 10) + '%'


def _get_repo_name():
    """
        Get repo name on which pylint is running
    """
    return os.path.basename(os.getcwd())


def get_insertion_and_deletions(changed_file, commit, prev_commit):
    """
        Get number of insert and delete on a particular commit
    """
    updates = \
        run_subprocess('git diff --stat {0}..{1} {2}'.format(commit,
                       prev_commit, changed_file))
    updates = re.findall(r'\d+', updates)
    insert = 0
    delete = 0
    if len(updates) > 0:
        insert = updates[1]
    if len(updates) > 1:
        delete = updates[2]
    return (insert, delete)


def _get_user(commit):
    """
    Returns user
    """

    get_user_cmd = 'git log -1 %s ' % commit
    get_user_cmd += '--format=%ae'
    user = subprocess.check_output(get_user_cmd.split())
    return user.split()[0]


def get_commit_file_data(git_file, commit_sha='HEAD~1'):
    """
    get previous commit git file data
    """

    diff_index_cmd = 'git show %s:%s' % (commit_sha, git_file)
    return run_subprocess(diff_index_cmd)


def is_empty_file(python_file):
    """
    Checking empty init file
    """

    if os.path.isfile(python_file) and os.stat(python_file).st_size \
        == 0:
        return True
    return False


def create_specfic_commit_git_file(lint_file, commit_sha):
    """
        Generate specfic commit git file
    """
    git_commit_file_name = 'lint_' + commit_sha + lint_file.split('/'
            )[-1]
    git_commit_file = '/tmp/' + git_commit_file_name
    if os.path.isfile(git_commit_file_name):
        os.remove(git_commit_file_name)
    f = open(git_commit_file, 'w')
    f.write(get_commit_file_data(lint_file, commit_sha))
    f.close()
    return git_commit_file


def get_changed_files(base, commit):
    """
        Get changed git file 
    """
    if base == '0000000000000000000000000000000000000000':
        results = \
            run_subprocess('git show --pretty=format: --no-commit-id --name-only %s'
                            % commit)
    else:
        results = run_subprocess('git diff --numstat --name-only %s..%s'
                                  % (base, commit))
    return results.strip().split('\n')


def run_subprocess(args):
    """
        Run subprocess on git commands
    """
    args = args.split(' ')
    try:
        environ = os.environ.copy()
        process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environ)
        (stdout, stderr) = process.communicate()
        status = process.poll()
    except Exception, e:
        print str(e)
    return ExecutionResult(status, stdout, stderr).stdout


def push_commit_score(
    limit,
    pylint='pylint',
    pylintrc='.pylintrc',
    pylint_params=None,
    suppress_report=False,
    datfile='/tmp/git.dat',
    scorefile='/tmp/scores.dat',
    ):
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

    line = sys.stdin.read()
    (base, commit, ref) = line.strip().split()

    git_changed_file_name_list = get_changed_files(base, commit)
    for changed_file in git_changed_file_name_list:
        commit_info = {}
        lint = _get_lint_type(changed_file)
        if lint:
            sys.stdout.write('Processing {} ..\t'.format(changed_file))
            sys.stdout.flush()
            if is_empty_file(lint_file):
                print 'Skipping {} (empty file)..\tSKIPPED'.format(changed_file)
                continue
            file_score = _get_file_score(lint, changed_file, commit)

            # prev_file_score = _get_file_score(lint, changed_file, base)

            commit_score = file_score
            (insert, delete) = \
                get_insertion_and_deletions(changed_file, commit, base)
            user = _get_user(commit)
            commit_info = {
                'score': commit_score,
                'commit': commit,
                'email': _get_user(commit),
                'status': _get_status(commit_score),
                'file': changed_file,
                'repo': _get_repo_name(),
                'insert': insert,
                'delete': delete,
                }
            jsondata = json.dumps(commit_info)
            url = 'http://10.70.210.192:4000/api/Commits'
            req = urllib2.Request(url, jsondata)
            req.add_header('Content-Type', 'application/json')
            urllib2.urlopen(req).read()

            # Add some output

            print '{:.2}/10.00\t{}'.format(decimal.Decimal(commit_score),
                    _get_status(commit_score))

            with open(datfile, 'a+') as f:
                f.write('{:40s} COMMIT SCORE {:5.2f} IMPACT ON REPO  AGAINST {} STATUS {} \n'.format(user,
                        commit_score, commit,
                        _get_status(commit_score))) 

def check_repo(
    limit,
    pylint='pylint',
    pylintrc='.pylintrc',
    pylint_params=None,
    suppress_report=False,
    datfile='/tmp/git.dat',
    scorefile='/tmp/scores.dat',
    ):
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
    for (python_file, score) in python_files:

        # Allow __init__.py files to be completely empty

        if is_empty_file(python_file):
            print 'Skipping pylint on {} (empty __init__.py)..\tSKIPPED'.format(python_file)

            # Bump parsed files

            i += 1
            continue

        # Start pylinting

        sys.stdout.write('Running pylint on {} (file {}/{})..\t'.format(python_file,
                         i, n_files))
        sys.stdout.flush()
        (out, _) = _run_pylint(pylint, python_file)

        # Verify the score

        score = _parse_score(out)
        file_prev_score = _get_prev_score(pylint, [(python_file,
                score)])
        if file_prev_score and score >= file_prev_score:
            status = 'PASSED'
        elif score >= float(limit):
            status = 'PASSED'
        else:
            status = 'FAILED'
            all_filed_passed = False

        total_score += score

        # Add some output

        print '{:.2}/10.00\t{}'.format(decimal.Decimal(score), status)
        if 'FAILED' in status:
            (out, _) = _run_pylint(pylint, python_file,
                                   suppress_report=True)
            print out

        # Bump parsed files

        i += 1

    user = _get_user()

    prev_score = _get_prev_score(pylint, python_files)

    if 'FAILED' in status:
        new_score = total_score
    else:
        new_score = (total_score + prev_score) / (n_files + 1)

    impact = new_score - prev_score
    total_score = total_score / n_files

    print 'Total score ', str(total_score)
    print 'Your score made an impact of ', str(impact)

    return all_filed_passed



            