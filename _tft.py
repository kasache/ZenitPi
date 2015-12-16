#!/usr/bin/python
import pygame
import io
import os
import time
import numpy as np
import picamera
import picamera.array
import RPi.GPIO as G
import threading
import smtplib
import sys
import getopt
import ftplib
#import urllib2
#import struct
import socket
import gc
from PIL import Image
from datetime import datetime
from os.path import basename
from os.path import exists
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
from email.utils import COMMASPACE, formatdate
from array import array
from fractions import Fraction
#from threading import Thread
#from threading import Timer
from subprocess import call, Popen, PIPE
from _htmlUi import HtmlUi
from _driveInfo import getDriveUse
from _driveInfo import getCpuTemp
from _driveInfo import getCpuUse
from _driveInfo import ggt
from _imap_gmail import ZenitMail
import SimpleHTTPServer
import SocketServer

ESYNC=1#ausloeser wird mit threading.event synchronisiert
VERBOSE = 0#redet viel
LOGFILE = 1#redet viel in datei
MCYC = 120
UICYC = 1
status = -2
abort = 0
dT = 0
t1 = 0
t2 = 0
t3 = 0
t4 = 0
dT1 = 0
dT2 = 0
dTrg = 0
trg1 = 0
trg2 = 0
wifi = 0
eTrgDwn = threading.Event()
#eTrgNxt = threading.Event()
logLck = threading.RLock()
lock = threading.RLock()
camLck = threading.RLock()
trgLck = threading.RLock()
inLck = threading.RLock()
hltLck = threading.RLock()
updUiLck = threading.RLock()
updHtmlLck = threading.RLock()
eIdleLck = threading.Event()
nMod = 0
nSet = 0
cntTrgUp = 0
cntTrgDwn = 0
zm = ZenitMail()
#wd = 0
UPDT = ('{:%Y-%m-%d-%H-%M-%S}').format(datetime.now())
lastError = ''
PORT = 8888
ALIVE = 0
ftpSRV = ''
ftpUSR = ''
ftpPWD = ''
ftpRDIR = ''
tmbL = []

#buttons
I1 = 40
I2 = 29
I3 = 16
#led
Qor = 35
Qur = 36
Qog = 37
Qug = 38
QFLS = 33
IS3 = 15
IS0 = 7
IS2 = 8
IS1 = 10
ITRG = 32
IM2 = 31
IM1 = 11
IM3 = 13
IM0 = 12
# set up the colors
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)
GREEN = (  0, 255,   0)
BLUE  = (  0,   0, 255)
SZ=(128,160)
screen = 0
fnt = 0
trds = 0
#Ls = []
F = 0
LL = 0
###                     [3]
###             [4]  ___----___[2]--TMLPS
###                 /125     60\  [1]--Foto2
###                /            \
###               |            30|  [0]--Foto
###           [5] |250           |
###                \            /  [9]--Video 1280x720
###            [7]  \500    __B/
###                     ----
###                 [7]       [8]--Video 1920x
###
###

#'mplayer -vf rotate=1 -vo fbdev2:/dev/fb1 -x 160 -y 90 -framedrop -zoom ' + vidDir 

tmlpsCmd = 'sudo raspistill -ISO %s -ex %s -awb %s -ifx %s -w %s -h %s -o /home/www/img/pic$DT.jpg'

#         [0           1           2        3        4        5        6        7                     8        9
modDscr = ['Foto Auto','Foto Semi','Foto M ','Zeitraffer ','Zeitraffer ','Zeitraffer ','Bewegung ','Zeitraffer CRONTAB ','Video 1280  ','Video 640  ']
modDscrShrt = ['F(A) ','F(S) ','F(M) ','Zeitraf. ','Zeitraf. ','Zeitraf. ','Bew. ','Zeitraf. CRON ','V1280 ','V640 ']
#                 0       1       2        3        4       5       6       7        8                9
cronTmlpsModDscr = ['1_min','5_min','15_min','30_min','1_std','3_std','6_std','11_uhr','1_std_9_18_uhr','3_std_9_18_uhr']

lstFilesToSend = []

F16_9 = 1.77777777778
F4_3  = 1.33333333333

ST_EXIT = -1
ST_IDLE = 0
ST_PREVIEW = 1
ST_ENCODING = 2
ST_MENU = 10
ST_REPLAY = 11
ST_HOLD_I1 = 12
ST_HOLD_I2 = 13
ST_FOTO_1 = 20
ST_FOTO_2 = 21
ST_FOTO_3 = 22
ST_TMLPS_1 = 23
ST_TMLPS_2 = 24
ST_TMLPS_4 = 25
#ST_TMLPS_FREE = 25
ST_MOTIONDETECT = 26
ST_TMLPS_CRON = 27
ST_VID_1280 = 28
ST_VID_640 = 29
ST_VID_STREAM = 30

#fileRoot = './'
fileRoot = '/home/www/'
imgDir = fileRoot + 'img/'
tmbDir = imgDir + 'tmb/'
vidDir = fileRoot + 'vid/'

def setLastError(err):
  global lastError
  lastError = err

def countLines(lst):
  l = []
  with open(lst, 'r') as f:
    l = list(f)
    f.close()
  return len(l)
  #

def prnt(text=''):
  with lock:
    if not text:
      text = 'invalid text?'
    if(VERBOSE):
      print(text)
    if(LOGFILE):
      #with logLck:
      try:
        with open(fileRoot+'log.txt', 'a') as f:
          f.write(('{:%Y-%m-%d-%H-%M-%S}').format(datetime.now()) + '\t' + getCpuTemp() + '\t' + str(threading.current_thread()) + '\t' + text + '\n')
      except:
        print('log ex')
  #prnt

def rdFtpAuth():
  global ftpSRV,ftpUSR,ftpPWD,ftpRDIR
  l = []
  with open('ftp.txt', 'r') as f:
    l = list(f)
    f.close()
  #
  if(len(l)==4):
    ftpSRV = l[0].rstrip()
    ftpUSR = l[1].rstrip()
    ftpPWD = l[2].rstrip()
    ftpRDIR = l[3].rstrip()


def checkDiskSpace():
  try:
    if(float(getDriveUse().strip('%')) > 90):
      setLastError('Zu wenig Speicher!')
      return 0
    else:
      return 1
  except:
    L1.red()
    return -1

def sendFileFtp(fn, ldir, rdir, srv, usr, pwd):
  prnt('sendFileFtp '+fn+' '+ldir+' '+rdir+' '+srv+' '+usr+' '+pwd)
  L1.ylw()
  res=False
  try:
    if(isInSubnet(srv)):
      ftp = ftplib.FTP(srv)
      ftp.login(usr, pwd)
      ftp.cwd(rdir)
      ftp.storbinary('STOR ' + fn, open(ldir+fn, 'r'))
      ftp.quit()
      res=True
  except Exception as ex:
    prnt(str(ex))
  L1.off()
  return res

#Modus und Einstellung lesen
def readMS():
  global nMod, nSet
  #prnt('IM'+str(G.input(IM3))+str(G.input(IM2))+str(G.input(IM1))+str(G.input(IM0)))
  nMod = G.input(IM3) << 3
  nMod = nMod | G.input(IM2) << 2
  nMod = nMod | G.input(IM1) << 1
  nMod = nMod | G.input(IM0)
  #prnt('nMod ' + str(nMod))
  #prnt('IS'+str(G.input(IS3))+str(G.input(IS2))+str(G.input(IS1))+str(G.input(IS0)))
  nSet = G.input(IS3) << 3
  nSet = nSet | G.input(IS2) << 2
  nSet = nSet | G.input(IS1) << 1
  nSet = nSet | G.input(IS0)
  #prnt('nSet ' + str(nSet))
  #readMS


#
########## Menu Fotos
# [Fotos] ->  Anz.
#  Video      Loe.
#  <----      <--
#
#
########## Menu Video
#  Fotos      Anz.
# [Video] ->  Loe.
#  <----      <--
#
########## Menu verlassen 
#  Fotos
#  Video
# [<----]
#
#
class CamMenu:
  def __init__(self):
    self.L = 3
    self.iSel = 0
    self.iLvl = 0
    self.iTmb = 0
    self.M = []
    self.M.append(['Bild','Film','<---'])
    self.M.append(['Vor','Zur.','Zeigen','Loeschen','<---'])
  def show(self, screen, fnt):
    prnt('menu show')
    sl = 10
    #tmb lesen tmbL
    if(self.iLvl == 1):
      img=pygame.image.load(tmbDir + tmbL[self.iTmb])
      showImg(img)
      #
    for i in range(0,len(self.M[self.iLvl])):
      txt = self.M[self.iLvl][i]
      if(i==self.iSel):
        text = ('[' + txt + ']')
      else:
        text = (' ' + txt + ' ')
      txtsrfc = fnt.render(txt, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
      txtsrfc = pygame.transform.rotate(txtsrfc,270)
      h,l=fnt.size(txt)
      screen.blit(txtsrfc,(sl,(160-h)-1))
      sl=sl+l
    #
  def sel(self):
    prnt('menu sel')
    if(self.iSel==len(self.M[self.iLvl])):
      self.iLvl=self.iLvl-1
      if(self.iLvl<0):
        self.iLvl=0
    if(self.M[self.iLvl][self.iSel] == 'Vor'):
      self.iTmb=self.iTmb+1
    if(self.M[self.iLvl][self.iSel] == 'Zur.'):
      self.iTmb=self.iTmb-1
    self.iTmb=self.iTmb%len(tmbL)      
    #
  def up(self):
    prnt('menu up')
    self.iSel=self.iSel+1
    self.iSel=self.iSel%len(self.M[self.iLvl])
    #
  def down(self):
    prnt('menu down')
    self.iSel=self.iSel-1
    self.iSel=self.iSel%len(self.M[self.iLvl])
  def toString(self):
    prnt('menu down ' + self.M[self.iLvl][self.iSel])
  #def update(self, status):
  #  if(status == )

menu = CamMenu()

class CamSettings:
  def __init__(self):
    self.C = 6
    self.AwbMod = ['auto','sunlight','cloudy','shade','tungsten','fluorescent','incandescent','flash','horizon','off']
    self.ExpMod = ['auto','night','nightpreview','backlight','spotlight','sports','snow','beach','verylong','fixedfps','antishake','fireworks','off']
    self.ExpCps = [-25,-20,-15,-12,-9,-6,-3,0,3,6,9,12,15,20,25]
    self.ImgEff =  ['none','negative','solarize','sketch','denoise','emboss','oilpaint','hatch','gpen','pastel','watercolor','film','blur','saturation','colorswap','washedout','posterise','colorpoint','colorbalance','cartoon','deinterlace1','deinterlace2']
    self.Iso = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100]
    self.Set = 0
    self.Itv = [-1,10,30,60,300,1800,3600,21600,43200,86400]
    self.CronItv = cronTmlpsModDscr
    self.iIso = 0
    self.iAwbMod = 0
    self.iExpMod = 0
    self.iExpCps = 7
    self.iImgEff = 0
    self.ImgCnt = 0
    self.iSel = 0
    self.isDirty = 0
  def reset(self):
    prnt('camstt reset')
    #self.iIso = 0
    self.iAwbMod = 0
    self.iExpMod = 0
    self.iExpCps = 7
    self.iImgEff = 0
    self.Set = nSet
    self.ImgCnt = 0
    self.iSel = 0
    self.isDirty = 0
    #
  def save(self, path):
    prnt('save')
    with open(path+'save.txt', 'w+') as f:
      f.seek(0,0)
      f.write(str(self.C) + ' ' + str(self.iAwbMod) + ' ' + str(self.iExpMod) + ' ' + str(self.iExpCps) + ' ' + str(self.iImgEff) + ' ' + str(self.iSel) + ' ' + str(self.Set) + ' ' + str(self.ImgCnt) + ' ' + getDriveUse() + ' ' + getCpuTemp() + ' ' + ('{:%Y-%m-%d-%H-%M-%S}').format(datetime.now()) + ' ' + lastError)
    #
  def read(self, path):
    prnt('read')
    res = False
    try:
      with open(path+'save.txt', 'r') as f:
        f.seek(0,0)
        ll = list(f)
      prnt(ll)#
      l = ll[0].split()
      if(self.C <= len(l[0])):
        self.iAwbMod = int(l[1])
        self.iExpMod = int(l[2])
        self.iExpCps = int(l[3])
        self.iImgEff = int(l[4])
        self.Set = int(l[5])
        self.ImgCnt = int(l[6])
        res = True
      else:
        prnt('wrong CamSettings count')
    except:
      L1.red()
      prnt('EXC no settings')
    return res
  def cntDwn(self):
    self.ImgCnt = self.ImgCnt - 1
    return self.ImgCnt
  def getPer(self,st):
    t = self.Itv[self.Set]
    if(st==ST_TMLPS_CRON):
      t = self.CronItv[self.Set%len(self.CronItv)]
    #elif(st==ST_TMLPS_FREE):
    #  t = -1
    else:
      t = self.Itv[st-ST_TMLPS_1+1]
    return t
    #
  def getCnt(self,st):
    cc = 50000
    #if(st!=ST_TMLPS_FREE and st!=ST_TMLPS_CRON):
    if(st!=ST_TMLPS_CRON):
      cc = 100*(2**self.Set)
      #
    self.ImgCnt = cc
    return cc
    #
  def getDur(self):
    return 5*(2**self.Set)
    #
  def getSet(self):
    readMS()
    st = nMod+ST_FOTO_1
    if(st == ST_TMLPS_CRON):
      res = self.getPer(st)#abstand zw. aufnahmen (1min,1std,1tag)
      #elif(st == ST_TMLPS_FREE):
      #  res = self.getPer(st)#abstand zw. aufnahmen, sekunden oder trigger
    elif(st >= ST_TMLPS_1 and st < ST_TMLPS_4):
      res = self.getCnt(st)#anzahl bilder
    elif(st == ST_VID_1280 or st == ST_VID_640):
      res = self.getDur()#dauer aufnahme
    else:
      res = self.Set
    return res
    #
  def selNext(self):
    prnt('camstt selNext')
    self.iSel=self.iSel+1
    self.iSel=self.iSel%self.C
    #
  def up(self):
    prnt('camstt up')
    if(self.iSel==2):
      self.iExpCps=self.iExpCps+1
      self.iExpCps=self.iExpCps%len(self.ExpCps)
    elif(self.iSel==1):
      self.iIso=self.iIso+1
      self.iIso=self.iIso%len(self.Iso)
    elif(self.iSel==5):
      self.iAwbMod=self.iAwbMod+1
      self.iAwbMod=self.iAwbMod%len(self.AwbMod)
    elif(self.iSel==0): 
      self.iExpMod=self.iExpMod+1
      self.iExpMod=self.iExpMod%len(self.ExpMod)
    elif(self.iSel==4):  
      self.iImgEff=self.iImgEff+1
      self.iImgEff=self.iImgEff%len(self.ImgEff)
    elif(self.iSel==3):
      self.Set = self.Set + 1
      self.Set = self.Set%10
    self.isDirty = 1
    #
  def down(self):
    prnt('camstt down')
    if(self.iSel==2):
      self.iExpCps=self.iExpCps-1
      if(self.iExpCps<0):
        self.iExpCps=7
    elif(self.iSel==1): 
      self.iIso=self.iIso-1
      if(self.iIso<0):
        self.iIso=len(self.Iso)-1
    elif(self.iSel==5): 
      self.iAwbMod=self.iAwbMod-1
      if(self.iAwbMod<0):
        self.iAwbMod=len(self.AwbMod)-1
    elif(self.iSel==0): 
      self.iExpMod=self.iExpMod-1
      if(self.iExpMod<0):
        self.iExpMod=len(self.ExpMod)-1
    elif(self.iSel==4):
      self.iImgEff=self.iImgEff-1
      if(self.iImgEff<0):
        self.iImgEff=len(self.ImgEff)-1
    elif(self.iSel==3):
      self.Set = self.Set - 1
      if(self.Set<0):
        self.Set = 0      
    self.isDirty = 1
    #
  def use(self,cam):
    prnt('use settings')
    cam.exposure_compensation = self.ExpCps[self.iExpCps]
    cam.iso = self.Iso[self.iIso]
    cam.awb_mode = self.AwbMod[self.iAwbMod]
    cam.exposure_mode = self.ExpMod[self.iExpMod]
    cam.image_effect = self.ImgEff[self.iImgEff]
    #
  def toStrExpCps(self,sel):
    s=str(self.ExpCps[self.iExpCps])
    if(self.iExpCps!=7):
      s = '*'+s
    if(self.iSel==sel):
      s = ' EV:['+s+']'
    else:
      s = ' EV: '+s+' '
    return s
  def toStrIso(self,sel):
    s=str(self.Iso[self.iIso])
    if(self.iIso!=0):
      s = '*'+s
    if(self.iSel==sel):
      s = ' ISO:['+s+']'
    else:
      s = ' ISO: '+s+' '
    return s
  def toStrAwbMod(self,sel):
    s=self.AwbMod[self.iAwbMod]
    if(self.iAwbMod!=0):
      s = '*'+s
    if(self.iSel==sel):
      s = 'AWB:['+s+']'
    else:
      s = 'AWB: '+s+' '
    return s
  def toStrExpMod(self,sel):
    s=self.ExpMod[self.iExpMod]
    if(self.iExpMod!=0):
      s = '*'+s
    if(self.iSel==sel):
      s = ' MOD:['+s+']'
    else:
      s = ' MOD: '+s+' '
    return s
  def toStrImgEff(self,sel):
    s=self.ImgEff[self.iImgEff]
    if(self.iImgEff!=0):
      s = '*'+s
    if(self.iSel==sel):
      s = ' EFF:['+s+']'
    else:
      s = ' EFF: '+s+' '
    return s
  def getTime(self, tm):
    s = ' s.'
    if(tm > 3600):
      tm = tm/3600
      s = ' h.'
    elif(tm > 60):
      tm = tm/60
      s = ' m.'
    return "{:.2f}".format(tm)  + s
    #
  def toStrSet(self,sel):
    s=str(self.getSet())
    st = nMod+ST_FOTO_1
    #if(st == ST_TMLPS_FREE):
    #  if(self.Set == 0):
    #    s = ' TRG'
    #  else:
    #    s=s+' sek.'
    if(st >= ST_TMLPS_1 and st < ST_TMLPS_4):
      s=s+'x'
    elif(st == ST_VID_1280 or st == ST_VID_640):
      s=str(self.getDur())+' sek.'
    if(self.iSel==sel):
      s = ' S:['+s+']'
    else:
      s = ' S: '+s+' '
    return s
  def toStringExp(self):
    return self.toStrExpMod(0)+self.toStrIso(1)+self.toStrExpCps(2)
  def toStringEff(self):
    res = self.toStrAwbMod(5)+self.toStrImgEff(4)+self.toStrSet(3)
    return res

camStt = CamSettings()

class DuoLed:
  def __init__(self,r,g,G):
    self.r = r
    self.g = g
    self.G = G
  def dark(self):
    hr = datetime.now().hour
    if(hr >= 19 or hr < 7):
      self.off()
      return True
    else:
      return False
  def off(self):
    try:
      G.output((self.r,self.g),0)
    except Exception as e:
      prnt('L.off' + str(e))  
  def red(self, frc=0):
    try:
      if(self.dark() and frc==0):
        return
      G.output((self.r,self.g),0)
      G.output(self.r,1)
    except Exception as e:
      prnt('L.red' + str(e))  
  def grn(self):
    try:
      if(self.dark()):
        return
      G.output((self.r,self.g),0)
      G.output(self.g,1)
    except Exception as e:
      prnt('L.grn ' + str(e))  
  def ylw(self, frc=0):
    try:
      if(self.dark() and frc==0):
        return
      G.output((self.r,self.g),0)
      G.output((self.r,self.g),1)
    except Exception as e:
      prnt('L.ylw' + str(e))  
  def isOn(self):
    ison = False
    try:
      if(G.input(self.g)==1):
        ison = True
      elif(G.input(self.r)==1):
        ison = True
    except Exception as e:
      prnt('L.isOn' + str(e))  
    return ison
  #class DuoLed

L0 = DuoLed(Qor,Qog,G)
L1 = DuoLed(Qur,Qug,G)

def holdI1_10():
  global L0,dT1
  prnt('holdI1_10 ' + str(dT1))
  if(dT1==0 and G.input(I1)==0):
    L0.red()

def holdI2_10():
  global L0,dT2
  prnt('holdI2_10 ' + str(dT2))
  if(dT2==0 and G.input(I2)==0):
    L1.red()
  #
def holdI1_5():
  global L0,dT1
  prnt('holdI1_10 ' + str(dT1))
  if(dT1==0 and G.input(I1)==0):
    L0.ylw()

def holdI2_5():
  global L0,dT2
  prnt('holdI2_10 ' + str(dT2))
  if(dT2==0 and G.input(I2)==0):
    L1.grn()
  #

def ledHalt():
  global L1,dT
  prnt('ledHalt ' + str(dT))
  if(dT==0 and G.input(I3)==0):
    L1.red(frc=1)
  #
def ledReboot():
  global L1,dT
  prnt('ledReboot ' + str(dT))
  if(dT==0 and G.input(I3)==0):
    L1.ylw(frc=1)
  #
def ledExit():
  global L1,dT
  prnt('ledExit ' + str(dT))
  if(dT==0 and G.input(I3)==0):
    L1.grn()
  #

def hasInet():
  return len(getIp())>6
  #
def isInSubnet(subn):
  #prnt('isInSubnet ' + subn)
  ip = getIp().split('.')
  sb = subn.split('.')
  res = True
  if(len(ip) == len(sb) and len(ip)==4):
    for i in range(0,3):
      #prnt(ip[i] + '==' + sb[i])
      res = (ip[i]==sb[i])
  else:
    res = False
  return res
  

def getIp():
  #print('>getIp')
  ip = '-'
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 0))  # connecting to a UDP address doesn't send packets
    ip = s.getsockname()[0]
  except Exception as e:
    prnt('getIp ' + str(e))
    ip = '?'
  #print('<getIp' + ip)
  return ip

def wrtCenterText(txt1, txt2):
  global screen
  font1 = pygame.font.SysFont("arial", 9, bold=1)
  txtsrfc = font1.render(txt1, 1, pygame.Color(255,255,0), pygame.Color(0,0,255))
  txtsrfc=pygame.transform.rotate(txtsrfc,270)
  h,l=font1.size(txt1)
  screen.blit(txtsrfc,((64+l),(160-h)/2))
  #
  txtsrfc = font1.render(txt2, 1, pygame.Color(255,255,0), pygame.Color(0,0,255))
  txtsrfc=pygame.transform.rotate(txtsrfc,270)
  h,l=font1.size(txt2)
  screen.blit(txtsrfc,((64-l),(160-h)/2))
  #

def wrtTft(text='', live=0, pos=(1,1)):
  global screen,fnt,status
  #prnt('wrtTft' + text)
  font = pygame.font.SysFont("arial", 9, bold=0)
  if(live):
    txt1 = camStt.toStringEff()
    txtsrfc = font.render(txt1, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
    txtsrfc=pygame.transform.rotate(txtsrfc,270)
    screen.blit(txtsrfc,(115,1))
    text = camStt.toStringExp()
    #linie
    pygame.draw.line(screen, WHITE, [64, 0], [64,159], 1)
    if((nMod+ST_FOTO_1) > ST_FOTO_3):
      pygame.draw.line(screen, RED, [19, 0], [19,159], 1)
      pygame.draw.line(screen, RED, [109, 0], [109,159], 1)
    #
  elif(status == ST_IDLE or status == ST_ENCODING):
    screen.fill(BLUE)
    txt1 = getIp()
    if(wifi == 0):#DIKAM
      txtsrfc = font.render(txt1, 1, pygame.Color(0,0,0), pygame.Color(55,255,55))
    else:
      txtsrfc = font.render(txt1, 1, pygame.Color(0,0,0), pygame.Color(255,255,55))
    txtsrfc=pygame.transform.rotate(txtsrfc,270)
    screen.blit(txtsrfc,(115,1))
    font1 = pygame.font.SysFont("arial", 9, bold=1)
    txt1=''
    txt2=''
    ctm = isCronTmlps()
    if(ctm != 'none'):
      txt1 = ctm + ' ZEITRAFFER ...'
      txt2 = 'zum Beenden ausloesen'
    elif(status == ST_ENCODING):
      txt1 = 'ENCODING ...'
      txt2 = 'bitte warten'
    else:
      txt1 = 'AUSLOESER HALTEN'
      txt2 = 'DANN LOSLASSEN'
    wrtCenterText(txt1,txt2)
    #
    txt2 = ('{:%H:%M}').format(datetime.now())
    txtsrfc = font.render(txt2, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
    txtsrfc=pygame.transform.rotate(txtsrfc,270)
    h,l=font.size(txt2)
    screen.blit(txtsrfc,(1,(160-h)-1))
    if(len(lastError)>0):
      txtsrfc = font1.render(lastError, 1, pygame.Color(255,0,0), pygame.Color(0,0,255))
      txtsrfc=pygame.transform.rotate(txtsrfc,270)
      h,l=font1.size(lastError)
      screen.blit(txtsrfc,((128-l)/4,(160-h)/2))
    #
  elif(status == ST_HOLD_I1):
    #obere taste gehalten
    txt1 = 'Taste 10s halten zum'
    txt2 = 'Video erstellen'
    wrtCenterText(txt1,txt2)
  elif(status == ST_HOLD_I2):
    #mittlere taste gehalten
    txt1 = 'Taste 10s halten zum'
    txt2 = 'ALLE Bild/Vid. loeschen!'
    wrtCenterText(txt1,txt2)
  elif(status == ST_MENU):
    text = menu.show(screen,fnt)
  elif(status > ST_FOTO_3 and status <= ST_VID_STREAM):
    if(status > ST_FOTO_3 and status < ST_VID_1280):
      txt1 = 'Zeitraffer ...'
      font1 = pygame.font.SysFont("arial", 11, bold=1)
      txtsrfc = font1.render(txt1, 1, pygame.Color(255,255,0), pygame.Color(0,0,255))
      txtsrfc=pygame.transform.rotate(txtsrfc,270)
      h,l=font1.size(txt1)
      screen.blit(txtsrfc,((128-l)/2,(160-h)/2))
    txt1 = '<- ABBRUCH'
    txtsrfc = font.render(txt1, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
    txtsrfc=pygame.transform.rotate(txtsrfc,270)
    screen.blit(txtsrfc,(115,1))
  if(status != ST_PREVIEW):
    txt1 = getDriveUse() + ' ' + getCpuTemp() + ' ' + getCpuUse()
    txtsrfc = font.render(txt1, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
    txtsrfc=pygame.transform.rotate(txtsrfc,270)
    h,l=font.size(txt1)
    screen.blit(txtsrfc,(115,(160-h)-1))
  txtsrfc = font.render(text + '(' + str(status) + ')', 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
  txtsrfc=pygame.transform.rotate(txtsrfc,270)
  screen.blit(txtsrfc,pos)
  #
  pygame.display.update()
  #prnt('<wrtTft')
  #

def wrtMode():
  #
  text = ' '
  readMS()
  st = nMod+ST_FOTO_1
  if(st == ST_TMLPS_CRON):
    text = text + cronTmlpsModDscr[nSet%len(cronTmlpsModDscr)]
  elif(st >= ST_TMLPS_1 and st < ST_TMLPS_4):
    text = text + ' B, ' + str(camStt.getPer(st)) + ' T'
  else:
    text = camStt.toStrSet(9)
  text = modDscrShrt[nMod%len(modDscrShrt)] + text + '  '+str(nSet)
  wrtTft(text)
  #

def startUpdateUiPeriodic():
  prnt('startUpdateUiPeriodic>')
  t = threading.Thread(target=updateUiPeriodic)
  t.setDaemon(1)
  t.start()
  prnt('startUpdateUiPeriodic<')
  #

def updateUiPeriodic():
  global status, ALIVE
  ii = 0
  while(status >= ST_IDLE):
    ii=ii+1
    ALIVE=ALIVE+1
    try:
      if(ALIVE%31==0):
        prnt('ALIVE')
        ALIVE=0
      if(status == ST_IDLE):
        if(isCronTmlps() != 'none'):
          if(ii>5):
            L0.ylw()
            ii=0
          else:
            L0.grn()
        else:
          L0.grn()
    except Exception as e:
      prnt(str(e))
      L1.red()
      #
    updateUi()
    time.sleep(UICYC)
  #

def updateUi():
  global status
  with updUiLck:
    if(status == ST_IDLE or status == ST_ENCODING):
      try:
        wrtMode()
      except Exception as e:
        prnt(str(e))
    #

def showAllJpg():
  global status
  if(status == ST_IDLE):
    for root, dirs, files in os.walk(tmbDir, topdown=True):
      for name in files:
        st = status
        status = ST_REPLAY
        img=pygame.image.load(tmbDir+name)
        showImg(img)
        time.sleep(3.0)
        status = st

def playAllVid():
  global status
  if(status == ST_IDLE):
    for root, dirs, files in os.walk(vidDir, topdown=True):
      for name in files:
        #t = Thread(target=sysCall, args=(cmd,))
        #t.start()
        playVid(vidDir+name)

def playVid(vid):
  global status
  prnt('playVid ' + vid)
  if(status == ST_IDLE):
    st = status
    status = ST_REPLAY
    sysCall('mplayer -vf rotate=1 -vo fbdev2:/dev/fb1 -x 80 -y 64 -framedrop -zoom ' + vid)
    #sysCall('mplayer -vf rotate=1 -vo fbdev2:/dev/fb1 -x 160 -y 90 -framedrop -zoom ' + vid)
    status = st

def sysCall(cmd, log=True):
  if(log):
    prnt('call> ' + cmd)
  try:
    #Popen(cmd,stdout=PIPE, stderr=PIPE, shell=True).wait()
    proc = Popen(cmd, shell=True)
    if(log):
      prnt('call wait ')
    proc.wait()
  except Exception as e:
    if(log):
      L1.red()
      prnt('ex sysCall ' + str(e))
  #
  if(log):
    prnt('call< ' + cmd)

def asyncSysCall(cmd,async=False):
  prnt('asyncSysCall ' + cmd + ' async=' + str(async))
  if(async):
    t = threading.Thread(target=sysCall, args=(cmd,))
    t.start()
  else:
    sysCall(cmd)
  #

def capt(cam):
  with camLck:
    prnt('capt ' + str(cam))
    try:
      fn=('pi{:%Y-%m-%d-%H-%M-%S}.jpg').format(datetime.now())
      cam.capture(imgDir + fn, use_video_port=True)
      prnt('captured ' + imgDir + fn)
      createTmb(imgDir + fn)
      updateHtml()
      att=[]
      att.append(imgDir + fn)
      #zm.sendMail('bewegung erkannt ', _text='', _files=att)
    except Exception as ex:
      prnt('capt ' + str(ex))

def asyncCapture(cam):
  prnt('asyncCapture')
  try:
    t = threading.Thread(target=capt, args=(cam,))
    t.start()
  except Exception as ex:
    prnt('asyncCapture ' + str(ex))
  #


def mailCllb(addr, cmd):
  global abort, eIdleLck
  eIdleLck.clear()
  try:
    to=[]
    to.append(addr)
    ctm = isCronTmlps()
    #if(ctm == 'none' and (status == ST_IDLE or status == ST_VID_STREAM)):
    if(status == ST_IDLE or status == ST_VID_STREAM):
      L0.red()
      if(cmd[0].lower() == 'help'):
        txt = 'Gueltiger Betreff: trigger foto=name.jpg=flash=iso=mode=effect=expc\n' 
        txt = txt + 'flash  0 / 1 \n'
        txt = txt + 'iso    0..800 \n'
        txt = txt + 'mode   ' + str(camStt.ExpMod) +'\n'
        txt = txt + 'effect ' + str(camStt.ImgEff) +'\n'
        zm.sendMail('Re: ' + cmd[0], _text=txt, _send_to=to)
      elif(cmd[0].lower() == 'trigger'):
        f = extern_trigger(cmd[1])
        att=[]
        #prnt('sende ' + fn)
        att.append(f)
        zm.sendMail('Re: ' + cmd[0], _text='echo', _send_to=to, _files=att)
        #sysCall('rm -f ' + f)
      elif(ctm == 'none' and cmd[0].lower() == 'stream'):
        if(cmd[1].lower() == '0'):
          abort = 1
        else:
          startStreamAsync()
          zm.sendMail('Re: ' + cmd[0], _text='tcp/h264://' + getIp() + ':8000', _send_to=to)
      elif(cmd[0].lower() == 'delete_mails'):
        zm.deleteAllSeen()
      L0.grn()
      #prnt('sollte mail senden an ' + addr)
    elif(ctm != 'none'):
      zm.sendMail(ctm, _text=':P', _send_to=to)
    else:
      zm.sendMail('hab grad was anderes zu tun', _text=':P', _send_to=to)
  except Exception as e:
    prnt('mailCallb ' + str(e))
    L1.red()
  eIdleLck.set()
  #mailClbk

def sendMail(text, atts):
  zm.sendMail(text, _files=atts)
  #

def sendMailAsync():
  atts = [F]
  prnt('before send ... ')
  t = threading.Thread(target=sendMail, args=('haha',atts))
  t.setDaemon(1)
  t.start()
  #sendMail('click ',atts)

def startCheckMailPeriodic():
  prnt('startCheckMailPeriodic>')
  t = threading.Thread(target=checkMailPeriodic)
  t.setDaemon(1)
  t.start()
  prnt('startCheckMailPeriodic<')
  # 

#alle MCYC Sekunden die emails abrufen
def checkMailPeriodic():
  readMS()
  st = status
  #if(st == ST_IDLE):
  #  st = nMod+ST_FOTO_1
  while(st >= ST_IDLE):
    time.sleep(MCYC)
    prnt('checkMailPeriodic ' + str(status))
    try:
      if(st == ST_IDLE or st == ST_VID_STREAM or st == ST_TMLPS_CRON):
        L1.ylw()
        if(hasInet()):
          #prnt('getSubscribers')
          zm.getSubscribers()
          prnt('copyOutstandingAsync')
          copyOutstandingAsync()
        else:
          restartNetwork()
    except Exception as ex:
      prnt('checkMailPeriodic ' + str(ex))
    L1.off()
  #

def checkMail():
  zm.getSubscribers()
  #
#
def checkMailAsync():
  t = threading.Thread(target=checkMail)
  t.setDaemon(1)
  t.start()
  #checkMailAsync

def copyOutstandingFtp():
  global lstFilesToSend
  try:
    while(len(lstFilesToSend)>0):
      fn = lstFilesToSend[0]
      if(sendFileFtp(fn, imgDir , ftpRDIR, ftpSRV, ftpUSR, ftpPWD)):
        sysCall('rm -f '+ imgDir + fn, log=False)
        lstFilesToSend.remove(fn)
      else:
        break;
  except Exception as ex:
    prnt('copyOutstandingFtp ' + str(ex))

def copyOutstandingAsync():
  t = threading.Thread(target=copyOutstandingFtp)
  t.setDaemon(1)
  t.start()

def deleteAll(filter=''):
  global eIdleLck
  eIdleLck.clear()
  try:
    with updUiLck:
      if(filter==''):
        wrtTft('alle Dateien loeschen...')
        sysCall('rm -f ' + imgDir +'pi*.jpg')
        sysCall('rm -f ' + tmbDir +'*.jpg')
        sysCall('rm -f ' + vidDir +'*.avi')
        sysCall('rm -f ' + vidDir +'*.h264')
        sysCall('rm -f ' + fileRoot +'logBefore*.txt')
      elif(filter=='tmlps'):
        sysCall('rm -f ' + imgDir + 'pic*.jpg')
      zm.deleteAllSeen()
  except Exception as e:
    prnt('deleteAll ' + str(e))
  eIdleLck.set()

#schreibe Liste (l) in die Datei (fi) 
def wrtLst(fi,l):
  with open(fi, 'w+') as f:
    f.seek(0,0)
    for r in l:
      f.write(r + '\n')
      #
    #
  #

def isCronTmlps():
  res = 'none'
  try:
    #prnt('isCronTmlps>')
    for ctm in cronTmlpsModDscr:
      f = '/home/pi/tmlps'+ctm+'.sh'
      if(res == 'none' and os.path.exists(f)):
        res = ctm
  except Exception as e:
    prnt('isCronTmlps ' + str(e))
    L1.red()
  #prnt('isCronTmlps< ' + res)
  return res;

def cronTmlps(ctm,on,fls):
  prnt('cronTmlps> ' + ctm + str(on))
  f = '/home/pi/tmlps'+ctm+'.sh'
  ccc = ''
  if(on):
    ccc = 'wget http://localhost:' + str(PORT) + '/foto=pic$DT.jpg=' + str(fls)
    with open(f, 'w+') as f:
      f.seek(0,0)
      f.write('#!/bin/bash\n')
      f.write('#\n')
      f.write('touch lock.txt\n')
      f.write('DT=$(date  +''%Y-%m-%d-%H-%M-%S'')\n')
      f.write(ccc + '\n')
      f.write('rm -f lock.txt')
      #
    #
    #sysCall('chmod +x ' + f)
  else:
    sysCall('rm -f ' + f)
  prnt('cronTmlps<')
  #

#callback fuer emails mit Betreff 'trigger'
def mailTrg(cmds):
  prnt('>mailTrg '+ str(cmds))
  img=imgDir
  prnt('<mailTrg ')
  return img
  #


def startUpdateHtmlPeriodic():
  prnt('>startUpdateHtmlPeriodic')
  t = threading.Thread(target=updateHtmlPeriodic)
  t.setDaemon(1)
  t.start()
  prnt('<startUpdateHtmlPeriodic')
  # 

def updateHtmlPeriodic():
  while(status >= ST_IDLE):
    updateHtml()
    time.sleep(UICYC*5)
  #

def updateHtml():
  global tmbL
  with updHtmlLck:
    ui = HtmlUi(fileRoot, 'ZenitPi')
    try:
      L1.ylw()
      tmbL = ui.create()
      del ui
      L1.off()
    except Exception as e:
      prnt('updateHtml ' + str(e))
      L1.red()
    gc.collect()
  #

#Thumbnails erstellen
def createTmb(fn):
  prnt('>createTmb ' + fn)
  splt = fn.split('/')
  ofn = tmbDir+splt[len(splt)-1]
  im = Image.open(fn)
  im.thumbnail((160,128), Image.ANTIALIAS)
  im.save(ofn, "JPEG")
  prnt('<createTmb ' + ofn)
  return ofn
  #
#

def streamVideo(cam):
  global abort, status
  while(abort != 1):
    lst = status
    status = ST_VID_STREAM
    try:
      _socket = socket.socket()
      _socket.bind(('0.0.0.0', 8000))
      _socket.listen(0)
      wrtTft('vlc tcp/h264://' + getIp() + ':8000')
      conn,addr = _socket.accept()
      wrtTft('connected ' + str(addr))
      f = conn.makefile('rb')
      try:
        if(0):
          cam.resolution = (640, 480)
          time.sleep(2)
          start = time.time()
          stream = io.BytesIO()
          # Use the video-port for captures...
          for foo in cam.capture_continuous(stream, 'jpeg', use_video_port=True):
            f.write(struct.pack('<L', stream.tell()))
            f.flush()
            stream.seek(0)
            f.write(stream.read())
            if abort==1:
              break
            stream.seek(0)
            stream.truncate()
          f.write(struct.pack('<L', 0))
        else:
          cam.resolution = (640, 480)
          time.sleep(2)
          cam.start_recording(f, format='h264')
          try:
            while(abort != 1):#jede sekunde auf abbruch testen
              wrtTft('send ' + str(addr))
              stream = io.BytesIO()
              cam.capture(stream, format='jpeg',use_video_port=True)
              stream.seek(0)
              img=pygame.image.load(stream,'jpeg')
              stream.close()
              showImg(img)
              #wrtTft('vlc tcp/h264://' + getIp() + ':8000')
              cam.wait_recording(1)
          finally:
            cam.stop_recording()
            cam.stop_preview()
      finally:
        f.close()
        conn.close()
        _socket.close()
    except Exception as e:
      prnt('streamVideo ' + str(e))
  status = lst
  #

def startStream():
  cam = picamera.PiCamera()
  try:
    streamVideo(cam)
  except:
    prnt('ouch')
  finally:
    cam.close()

def startStreamAsync():
  prnt('>startStreamAsync')
  t = threading.Thread(target=startStream)
  t.setDaemon(1)
  t.start()
  prnt('<startStreamAsync')

def createTmlps(pics, res, rmPic=False):
  global status
  prnt('>createTmlps status='+str(status))
  st = status
  status = ST_ENCODING
  L0.red()
  try:
    aspect = ggt(res[0],res[1])
    tmstmp = 'tmlps{:%Y-%m-%d-%H-%M-%S}'.format(datetime.now())
    ext='.avi'
    fn=vidDir+tmstmp+ext
    #fn1=vidDir+tmstmp+'_1fps'+ext
    #fn5=vidDir+tmstmp+'_5fps'+ext
    #fn15=vidDir+tmstmp+'_15fps'+ext
    #fn30=vidDir+tmstmp+'_30fps'+ext
    wrtTft('tmpls encoding ...')
    cnt = len(pics)
    lst = 'list.txt'
    #lst = imgDir + 'list.txt'
    sysCall('rm -f ' + lst)
    #mencoder mf:///home/www/img/pic*.jpg -mf w=800:h=600:fps=25:type=jpg -ovc lavc -lavcopts vcodec=mpeg4:mbd=2:trell -oac copy -o output.avi
    if(cnt == 0):
      sysCall('ls ' + imgDir + 'pic*.jpg > ' + lst)
      cnt = countLines(lst)
      #lst =/home/www/img/pic*.jpg 
    else:
      wrtLst(lst,pics)
    if(cnt > 0):
      prnt('start mencoder for ' + fn + ' with ' + lst + ' frames:' + str(cnt))
    if(cnt>12000):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=24 mf:///home/www/img/pic*.jpg')
      #
    elif(cnt>3000):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=15 mf:///home/www/img/pic*.jpg')
     #
    elif(cnt>500):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=10 mf:///home/www/img/pic*.jpg')
      #
    elif(cnt>20):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=5 mf:///home/www/img/pic*.jpg')
      #
    elif(cnt>0):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=1 mf:///home/www/img/pic*.jpg')
    #
    wrtTft('tmpls clean up ...')
    try:
      if(rmPic):
        #os.remove(imgDir + 'pic*.jpg')
        sysCall('rm -f ' + imgDir + 'pic*.jpg')
      #os.remove(imgDir + 'list.txt')
      sysCall('rm -f ' + lst)
    except Exception as e:
      prnt(str(e))
      L0.ylw()
  except  Exception as e:
    prnt('createTmlps' + str(e))
  L0.grn()
  status = st
  prnt('<createTmlps')
  return fn


def measureLight(camera):
  pixAverage = 0
  orig_res = camera.resolution
  orig_iso = camera.iso
  camera.resolution = (400, 300)
  camera.iso = 400
  with picamera.array.PiRGBArray(camera) as stream:
    #prnt("measureLight")
    camera.exposure_mode = 'auto'
    camera.awb_mode = 'auto'
    #camera.iso = 800
    camera.capture(stream, format='rgb')
    pixAverage = int(np.average(stream.array[...,1]))
  prnt("measureLight pixAverage=%i" % pixAverage)
  camera.resolution = orig_res
  camera.iso = orig_iso
  return pixAverage

def liveRec(cam,dur):
  global abort
  ts = time.time()
  tt = time.time()
  while((tt - ts) < dur and abort!=1):
    stream = io.BytesIO()
    cam.capture(stream, format='jpeg',use_video_port=True)
    stream.seek(0)
    img=pygame.image.load(stream,'jpeg')
    stream.close()
    showImg(img)
    if(checkDiskSpace()==0 or abort==1):
      break
    wrtTft(str((tt - ts)) + ' / ' + str(dur))
    cam.wait_recording(1)
    tt = time.time()
    #
  #
#ausloeser
def manuTrg(cam, fn='', fls=1, mode=0, sett=0):
  global nMod, nSet, F, status, abort, eIdleLck, lstFilesToSend
  eIdleLck.clear()
  prnt('>trigger mode='+ str(mode) + ' sett=' + str(sett) + ' fn=' + fn)
  if(checkDiskSpace()==0):
    return
  #
  #status = ST_FOTO_1#
  #if(hw):
  #  status = nMod + status#
  if(mode==0):
    readMS()
    mode = nMod + ST_FOTO_1#
    sett = nSet
  status = mode
  abort = 0
  L0.ylw()
  if(status == ST_FOTO_1 or status == ST_FOTO_2 or status == ST_FOTO_3):
    #einzelbild
    if(sett < 3):
      if(status == ST_FOTO_3):
        fn=('pic{:%Y-%m-%d-%H-%M-%S}.jpg').format(datetime.now())
      elif(fn == ''):
        fn=('pi{:%Y-%m-%d-%H-%M-%S}.jpg').format(datetime.now())
      #elif(fn=='yuv'):
      #prnt('capture ' + fn)
      if(fls==1):
        G.output(QFLS,1)
      try:
        cam.exif_tags['IFD0.Copyright'] = '(c) ' + zm.getAddr()
        cam.exif_tags['EXIF.UserComment'] = b'Zenit Foto + PI'
        cam.exif_tags['EXIF.Flash'] = str(fls)
        cam.resolution = (2592,1944)
        if(status==ST_FOTO_2):
          cam.capture(imgDir + fn, 'yuv')  
        else:
          cam.capture(imgDir + fn)
        F = imgDir + fn
      except Exception as e:
        #cam.close()
        prnt('manuTrg FOTO' + str(e))
      if(fls==1):
        G.output(QFLS,0)
      ctm = isCronTmlps()
      if(ctm != 'none' or status == ST_FOTO_3):
        lstFilesToSend.append(fn)
      elif(status == ST_FOTO_1):#nicht bei foto_2
        createTmb(imgDir + fn)
      #img=pygame.image.load(fn)
      #showImg(img)
      #prnt('click ' + str(sett))
    elif(sett==9):#stream
      status = ST_VID_STREAM
      streamVideo(cam)
    #
  elif(status == ST_VID_1280 or status == ST_VID_640):
    prnt('video ...')
    if(status == ST_VID_1280):
      cam.resolution = (1280,720)
    else:
      cam.resolution = (640,480)
    dur = camStt.getDur()
    prnt('start vid (' + str(cam.resolution) + ') for ' + str(dur))
    wrtTft('start vid (' + str(cam.resolution) + ') for ' + str(dur))
    #fn=vidDir+'piv{:%Y-%m-%d-%H-%M-%S}.mjpeg'.format(datetime.now())
    fn=vidDir+'piv{:%Y-%m-%d-%H-%M-%S}.h264'.format(datetime.now())
    cam.start_recording(fn)
    #cam.wait_recording(dur)
    liveRec(cam,dur)
    cam.stop_recording()
    prnt('... stop vid')
  elif(status >= ST_TMLPS_1 and status <= ST_TMLPS_4):
    prnt('tmlps start ...')
    prnt('rm old imgs')
    sysCall('rm -f '+imgDir+'pic*.jpg')
    cam.resolution = (1920,1080)
    cc = camStt.getCnt(status)
    cs = camStt.getPer(status)
    if(cs > 1500):
      cam.resolution = (1280,720)
    try:
      prnt('tmlps start ' +str(cc) + 'x ' + str(cs) + 's')
      tt = time.time()
      pics = []
      L0.red()
      #for i, filename in enumerate(cam.capture_continuous(imgDir+'pic{counter:05d}.jpg')):
      for i in range(cc):
        filename = imgDir+'pic%(counter)05d.jpg'%{'counter':i}
        G.output(QFLS,1)
        cam.capture(filename)
        G.output(QFLS,0)
        prnt('click ' + filename)
        pics.append(filename)
        img=pygame.image.load(filename)
        showImg(img)
        L0.ylw()
        camStt.save(fileRoot)
        if(cs > 0):
          #normales intervall
          wrtTft('tmlps ' + str(i+1) + '/' + str(cc) + ' itv=' + str(cs))
          #vom intervall die Dauer der letzten Aufnahme abziehen
          ncs = cs - (time.time() - tt)
          prnt('sleep ' + str(ncs))
          if(ncs > 0):
            time.sleep(ncs)
          tt = time.time()
          #
        else:
          #auf ITRG warten
          wrtTft('tmlps ' + str(i+1) + ': press trigger for next img. ' + str(status) + ' ' + str(abort))
          waitTrg()
          #
        if(i == cc or abort==1 or status==ST_EXIT or checkDiskSpace()==0):
          wrtTft('stop rec tmlps')
          prnt('tmlps stop/abort ' + str(i) + ' ' + str(abort))
          break
          #
        L0.red()
        #for continous
      L0.ylw()
      createTmlps(pics, cam.resolution, rmPic=True)
      del pics
      L0.grn()
      prnt('tmlps finish')
      #
    except Exception as e:
      L1.red()
      L0.red()
      prnt('ex TMLPS')
      prnt(str(e))
      raise
      #
    #
  elif(status == ST_MOTIONDETECT):
    #with picamera.PiCamera() as camera:
    with DetectMotion(cam) as output:
      cam.resolution = (800, 600)
      cam.iso = 800
      cam.drc_strength='high'
      cam.start_recording(
            '/dev/null', format='h264', motion_output=output)
      while(abort != 1):
        cam.wait_recording(30)
      cam.stop_recording()
  elif(status == ST_TMLPS_CRON):
    prnt('cron tmlps')
    cam.resolution = (2592,1944)#(1920,1080)
    per = camStt.getPer(status)#abstand zw. aufnahmen
    ctm = isCronTmlps()
    if(ctm != 'none'):
      #stop wenn lauft
      cronTmlps(ctm, False, 0)
      #if(G.input(I1) == 0):#nur film machen wenn knopf?
      #pics = []
      #fn = createTmlps(pics, cam.resolution, rmPic=False)
    else:
      #start
      cronTmlps(per, True, 0)
  else:
    prnt('unused mode ' + str(status))
    #
  cam.iso = 0
  status = ST_IDLE
  L0.grn()
  eIdleLck.set()
  prnt('<trigger')
  return F
  #manuTrg

#GPIO callback fuer Ausloeser
def trg_cllbck(ch):
  global dTrg,trg1,trg2,eTrgDwn,abort,cntTrgUp,cntTrgDwn,status
  readMS()
  prnt('>trg_cllbck')
  if(status > ST_EXIT):
    try:
      with trgLck:
        L0.ylw()
        st = G.input(ITRG)
        prnt('trg_cllbck ' + str(cntTrgUp) + ' ' + str(cntTrgDwn) + ' ' + str(ch) + ' ' + str(st) + ' dTrg ' + str(dTrg))
        if(ch == ITRG):
          prnt('ITRG event ' + str(st))
          if(st):
            if(1):
              cntTrgUp = cntTrgUp+1
              trg2 = time.time()
              dTrg = trg2-trg1
              prnt('up ITRG ' + str(dTrg))
              #eTrgDwn.clear()
              #if(status == ST_TMLPS_FREE):
              #  if(dTrg>5.0):
              #    prnt('dTrg ' + str(dTrg))
              #    abort = 1
            else:
              prnt('invalid trg up')
            #
          else:
            if(1):
              cntTrgDwn = cntTrgDwn+1
              prnt('down ITRG')
              trg1 = time.time()
              trg2 = 0
              dTrg = 0
              if (status == ST_IDLE or status == ST_TMLPS_CRON):
              #if (status == ST_IDLE):
                eTrgDwn.set()
              else:
                wrtTft('BUSY')
                prnt('skip trg edge due to status == ' + str(status))
            else:
              prnt('invalid trg down')
            #
          #
        else:
          prnt('wrong channel ' + str(ch))
          #
        #with lock
    except Exception as e:
      prnt('EXC trg_cllbck ' + str(e))
      L1.red()
      #print(e)
      #
    L0.grn()
  else:
    prnt('trg_cllbck, wrong status' + str(status))
  prnt('<trg_cllbck')
  #

#GPIO callback fuer HLT
def hlt_cllbck(ch):
  global dT,t1,t2,status,eTrgDwn,abort,status
  try:
    with hltLck:
      L0.ylw()
      st = G.input(ch)
      prnt('hlt_cllbck ' + str(ch) + ' ' + str(st) + ' status ' + str(status) + ' dT ' + str(dT))
      if(st == 0):#gedrueckt
        if(status == ST_PREVIEW):#in vorschau
          camStt.selNext()
        elif(status == ST_MENU):
          menu.sel()
        else:
          dT = 0
          t1 = time.time()
          threading.Timer(5, ledHalt, ()).start()
          threading.Timer(10, ledReboot, ()).start()
          threading.Timer(15, ledExit, ()).start()
        #
      else:# losgelassen
        if(status != ST_PREVIEW):
          t2 = time.time()
          if(t1 > 0.0):
            dT = t2-t1
            t1=0
            prnt('dT ' + str(dT))
            if(dT > 5.0):
              abort = 1
              status = ST_EXIT
              eTrgDwn.set()
              #
            elif(dT > 2.0 and status == ST_IDLE):
              swapWiFi()
            elif(dT > 1.0 and status == ST_IDLE):
              status = ST_MENU
              #
            #
          #
        #
      #with lock
    L0.grn()
  except Exception as e:
    prnt('EXC hlt_cllbck ' + str(e))
    L1.red()
    #print(e)
    #
  #

#GPIO callback fuer IN1 und IN2
def in_cllbck(ch):
  global eTrgDwn,abort,t3,t4,dT1,dT2,status
  try:
    with inLck:
      st = G.input(ch)
      prnt('>in_cllbck ' + str(ch) + ' ' + str(st) + ' dT ' + str(dT))
      prnt('IM'+str(nMod))
      prnt('IS'+str(nSet))
      #
      #iTrg = G.input(ITRG)
      #i1 = G.input(I1)
      #i2 = G.input(I2)
      #i3 = G.input(I3)
      #
      if(status > ST_PREVIEW):
        abort = 1
        #eTrgDwn.set()
        prnt('abort TMLPS...')
      else:
        if(st == 0):
          if(ch == I2):
            if(status == ST_PREVIEW):
              camStt.down()
            elif(status == ST_MENU):
              menu.down()
            elif(status == ST_IDLE):
              dT2 = 0
              t4 = 0
              t3 = time.time()
              threading.Timer(10, holdI2_10, ()).start()
              threading.Timer(5, holdI2_5, ()).start()
              #status = ST_HOLD_I2
            #
          elif(ch == I1):
            if(status == ST_PREVIEW):
              camStt.up()
            elif(status == ST_MENU):
              menu.up()
            elif(status == ST_IDLE):
              dT1 = 0
              t4 = 0
              t3 = time.time()
              threading.Timer(10, holdI1_10, ()).start()
              threading.Timer(5, holdI1_5, ()).start()
              #status = ST_HOLD_I1
              #
            #
          else:
            prnt('in_cllbck ' + str(ch))
        else:
          prnt('in_cllbck up')
          if(ch == I2):
            if(status == ST_IDLE):
              t4 = time.time()
              dT2 = t4-t3
              if(dT2>10.0):
                deleteAll()
                updateHtml()
                L1.off()
              elif(dT2>5.0):
                sendMailAsync()
              else:
                wrtTft('Keine Funktion')
              #status = ST_IDLE
          elif(ch == I1):
            if(status == ST_PREVIEW):
              camStt.up()
            elif(status == ST_IDLE):
              t4 = time.time()
              dT1 = t4-t3
              if(dT1>10.0):
                #
                #
                L0.grn()
                pics = []
                reso = (2592,1944)
                createTmlps(pics, reso)
                updateHtml()
              elif(dT1>1.0):
                showAllJpg()
                #playAllVid()
              else:
                wrtTft('Keine Funktion')
              #status = ST_IDLE
              #
            #
        prnt('end lock')
      #with lock
  except Exception as e:
    prnt('EXC in_clbck' + str(e))
    L1.red()
    #status = ST_IDLE
    #print(e)
    #
  prnt('<in_cllbck')
  #

def im_cllbck(ch):
  readMS()
  wrtMode()
  #
def is_cllbck(ch):
  readMS()
  wrtMode()
  #

#WiFi umschalten
def swapWiFi():
  global wifi
  #L1.red()
  if(wifi):
    wifi = 0
    sysCall('/home/pi/wifiDikam.sh')
  else:
    wifi = 1
    sysCall('/home/pi/wifiKa3ax.sh')
  #

def restartNetwork():
    asyncSysCall('/etc/init.d/networking restart')
  #

def checkTime():
  if(hasInet()):
    YY = datetime.now().date().year%100
    MM = datetime.now().date().month
    DD = datetime.now().date().day
    hh = datetime.now().time().hour
    mm = datetime.now().time().minute
    ss = datetime.now().time().second
    cmd = ('/home/pi/adjClk.sh ?? 0x%d 0x%d 0x%d 0x%d 0x%d 0x%d' % (DD,MM,YY,hh,mm,ss))
    prnt('set time ' + cmd)
    asyncSysCall(cmd)
  else:
    asyncSysCall('/home/pi/adjClk.sh set')


def waitTrg():
  global eTrgDwn
  prnt('waiting trg down ...')
  if(ESYNC):
    eTrgDwn.wait()
  else:
    G.wait_for_edge(ITRG,G.FALLING)
    #
  readMS()
  eTrgDwn.clear()
  prnt('... trg down')
  #

def diag():
  prnt('diag PI ' + str(G.RPI_REVISION) + ' V'  + str(G.VERSION))
  G.setmode(G.BOARD)
  for i in range(40):
    try:
      prnt('pin ' + str(i) + ' function ' +  str(G.gpio_function(i)))
    except:
      prnt('invalid pin ' + str(i))
      #
    #for
  #diag

def extern_trigger(_command):
  global LL
  fn = ''
  #foto=name.jpg=flash=iso=mode=effect=drc
  if(_command.find("foto=") >= 0):
    #prnt('extern_trigger 1')
    cmds = _command.split('=')
    flsCmd = 0
    drc = 'off'
    with picamera.PiCamera() as cam:
      prnt('extern_trigger cmds ' + str(cmds))
      try:
        if(len(cmds)>2):#flash
          if(len(cmds[2])>0):
            flsCmd = int(cmds[2])
        if(len(cmds)>3):#iso
          if(len(cmds[3])>0):
            cam.iso = int(cmds[3])
        if(len(cmds)>4):#mode
          if cmds[4] in camStt.ExpMod:
            cam.exposure_mode = cmd[4]
        if(len(cmds)>5):#effect
          if cmds[5] in camStt.ImgEff:
            cam.image_effect = cmd[5]
        if(len(cmds)>6):#drc
          if(len(cmds[6])>0):
            drc = cmds[6]
        if(len(cmds)>7):#drc
          if(len(cmds[7])>0):
            cam.exposure_compensation = int(cmds[7])
        cam.drc_strength=drc
        ll = measureLight(cam)
        l = (LL+ll)/2
        if(l < 20):
          if(l == 0):
            l = 1
          prnt('extern_trigger nacht')
          cam.framerate = Fraction(1, 4*l)
          time.sleep(2.0)
          cam.shutter_speed = 8000000/l
          #cam.shutter_speed = cam.exposure_speed
          cam.exposure_mode = 'off'
          g = cam.awb_gains
          cam.awb_mode = 'off'
          cam.awb_gains = g
          cam.iso = 600
          #
        elif(l > 120):
          cam.exposure_compensation = -6
        elif(l > 140):
          cam.exposure_compensation = -12
        time.sleep(3.0)
        LL = l
        prnt('extern_trigger ' + str(cam.framerate) + ' ' + str(cam.shutter_speed))
        fn = manuTrg(cam, cmds[1], fls=flsCmd, mode=ST_FOTO_1)
        cam.close()
      except Exception as e:
        #cam.close()
        prnt('ex:' + str(e))
      #
  return fn
  #

def getHtml():
  html='<html><head><title> ZenitPi </title> </head><body>CPU: ' + getCpuTemp() + ' <br>'
  files = os.listdir(tmbDir)
  #for root, dirs, files in os.walk(tmbDir):
  for name in files:
    html=html+str('<a href=\"./img/' + name + '\"><img src=\"./img/tmb/'+ name + '\" width=160 alt=\"' + name +  '\" name=\"' + name + '\"/></a>')
    prnt(name)
    #
    #
  html=html+'<br></body></html>'
  return html
  #

class DetectMotion(picamera.array.PiMotionAnalysis):
  def __init__(self, camera):
    super(DetectMotion, self).__init__(camera)
    self.cam = camera
    self.first=True
  def analyse(self, a):
    a = np.sqrt(
      np.square(a['x'].astype(np.float)) +
      np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
    # If there're more than 10 vectors with a magnitude greater
    # than 60, then say we've detected motion
    if (a > 50).sum() > 50:
      if(self.first):
        self.first = False
      else:
        asyncCapture(self.cam)


class MyRequestHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
  def do_GET(self):
    global LL
    prnt('do_GET>' + self.path)
    self.protocol_version='HTTP/1.1'
    self.send_response(200, 'OK')
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    html="<html><head><title> ZenitPi </title> </head><body>CPU: " + getCpuTemp() + " <br></body></html>"
    if(self.path.find("foto=") >= 0):
      #prnt('do_GET 1')
      fn = extern_trigger(self.path)
      updateHtml()
      #
    elif(self.path.find("tmlps=") >= 0):
      cmd = self.path.split('=')[1]
    else:
      prnt('do_GET else')
      try:
        html="<html> <head><title> ZenitPi </title> </head>"
        html=html+"<body>CPU: " + str(getCpuTemp()) + "<br>"
        html=html+"cmds:<br>"
        html=html+"http://" + getIp() + ":" + str(PORT) + "/foto=1<br>"
        html=html+"DRC:" + str(picamera.PiCamera.DRC_STRENGTHS) + "<br>"
        html=html+"AWB:" + str(picamera.PiCamera.AWB_MODES) + "<br>"
        html=html+"EFF:" + str(picamera.PiCamera.IMAGE_EFFECTS) + "<br>"
        html=html+"EXP:" + str(picamera.PiCamera.EXPOSURE_MODES) + "<br>"
        html=html+"MET:" + str(picamera.PiCamera.METER_MODES) + "<br>"
        html=html+"<br></body></html>"
        prnt(html)
      except Exception as ex:
        prnt('do_GET ' + str(ex))
    #html = getHtml()
    self.wfile.write(html)
    prnt('do_GET<')
  def do_POST(self):
    logging.error(self.headers)
    form = cgi.FieldStorage(
    fp=self.rfile,
    headers=self.headers,
    environ={'REQUEST_METHOD':'POST','CONTENT_TYPE':self.headers['Content-Type'],})
    for item in form.list:
      logging.error(item)
    SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

Handler = MyRequestHandler
HTTPD = SocketServer.TCPServer(("", PORT), Handler)
HTTPT = 0

def startHttpd():
  global PORT, HTTPD
  try:
    prnt('serving at port ' + str(PORT))
    HTTPD.serve_forever()
  except Exception as e:
    prnt('startHttpd exc ' + str(e))  

def startHttpdThrd():
  global HTTPT
  HTTPT = threading.Thread(target=startHttpd)
  HTTPT.setDaemon(1)
  HTTPT.start()

def init():
  global I1,I2,I3,Q1,Q2,Q3,Q4,QFLS,IS3,IS0,IS2,IS1,ITRG,IM2,IM1,IM3,IM0
  global screen, fnt, L0, L1, status, HTTPT
  #gpio
  prnt('init PI ' + str(G.RPI_REVISION) + ' V'  + str(G.VERSION))
  res = True
  G.setmode(G.BOARD)
  G.setup(I1,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I1, G.BOTH, callback=in_cllbck, bouncetime=100)
  G.setup(I2,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I2, G.BOTH, callback=in_cllbck, bouncetime=100)
  G.setup(I3,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I3, G.BOTH, callback=hlt_cllbck, bouncetime=100)
  G.setup(ITRG,G.IN,pull_up_down=G.PUD_UP)
  #G.add_event_detect(ITRG, G.FALLING)
  if(ESYNC):
    G.add_event_detect(ITRG, G.BOTH, callback=trg_cllbck, bouncetime=100)
    #
  G.setup(Qor, G.OUT)
  G.setup(Qur, G.OUT)
  G.setup(Qog, G.OUT)
  G.setup(Qug, G.OUT)
  G.setup(QFLS, G.OUT)
  G.setup(IS0,G.IN,pull_up_down=G.PUD_DOWN)
  #G.add_event_detect(IS0, G.BOTH, callback=is_cllbck, bouncetime=200)
  G.setup(IS1,G.IN,pull_up_down=G.PUD_DOWN)
  #G.add_event_detect(IS1, G.BOTH, callback=is_cllbck, bouncetime=200)
  G.setup(IS2,G.IN,pull_up_down=G.PUD_DOWN)
  #G.add_event_detect(IS2, G.BOTH, callback=is_cllbck, bouncetime=200)
  G.setup(IS3,G.IN,pull_up_down=G.PUD_DOWN)
  #G.add_event_detect(IS3, G.BOTH, callback=is_cllbck, bouncetime=200)
  G.setup(IM0,G.IN,pull_up_down=G.PUD_DOWN)
  G.add_event_detect(IM0, G.BOTH, callback=im_cllbck, bouncetime=200)
  G.setup(IM1,G.IN,pull_up_down=G.PUD_DOWN)
  G.add_event_detect(IM1, G.BOTH, callback=im_cllbck, bouncetime=200)
  G.setup(IM2,G.IN,pull_up_down=G.PUD_DOWN)
  G.add_event_detect(IM2, G.BOTH, callback=im_cllbck, bouncetime=200)
  G.setup(IM3,G.IN,pull_up_down=G.PUD_DOWN)
  G.add_event_detect(IM3, G.BOTH, callback=im_cllbck, bouncetime=200)
  #
  G.output((Qor,Qur,Qog,Qug,QFLS),0)
  prnt('IS'+str(G.input(IS0))+str(G.input(IS1))+str(G.input(IS2))+str(G.input(IS3)))
  prnt('IM'+str(G.input(IM0))+str(G.input(IM1))+str(G.input(IM2))+str(G.input(IM3)))
  #setup  display
  os.environ["SDL_VIDEODRIVER"]="fbcon"
  os.environ["SDL_FBDEV"]="/dev/fb1"
  pygame.init()
  screen = pygame.display.set_mode(SZ, 0, 32)
  #pygame.display.set_caption('ZPI')
  pygame.mouse.set_visible(0)
  screen.fill(GREEN)
  pygame.display.update()
  fnt = pygame.font.SysFont(None, 8)
  #zm.add_log(prnt)
  zm.add_observer(mailCllb)
  #check inet
  checkTime()
  #hdmi ausschalten
  sysCall('/usr/bin/tvservice -o')
  status = ST_IDLE
  if(G.input(I1) == 0 and G.input(I2) == 0):
    prnt('off')
    res = False
  else:
    startCheckMailPeriodic()
    #startUpdateHtmlPeriodic()
    updateHtml()
    startUpdateUiPeriodic()
    startHttpdThrd()
    rdFtpAuth()
  return res
  #init

def showImg(img):
  global screen
  #prnt('>showImg')
  img = img.convert()
  iH=img.get_height()
  iW=img.get_width()
  iF=iW/160
  iH=iH/iF
  iW=iW/iF
  img=pygame.transform.rotate(img,270)
  img=pygame.transform.scale(img,(iH,iW))
  h = (128-iH)/2
  w = (160-iW)/2
  screen.fill(BLUE)
  screen.blit(img, (h,w))
  pygame.display.update()
  #prnt('<showImg')
  #

def main(argv):
  global I1,I2,I3,Q1,Q2,Q3,Q4,QFLS,IS3,IS0,IS2,IS1,ITRG,IM2,IM1,IM3,IM0
  global screen,fnt,VERBOSE,L0,L1,mailTimer,status,eIdleLck,HTTPT
  try:
    opts, args = getopt.getopt(argv, 'vhi:')
    for opt, arg in opts:
      if(opt in ('v','-v')):
        print('is verbose')
        VERBOSE = 1
        #
      #if opt
    #for args
  except:
    print('args exception')
    sys.exit(2)
    #
  sysCall('mv ' + fileRoot+'log.txt ' + fileRoot+'logBefore' + UPDT + '.txt', log=False)
  if(init()):
    #diag()
    #
    try:
      wrtTft('start main PI ' + str(G.RPI_REVISION) + ' V'  + str(G.VERSION))
      #with picamera.PiCamera() as cam:
      wrtTft('starting...')
      screen.fill(BLUE)
      pygame.display.update()
      status = ST_IDLE
      eIdleLck.set()
      L0.grn()
      while(dT < 5):
        readMS()
        prnt('while dT ' + str(dT))
        try:
          #ctm = isCronTmlps()
          #if(ctm != 'none'):
          #  status = ST_TMLPS_CRON
          wrtMode()
          #wrtTft('wait trigger, mod=' + str(nMod) + ' set=' + str(nSet))
          waitTrg()
          if(os.path.exists('lock.txt')):
            wrtTft('Camera BUSY')
          else:
            cam = picamera.PiCamera()
            #cam.resolution = (2592,1944)
            cam.resolution = (160,128)
            if(status == ST_IDLE):
              prnt('ITRG ' + str(G.input(ITRG)))
              L0.ylw()
              #show preview
              cam.resolution = (160,128)
              cam.iso = 1000
              if((nMod+ST_FOTO_1) != ST_FOTO_2):#nur bei FOTO_2 die einstellungen behalten
                camStt.reset()
              #
              while(G.input(ITRG)==0):
                #while(eTrgDwn.isSet()):
                status=ST_PREVIEW
                camStt.use(cam)
                stream = io.BytesIO()
                cam.capture(stream, format='jpeg')
                stream.seek(0)
                img=pygame.image.load(stream,'jpeg')
                stream.close()
                del stream
                showImg(img)
                wrtTft(' ', live=1)
                #while preview
                L0.grn()
              cam.stop_preview()
              manuTrg(cam)#kann lange laufen
            #else:
            #  manuTrg(cam)
        except Exception as e:
          wrtTft('Exc preview: ' + str(e))
        finally:
          try:
            cam.close()
          except Exception as e:
            prnt(str(e))
        status = ST_IDLE
        updateHtml()
        prnt('end rec')
        gc.collect()
        #while
    except Exception as e:
      wrtTft('MAIN EXCEPTION! ' + str(e))
      print(e)
      time.sleep(5.0)
      #
  else:
    prnt('init failed')
  wrtTft('exit...')
  G.cleanup()
  status = ST_EXIT
  time.sleep(1.0)
  eIdleLck.wait()
  pygame.quit()
  HTTPD.shutdown()
  if(dT > 15.0):
    prnt('normal exit')
  elif(dT > 10.0):
    sysCall('reboot')
  elif(dT > 5.0):
    sysCall('halt')
  #main

if __name__ == "__main__":
    main(sys.argv[1:])
