import io
from subprocess import call, Popen, PIPE

VERBOSE = 0

def prnt(text):
  if(VERBOSE and text):
    print(text)

def getDriveUse():
  u = '?%'
  try:
    cmd = 'df'
    output,error = Popen(cmd.split(),stdout = PIPE, stderr=PIPE).communicate()
    u = output.split()[11]
  except Exception as e:
    prnt(e)
  return u

def getCpuTemp():
  #vcgencmd measure_temp
  u = '?C'
  try:
    cmd = 'vcgencmd measure_temp'
    output,error = Popen(cmd.split(),stdout = PIPE, stderr=PIPE).communicate()
    u = output.split('=')[1]
  except Exception as e:
    prnt(e)
  return u.rstrip()

def aaaa():
  #vcgencmd measure_temp
  u = '?C'
  try:
    cmd = 'rm -f /home/a/Bilder/aaa*.txt'
    print(cmd.split())
    output,error = Popen(cmd,stdout = PIPE, stderr=PIPE, shell=True).communicate()
    print(error)
    print(output)
  except Exception as e:
    prnt(e)
  return u.rstrip()

#print(getDriveUse())
#aaaa()

#getDriveUse()
#getCpuTemp()
