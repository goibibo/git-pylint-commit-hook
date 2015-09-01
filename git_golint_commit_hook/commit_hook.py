#!/usr/bin/env python2.7
""" commit hook for golint """
import decimal
import os
import re
import sys
import subprocess
import collections
import ConfigParser
import tempfile
import urllib2
import json


ExecutionResult = collections.namedtuple(
    'ExecutionResult',
    'status, stdout, stderr'
)

def get_repo_name():
    currentpath = os.getcwd()
    dirname = os.path.basename(currentpath)
    return dirname

def get_changed_files(base, commit):
    if (base == "0000000000000000000000000000000000000000"):
	results = git(('git','show','--pretty=format:','--no-commit-id','--name-only',"%s" % (commit))).stdout
    else:
    	results = git(('git', 'diff', '--numstat', '--name-only', "%s..%s" % (base, commit))).stdout
    return results.strip().split('\n')

def git(args):
    environ = os.environ.copy()
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environ)
    stdout, stderr = process.communicate()
    status = process.poll()
    return ExecutionResult(status, stdout, stderr)

def get_file_content(filename, commit):
    results = git(('git', 'show', '%s:%s' % (commit, filename))).stdout
    return results

def _current_commit():
    if git('git rev-parse --verify HEAD'.split()).status:
        return '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
    else:
        return 'HEAD'

def _get_user(commit):
    """
    Returns user
    """
    get_user_cmd = 'git log -1 %s ' % (commit)
    get_user_cmd += '--format=%ae'
    user = subprocess.check_output(
        get_user_cmd.split()
    )
    return user.split()[0]

def _is_go_file(filename):
    """ Check if the input file looks like a Golang file.
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
    if totallines == 0:
	currentScore = 0
    else:
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
    line = sys.stdin.read()
    (base, commit, ref) = line.strip().split()
    reponame = get_repo_name()
    url_get_commit = 'http://10.70.210.192:4000/api/Commits/%s/%s/isExists' % (commit,reponame)
    request = urllib2.Request(url_get_commit) 
    json_data = urllib2.urlopen(url_get_commit).read()
    commit_data = json.loads(json_data) 
    commit_exists = commit_data['isExists']
    if commit_exists :
        sys.exit(0)
     
    modified = get_changed_files(base, commit)
    files=[]
    for fname in modified:
	if _is_go_file(fname):
		file_content = get_file_content(fname, commit)
		files.append((fname,file_content,None))	
  
    # Don't do anything if there are no Go files
    if len(modified) == 0:
        sys.exit(0)

    # Golint files
    i = 1
    skipped_filecount=0
    n_files = len(modified)
    user = _get_user(commit)
    url ='http://10.70.210.192:4000/api/Commits'
    for filename, filecontent, score in files:
	tmpfile = tempfile.NamedTemporaryFile(delete=False)	
	tmpfile.write(filecontent)
	tmpfile.close()

        if os.stat(tmpfile.name).st_size == 0:
        	print(
                    'Skipping {} (empty file)..'
                    '\tSKIPPED'.format(filename))
		skipped_filecount += 1
		os.unlink(tmpfile.name)
                # Bump parsed files
                i += 1
                continue

        # Start golinting
        sys.stdout.write("Processing {} (file {}/{})..\t".format(filename, i, n_files ))
        sys.stdout.flush()    
        score = runGolint(tmpfile.name,golint)
	os.unlink(tmpfile.name)
        status = ""

        # Verify the score
        if score >= float(limit):
            status = 'PASSED'
        else:
            status = 'FAILED'
        
        committed_data={}
	committed_data.update({"email":user})
 	committed_data.update({"repo":reponame})
	committed_data.update({"score":score})
	committed_data.update({"status":status})
	committed_data.update({"file":filename})
        committed_data.update({"commitid":commit}) 
        jsondata = json.dumps(committed_data)
        req = urllib2.Request(url,jsondata)
        req.add_header('Content-Type', 'application/json')
        urllib2.urlopen(req).read()
        # Add some output
        print('{:.2}/10.00'.format(decimal.Decimal(score)))
        # Bump parsed files
        i += 1
   
        with open(datfile, "a+") as f:
        	f.write('{:40s} COMMIT SCORE {:5.2f} IMPACT ON REPO  AGAINST {} STATUS {} \n'.format(user, score, commit, status))
      
