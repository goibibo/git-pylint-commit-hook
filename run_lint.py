#!/usr/bin/env python

"""
Git pre-commit hook for checking Python code quality.
Enables tracking of  commit score history

The hook requires pylint

AUTHOR:
    Sourabh Gupta <sourabh5588gupta@gmail.com>

LICENSE:
    Apache License 2.0
    http://www.apache.org/licenses/LICENSE-2.0.html
"""

import decimal
import os
import re
import sys
import subprocess
import collections
import ConfigParser
import json


from git_pylint_commit_hook.commit_hook import get_pylint_score
from common_methods import is_empty_file, run_subprocess, \
                                get_commit_file_data, create_specfic_commit_git_file

def _process_git_log_data(git_log_data):
    """
    parse and process git log data 
    """

    git_log_commit = []
    for each_commit in git_log_data.split('\n'):
        git_log_commit.append(json.loads(each_commit))
    return git_log_commit

def _get_lint_type(filename):
    file_ext = filename.split('.')[-1]
    lint_type = {
        'py' : 'pylint',
        'go' : 'golint',
    }
    return lint_type.get(file_ext, '')

def _get_lint_score(lint, git_commit_file):
    file_ext = git_commit_file.split('.')[-1]
    lint_types = {
    'py' : get_pylint_score,
    #'go' : _get_golint_score
    'other' : ''
    }
    return lint_types.get(file_ext, 'other')(lint, git_commit_file)


def _get_file_score(lint, lint_file, commit_sha='HEAD~1'):
    score = 0.0
    if is_empty_file(lint_file):
        return score
    git_commit_file = create_specfic_commit_git_file(lint_file, commit_sha)
    score = _get_lint_score(lint, git_commit_file)
    os.remove(git_commit_file)
    return score

def _get_status(commit_score):
    if commit_score >= 0:
        return 'SUCCESS'
    else:
        return 'Failure'

def _get_impact(commit_score):
    return str(commit_score*10) + '%'

def _get_repo_name():
    repo_name = run_subprocess('git rev-parse --show-toplevel')
    repo_name = repo_name.split('\n')[0]
    repo_name = repo_name.split('/')[-1]
    return repo_name

def get_insertion_and_deletions(changed_file, commit, prev_commit):
    updates = run_subprocess('git diff --stat {0}..{1} {2}'.format(commit, prev_commit, changed_file))
    updates = re.findall(r'\d+',updates)
    insert = 0
    if len(updates) > 0:
        insert = updates[1]
    if len(updates) > 1:
        delete = updates[2]
    return insert,delete

def _repo_score():
    """
    Calculate git repo score.
    """
    gitlogs = \
        'git log -n 10 --pretty=format:{"commit":"%H","user":"%an","email":"%ce"}'
    git_log_output = run_subprocess(gitlogs)

    process_git_log_data = _process_git_log_data(git_log_output)
    list_of_commit_score = []
    for i in xrange(0, len(process_git_log_data) - 1):
        commit_score = 0
        commit = process_git_log_data[i]['commit']
        prev_commit = process_git_log_data[i + 1]['commit']
        
        file_changed = \
            'git log  --name-only --pretty=format:%f {0}..{1}'.format(prev_commit,
                commit)
        file_changed_info = run_subprocess(file_changed)
        file_changed_list = file_changed_info.split('\n')[1:]
        for changed_file in file_changed_list:
            lint = _get_lint_type(changed_file)
            if lint:
                file_score = _get_file_score(lint, changed_file, commit)
                prev_file_score = _get_file_score(lint, changed_file, prev_commit)
                commit_score = (file_score - prev_file_score)
                insert,delete = get_insertion_and_deletions(changed_file, commit, prev_commit)
                list_of_commit_score.append({
                                        'score': commit_score,
                                        'commit': process_git_log_data[i]['commit'],
                                        'email': process_git_log_data[i]['email'],
                                        'status': _get_status(commit_score),
                                        'impact': _get_impact(commit_score),
                                        'file': changed_file,
                                        'repo': _get_repo_name(),
                                        'insert': insert,
                                        'delete':delete
                                    })
    print json.dumps(list_of_commit_score)

if __name__=="__main__":
    _repo_score()