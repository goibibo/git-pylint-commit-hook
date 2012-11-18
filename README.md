git-pylint-commit-hook
======================

.. image:: https://secure.travis-ci.org/sebdah/git-pylint-commit-hook.png?branch=master

Pre-commit hook for Git checking Python code quality. The hook will check files ending with `.py` or that has a she bang containing `python`.

Set the threshold for the quality by updating the `LIMIT` value in the `pre-commit` hook.

Installation
------------

Download the hook (or just copy it from GitHub) and save it in your Git repo as `.git/hooks/pre-commit`.

Don't forget to make it executable.

Requirements
------------

This commit hook is written in Python and has the following requirements:

- [pylint](http://www.logilab.org/857)
- Python >2.5

Release notes
-------------

### 0.3 (2012-11-18)

- Fixed bug with non-python files getting checked, if they contained `python` on the first row

### 0.2 (2012-11-16)

- Added support for handling moved or deleted files

### 0.1 (2012-11-09)

 - Initial release of the commit hook