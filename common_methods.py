import os
import subprocess


def is_empty_file(python_file):
    """
    Checking empty init file
    """
    if os.stat(python_file).st_size == 0:
            return True
    return False


def get_commit_file_data(git_file, commit_sha='HEAD~1'):
    """
    get previous commit git file data
    """

    diff_index_cmd = 'git show %s:%s' % (commit_sha, git_file)
    return run_subprocess(diff_index_cmd)

def run_subprocess(process_command):
    """
     run subprocess in python
    """

    try:
        diff_index_cmd = process_command
        output = subprocess.check_output(diff_index_cmd.split())
    except Exception, e:
        output = ''
    return output

def create_specfic_commit_git_file(lint_file, commit_sha):
    git_commit_file_name = 'lint_' + lint_file.split('/')[-1]
    git_commit_file = '/'.join(lint_file.split('/')[:-1]
                                   + [git_commit_file_name])
    if os.path.isfile(git_commit_file_name):
    	os.remove(git_commit_file_name)
    f = open(git_commit_file, 'w')
    f.write(get_commit_file_data(lint_file, commit_sha))
    f.close()
    return git_commit_file
