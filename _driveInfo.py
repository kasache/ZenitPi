import io
import subprocess

VERBOSE = 0

def prnt(text):
  if(VERBOSE and text):
    print(text)

def getCpuUse():
  strResult = "n/a"
  strResult = subprocess.check_output(
    "top -b -n1 | awk '/Cpu\(s\):/ {print $2}'",
    stderr = subprocess.STDOUT,
    shell = True,
    universal_newlines = True)
  return strResult

def getDriveUse():
  u = '?%'
  try:
    cmd = 'df'
    output,error = subprocess.Popen(cmd.split(),stdout = subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    u = output.split()[11]
  except Exception as e:
    prnt(e)
  return u

def getCpuTemp():
  #vcgencmd measure_temp
  u = '?C'
  try:
    cmd = 'vcgencmd measure_temp'
    output,error = subprocess.Popen(cmd.split(),stdout = subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    u = output.split('=')[1]
  except Exception as e:
    prnt(e)
  return u.rstrip()

#print(getCpuUse())
#print(getDriveUse())
#aaaa()

#getDriveUse()
#getCpuTemp()
