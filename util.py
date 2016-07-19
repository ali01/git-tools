import subprocess


def run_command(*arg, shell=True):
  stdout = subprocess.check_output(*arg, shell=shell, stderr=subprocess.STDOUT)
  return stdout.decode('utf-8').strip()
