=========
Utilities
=========

Cuckoo comes with a set of pre-built utilities to automatize several common
tasks.
You can find them in "utils" folder.

Cleanup utility
===============

If you want to delete all history, analysis, data and begin again from the first
task you need clean.sh utility.

.. note::

    Running clean.sh will delete:
    * Analyses
    * Binaries
    * Cuckoo task's database
    * Cuckoo logs

To clean your setup, run:

    $ cd utils
    $ sh clean.sh

Submission Utility
==================

Submits sample to analysis. This tool is already described in :doc:`submit`.

Web Utility
===========

Cuckoo's web interface. This tool is already described in :doc:`submit`.

Test Report Utility
===================

Run the reporting engine (run all reports) on an already available analysis
folder. So you don't need to run an analysis again to generate reports.
This is used mainly in debugging and developing Cuckoo.
For example if you want run again the report engine for analysis number 1:

    $ cd utils
    $ python testreport.py ../storage/analyses/1/

Test Signature Utility
======================

Run the signature engine (checks all signatures) on an already available 
analysis folder. So you don't need to run an analysis again.
This is used mainly in debugging and developing Cuckoo.
For example if you want run again the singature engine for analysis number 1:

    $ cd utils
    $ python testsignatures.py ../storage/analyses/1/
