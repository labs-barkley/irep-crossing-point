"""
One command from raw download to figures.

    python run.py

Stages run in the order the pre-registration requires: the panel is built, the
analytic prediction is computed and committed on training seasons only, and only
then does anything out-of-sample execute.

Dependencies: numpy and matplotlib. Nothing else. The database is read through
the standard library's sqlite3.
"""

import hashlib
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DATA = os.path.join(ROOT, "data")
DB = os.path.join(DATA, "lahman.sqlite")

URL = ("https://github.com/jknecht/baseball-archive-sqlite/releases/download/"
       "2022/lahman_1871-2022.sqlite")
SHA256 = "d688f51113bfce19d7314f9824ea0d080c074b5d106493bfea2ac8d3bfb8d3e2"


def fetch():
    if os.path.exists(DB):
        h = hashlib.sha256(open(DB, "rb").read()).hexdigest()
        if h == SHA256:
            print("STAGE 0  database present, checksum matches")
            return
        print("STAGE 0  checksum mismatch, re-downloading")
    os.makedirs(DATA, exist_ok=True)
    print("STAGE 0  downloading Lahman 1871-2022 (69 MB)")
    urllib.request.urlretrieve(URL, DB)
    h = hashlib.sha256(open(DB, "rb").read()).hexdigest()
    if h != SHA256:
        raise SystemExit("checksum mismatch after download: %s" % h)
    print("         checksum ok")


def stage(script):
    print()
    r = subprocess.run([sys.executable, script], cwd=SRC)
    if r.returncode != 0:
        raise SystemExit("%s failed" % script)


if __name__ == "__main__":
    fetch()
    stage("panel.py")
    stage("variance.py")
    print("\n  --- the analytic prediction is now on disk. Everything after this "
          "line is out-of-sample. ---")
    stage("validate.py")
    stage("figures.py")
    stage("sensitivity.py")
    print("\nDone. Figures, results and sensitivity analyses are in out/.")
