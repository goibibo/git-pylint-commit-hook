#git-pylint-commit-hook

This git Pre-commit hook will allow
- limit to quality of each file checked in
- tracking against developer of impact on the quality of the commit
- logging of history

Based on /forked from : https://github.com/sebdah/git-pylint-commit-hook

##Installation

Install via PyPI

    pip install git-pylint-commit-hook


## Usage


To use ``git-pylint-commit-hook`` in a project, create a new file under ``/project/root/.git/hooks/pre-commit`` and add the following to that file:
```
    #!/usr/bin/env bash
    git-pylint-commit-hook
```

Save the file and make it executable:
```
   chmod +x .git/hooks/pre-commit
```

Your Python files should now be checked upon commit.

The commit hook will automatically be called when you are running `git commit`.

##Configuration

In the git commit hook above, multiple command line options can be passed

--limit : score watermark ; if any file scores below this limit, the commit is rejected [default 5]
--datfile : log file to log, user, score, impact etc  [default /tmp/git.dat]
--scorefile : file to store scores [default /tmp/scores.dat]
--suppress-report : Suppress report output if pylint fails

## Requirements


This commit hook is written in Python and has the following requirements:

- [pylint](http://www.logilab.org/857) (`sudo pip install pylint`)
- Python >2.5 and <3.0

