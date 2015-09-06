#!/usr/bin/python
import pygame
import io
import os
import time
import picamera
import RPi.GPIO as G
import threading
import smtplib
import sys
import getopt
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
#from threading import Thread
#from threading import Timer
from subprocess import call, Popen, PIPE
from _htmlUi import HtmlUi
from _driveInfo import getDriveUse
from _driveInfo import getCpuTemp
from _driveInfo import getCpuUse
from _imap_gmail import ZenitMail
from watchdogdev import *

ESYNC=1#ausloeser wird mit threading.event synchronisiert
VERBOSE = 0#redet viel
LOGFILE = 1#redet viel in datei
MCYC = 60
UICYC = 1
status = -2
abort = 0
dT = 0
t1 = 0
t2 = 0
t3 = 0
t4 = 0
dT1 = 0
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
nMod = 0
nSet = 0
cntTrgUp = 0
cntTrgDwn = 0
zm = ZenitMail()
wd = 0
UPDT = ('{:%Y-%m-%d-%H-%M-%S}').format(datetime.now())
lastError = ''

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
modDscr = ['Foto Auto','Foto Semi','Zeitraffer ','Zeitraffer ','Zeitraffer ','Zeitraffer ','Zeitraffer ','Zeitraffer frei ','Video 1280  ','Video 1920  ']
modDscrShrt = ['F(A)','F(S)','Zeitraf. ','Zeitraf. ','Zeitraf. ','Zeitraf. ','Zeitraf. frei','Zeitraf. CRON ','V1280 ','V1920 ']
#                 0       1       2        3        4       5       6       7        8                9
cronTmlpsModDscr = ['1_min','5_min','15_min','30_min','1_std','3_std','6_std','11_uhr','1_std_9_18_uhr','3_std_9_18_uhr']

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
ST_TMLPS_1 = 22
ST_TMLPS_2 = 23
ST_TMLPS_3 = 24
ST_TMLPS_4 = 25
ST_TMLPS_FREE = 26
ST_TMLPS_CRON = 27
ST_VID_1280 = 28
ST_VID_1920 = 29
ST_VID_STREAM = 30

#fileRoot = '/home/pi/'
fileRoot = '/home/www/'
imgDir = fileRoot + 'img/'
tmbDir = imgDir + 'tmb/'
vidDir = fileRoot + 'vid/'

def setLastError(err):
  global lastError
  lastError = err

def prnt(text=''):
  with lock:
    if not text:
      text = 'invalid text?'
    if(VERBOSE):
      print(text)
    if(LOGFILE):
      #with logLck:
      with open(fileRoot+'log' + UPDT + '.txt', 'a') as f:
        f.write(('{:%Y-%m-%d-%H-%M-%S}').format(datetime.now()) + '\t' + getCpuTemp() + '\t' + str(threading.current_thread()) + '\t' + text + '\n')
  #prnt

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
    self.M = []
    self.M.append(['Bild','Film','<---'])
  def sel(self):
    prnt('menu selLvlUp')
    self.iLvl=self.iLvl+1
    self.iLvl=self.iLvl%len(self.M)    
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
    elif(st!=ST_TMLPS_FREE):
      t = self.Itv[st-ST_TMLPS_1+1]
    return t
    #
  def getCnt(self,st):
    cc = 50000
    if(st!=ST_TMLPS_FREE and st!=ST_TMLPS_CRON):
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
    elif(st == ST_TMLPS_FREE):
      res = self.getPer(st)#abstand zw. aufnahmen, sekunden oder trigger
    elif(st >= ST_TMLPS_1 and st < ST_TMLPS_FREE):
      res = self.getCnt(st)#anzahl bilder
    elif(st == ST_VID_1280 or st == ST_VID_1920):
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
    if(st == ST_TMLPS_FREE):
      if(self.Set == 0):
        s = ' TRG'
      else:
        s=s+' sek.'
    elif(st >= ST_TMLPS_1 and st < ST_TMLPS_FREE):
      s=s+'x'
    elif(st == ST_VID_1280 or st == ST_VID_1920):
      s=s+' sek.'
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
  def off(self):
    try:
      G.output((self.r,self.g),0)
    except Exception as e:
      prnt('L.off' + str(e))  
  def red(self):
    try:
      G.output((self.r,self.g),0)
      G.output(self.r,1)
    except Exception as e:
      prnt('L.red' + str(e))  
  def grn(self):
    try:
      G.output((self.r,self.g),0)
      G.output(self.g,1)
    except Exception as e:
      prnt('L.grn' + str(e))  
  def ylw(self):
    try:
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
  global L0,dT1
  prnt('holdI2_10 ' + str(dT1))
  if(dT1==0 and G.input(I2)==0):
    L1.red()
  #
def holdI1_5():
  global L0,dT1
  prnt('holdI1_10 ' + str(dT1))
  if(dT1==0 and G.input(I1)==0):
    L0.ylw()

def holdI2_5():
  global L0,dT1
  prnt('holdI2_10 ' + str(dT1))
  if(dT1==0 and G.input(I2)==0):
    L1.grn()
  #

def ledHalt():
  global L1,dT
  prnt('ledHalt ' + str(dT))
  if(dT==0 and G.input(I3)==0):
    L1.red()
  #
def ledReboot():
  global L1,dT
  prnt('ledReboot ' + str(dT))
  if(dT==0 and G.input(I3)==0):
    L1.ylw()
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
  global screen
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
    if((nMod+ST_FOTO_1) > ST_FOTO_2):
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
    text = menu.toString()
  elif(status > ST_FOTO_2 and status <= ST_VID_STREAM):
    if(status > ST_FOTO_2 and status < ST_VID_1280):
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
  txtsrfc = font.render(text, 1, pygame.Color(0,0,0), pygame.Color(255,255,255))
  txtsrfc=pygame.transform.rotate(txtsrfc,270)
  screen.blit(txtsrfc,pos)
  #
  pygame.display.update()
  #prnt('<wrtTft')
  #

def wrtMode():
  #
  text = ' '
  st = nMod+ST_FOTO_1
  readMS()
  if(st == ST_TMLPS_CRON):
    text = text + cronTmlpsModDscr[nSet%len(cronTmlpsModDscr)]
  elif(st >= ST_TMLPS_1 and st < ST_TMLPS_FREE):
    text = text + ' B, ' + str(camStt.getPer(st)) + ' T'
  else:
    text = camStt.toStrSet(9)
  text = modDscrShrt[nMod%len(modDscrShrt)] + text + '  '+str(nSet)
  wrtTft(text)
  #

def startUpdateUiPeriodic():
  prnt('>startUpdateUiPeriodic')
  t = threading.Thread(target=updateUiPeriodic)
  t.setDaemon(1)
  t.start()
  prnt('<startUpdateUiPeriodic')
  #

def updateUiPeriodic():
  global wd
  ii = 0
  while(status >= ST_IDLE):
    ii=ii+1
    try:
      if(wd == 0 or wd is None):
        prnt('start wd')
        sysCall('modprobe bcm2708_wdog')
        wd = watchdog('/dev/watchdog')
      elif(wd.get_time_left()<6):
        #prnt('wd.keep_alive')
        wd.keep_alive()
      if(status == ST_IDLE):
        if(isCronTmlps() != 'none'):
          #nachts die lichter aus
          hr = datetime.now().hour
          if(hr >= 19 or hr < 7):
            L0.off()
            L1.off()
          elif(ii>5):
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
    sysCall('mplayer -vf rotate=1 -vo fbdev2:/dev/fb1 -x 160 -y 90 -framedrop -zoom ' + vid)
    status = st

def sysCall(cmd):
  prnt('call> ' + cmd)
  try:
    output,error = Popen(cmd,stdout = PIPE, stderr=PIPE, shell=True).communicate()
    #call(cmd.split())
    #if(error is not None):
    #  prnt('call result ' + str(error))
    prnt(output)
  except Exception as e:
    L1.red()
    prnt('ex sysCall ' + str(e))
  #
  prnt('call< ' + cmd)

def asyncSysCall(cmd,async=False):
  prnt('asyncSysCall ' + cmd + ' async=' + str(async))
  if(async):
    t = threading.Thread(target=sysCall, args=(cmd,))
    t.start()
  else:
    sysCall(cmd)
  #

def mailCllb(addr, cmd):
  global abort
  try:
    to=[]
    to.append(addr)
    if(status == ST_IDLE or status == ST_VID_STREAM):
      L0.red()
      if(cmd[0].lower() == 'help'):
        zm.sendMail('Re: ' + cmd[0], _text='no help', _send_to=to)
      elif(cmd[0].lower() == 'trigger'):
        cam = picamera.PiCamera()
        fn = manuTrg(cam, hw=False)
        cam.close()
        att=[]
        #prnt('sende ' + fn)
        att.append(fn)
        zm.sendMail('Re: ' + cmd[0], _text='echo', _send_to=to, _files=att)
      elif(cmd[0].lower() == 'stream'):
        if(cmd[1].lower() == '0'):
          abort = 1
        else:
          startStreamAsync()
          zm.sendMail('Re: ' + cmd[0], _text='vlc tcp/h264://' + getIp() + ':8000', _send_to=to)
      L0.grn()
      #prnt('sollte mail senden an ' + addr)
    else:
      zm.sendMail('busy, try later', _text=':P', _send_to=to)
  except Exception as e:
    prnt(str(e))
    L1.red()
  #

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
  prnt('>startCheckMailPeriodic')
  t = threading.Thread(target=checkMailPeriodic)
  t.setDaemon(1)
  t.start()
  prnt('<startCheckMailPeriodic')
  # 

#alle MCYC Sekunden die emails abrufen
def checkMailPeriodic():
  while(status >= ST_IDLE):
    time.sleep(MCYC)
    #prnt('checkMailPeriodic')
    try:
      if(status == ST_IDLE or status == ST_VID_STREAM):
        L1.ylw()
        if(hasInet()):
          prnt('checkMailPeriodic abrufen')
          zm.getSubscribers()
          prnt('checkMailPeriodic fertig')
        else:
          restartNetwork()
    except:
      prnt('exc checkMailPeriodic')
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


def deleteAll(filter=''):
  with updUiLck:
    if(filter==''):
      wrtTft('alle Dateien loeschen...')
      sysCall('rm -f ' + imgDir +'pi*.jpg')
      sysCall('rm -f ' + tmbDir +'*.jpg')
      sysCall('rm -f ' + vidDir +'*.avi')
      sysCall('rm -f ' + vidDir +'*.h264')
      sysCall('rm -f ' + fileRoot +'*.txt')
    elif(filter=='tmlps'):
      sysCall('rm -f ' + imgDir + 'pic*.jpg')

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
    prnt(str(e))
    L1.red()
  #prnt('isCronTmlps< ' + res)
  return res;

def cronTmlps(ctm,on,cam):
  prnt('cronTmlps> ' + ctm + str(on))
  f = '/home/pi/tmlps'+ctm+'.sh'
  ccc = ''
  if(on):
    ccc = 'sudo raspistill -ISO %s -ex %s -awb %s -ifx %s -w %s -h %s -o /home/www/img/pic$DT.jpg' % (str(cam.iso),str(cam.exposure_mode),str(cam.awb_mode),str(cam.image_effect),str(cam.resolution[0]),str(cam.resolution[1]))
    with open(f, 'w+') as f:
      f.seek(0,0)
      f.write('#!/bin/bash\n')
      f.write('#\n')
      f.write('DT=$(date  +''%Y-%m-%d-%H-%M-%S'')\n')
      f.write(ccc + '\n')
      #
    #
    #sysCall('chmod +x ' + f)
  else:
    sysCall('rm -f ' + f)
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
  with updHtmlLck:
    ui = HtmlUi(fileRoot, 'ZenitPi')
    try:
      L1.ylw()
      ui.create()
      del ui
      L1.off()
    except Exception as e:
      prnt(str(e))
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
          cam.start_preview()
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
      prnt(str(e))
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
  lst = status
  status = ST_ENCODING
  L0.red()
  try:
    if(len(pics) > 0):
      wrtLst(imgDir+'list.txt',pics)
    aspect = '16/9'
    if(res[0]/res[1]<1.4):
      aspect = '4/3'
    tmstmp = 'tmlps{:%Y-%m-%d-%H-%M-%S}'.format(datetime.now())
    ext='.avi'
    fn=vidDir+tmstmp+ext
    fn1=vidDir+tmstmp+'_1fps'+ext
    fn5=vidDir+tmstmp+'_5fps'+ext
    fn15=vidDir+tmstmp+'_15fps'+ext
    fn30=vidDir+tmstmp+'_30fps'+ext
    prnt('start mencoder for ' + fn)
    wrtTft('tmpls encoding ...')
    if(len(pics)>12000):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=24 mf://@' + imgDir + 'list.txt')
      #
    elif(len(pics)>3000):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=15 mf://@' + imgDir + 'list.txt')
     #
    elif(len(pics)>500):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=10 mf://@' + imgDir + 'list.txt')
      #
    elif(len(pics)>20):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=5 mf://@' + imgDir + 'list.txt')
      #
    elif(len(pics)>0):
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn + ' -mf type=jpeg:fps=1 mf://@' + imgDir + 'list.txt')
    #
    else:
      sysCall('ls ' + imgDir + 'pic*.jpg > ' + imgDir + 'list.txt')
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn1 + ' -mf type=jpeg:fps=1 mf://@' + imgDir + 'list.txt')
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn5 + ' -mf type=jpeg:fps=5 mf://@' + imgDir + 'list.txt')
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn15 + ' -mf type=jpeg:fps=15 mf://@' + imgDir + 'list.txt')
      sysCall('mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:aspect=' + aspect + ':vbitrate=8000000 -vf scale='+str(res[0])+':'+str(res[1])+' -o ' + fn30 + ' -mf type=jpeg:fps=30 mf://@' + imgDir + 'list.txt')
    wrtTft('tmpls clean up ...')
    try:
      if(rmPic):
        #os.remove(imgDir + 'pic*.jpg')
        sysCall('rm -f ' + imgDir + 'pic*.jpg')
      #os.remove(imgDir + 'list.txt')
      sysCall('rm -f ' + imgDir + 'list.txt')
    except Exception as e:
      prnt(str(e))
      L0.ylw()
  except  Exception as e:
    prnt(str(e))
  L0.grn()
  status = lst
  prnt('<createTmlps')
  return fn


#ausloeser
def manuTrg(cam, hw=True):
  global nMod, nSet, F, status, abort
  readMS()
  prnt('>trigger '+ str(nMod) + ' ' + str(nSet))
  if(checkDiskSpace()==0):
    return
  #
  fn=''
  status = ST_FOTO_1#
  if(hw):
    status = nMod + status#
  abort = 0
  L0.ylw()
  if(status == ST_FOTO_1 or status == ST_FOTO_2):
    #einzelbild
    if(nSet < 3):
      fn=(imgDir+'pi{:%Y-%m-%d-%H-%M-%S}.jpg').format(datetime.now())
      prnt('capture ' + fn)
      G.output(QFLS,1)
      cam.exif_tags['IFD0.Copyright'] = 'zenitpi2@gmail.com'
      cam.exif_tags['EXIF.UserComment'] = b'Zenit Foto + PI'
      cam.resolution = (2592,1944)
      cam.capture(fn)
      G.output(QFLS,0)
      F = fn
      createTmb(fn)
      #img=pygame.image.load(fn)
      #showImg(img)
      prnt('click ' + str(nSet))
    elif(nSet==9):#stream
      status = ST_VID_STREAM
      streamVideo(cam)
    #
  elif(status == ST_VID_1280 or status == ST_VID_1920):
    prnt('video ...')
    if(status == ST_VID_1280):
      cam.resolution = (1280,720)
    else:
      cam.resolution = (1920,1080)
    dur = camStt.getDur()
    wrtTft('start vid (' + str(cam.resolution) + ') for ' + str(dur))
    #fn=vidDir+'piv{:%Y-%m-%d-%H-%M-%S}.mjpeg'.format(datetime.now())
    fn=vidDir+'piv{:%Y-%m-%d-%H-%M-%S}.h264'.format(datetime.now())
    cam.start_recording(fn)
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
      tt = time.time()
      #
    cam.stop_recording()
    prnt('... stop vid')
  elif(status >= ST_TMLPS_1 and status <= ST_TMLPS_FREE):
    prnt('tmlps start ...')
    prnt('rm old imgs')
    sysCall('rm -f '+imgDir+'pic*.jpg')
    cam.resolution = (1920,1080)
    cc = camStt.getCnt(status)
    cs = camStt.getPer(status)
    if(cs > 1500):
      cam.resolution = (1280,720)
    try:
      prnt('cont start ' +str(cc) + 'x ' + str(cs) + 's')
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
          prnt('tmlps stop/abort')
          break
          #
        L0.red()
        #for continous
      L0.ylw()
      fn = createTmlps(pics, cam.resolution, rmPic=True)
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
  elif(status == ST_TMLPS_CRON):
    prnt('cron tmlps')
    cam.resolution = (2592,1944)#(1920,1080)
    per = camStt.getPer(status)#abstand zw. aufnahmen
    ctm = isCronTmlps()
    if(ctm != 'none'):
      #stop wenn lauft
      cronTmlps(ctm, False, cam)
      if(G.input(I1) == 0):#nur film machen wenn knopf?
        pics = []
        fn = createTmlps(pics, cam.resolution)
    else:
      #start
      cronTmlps(per, True, cam)
  else:
    prnt('unused mode ' + str(status))
    #
  cam.iso = 0
  status = ST_IDLE
  L0.grn()
  prnt('<trigger')
  return fn
  #manuTrg

#GPIO callback fuer Ausloeser
def trg_cllbck(ch):
  global dTrg,trg1,trg2,eTrgDwn,abort,cntTrgUp,cntTrgDwn
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
              if(status == ST_TMLPS_FREE):
                if(dTrg>5.0):
                  abort = 1
            else:
              prnt('invalid trg up')
            #
          else:
            if(1):
              cntTrgDwn = cntTrgDwn+1
              prnt('down ITRG')
              trg1 = time.time()
              dTrg = 0
              if (status == ST_IDLE or status == ST_TMLPS_FREE):
                eTrgDwn.set()
              else:
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
  global dT,t1,t2,status,eTrgDwn,abort
  try:
    with hltLck:
      L0.ylw()
      st = G.input(ch)
      prnt('hlt_cllbck ' + str(ch) + ' ' + str(st) + ' status ' + str(status) + ' dT ' + str(dT))
      if(st == 0):#gedrueckt
        if(status == ST_PREVIEW):#in vorschau
          camStt.selNext()
        elif(status == ST_MENU):
          menu.selLvlUp()
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
  global eTrgDwn,abort,t3,t4,dT1,status
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
        prnt('abort TMLPS...')
      else:
        if(st == 0):
          if(ch == I2):
            if(status == ST_PREVIEW):
              camStt.down()
            elif(status == ST_IDLE):
              dT1 = 0
              t3 = time.time()
              threading.Timer(10, holdI2_10, ()).start()
              threading.Timer(5, holdI2_5, ()).start()
              #status = ST_HOLD_I2
            #
          elif(ch == I1):
            if(status == ST_PREVIEW):
              camStt.up()
            elif(status == ST_IDLE):
              dT1 = 0
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
              dT1 = t4-t3
              if(dT1>10.0):
                deleteAll()
                updateHtml()
                L1.off()
              elif(dT1>5.0):
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
              elif(dT1>5.0):
                playAllVid()
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
  #if(hasInet()):
  #  L1.grn()
  #else:
  #  L1.ylw()
  #time.sleep(1)
  #L1.off()
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

def init():
  global I1,I2,I3,Q1,Q2,Q3,Q4,QFLS,IS3,IS0,IS2,IS1,ITRG,IM2,IM1,IM3,IM0
  global screen, fnt, L0, L1, status
  #gpio
  prnt('init PI ' + str(G.RPI_REVISION) + ' V'  + str(G.VERSION))
  res = True
  G.setmode(G.BOARD)
  G.setup(I1,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I1, G.BOTH, callback=in_cllbck, bouncetime=50)
  G.setup(I2,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I2, G.BOTH, callback=in_cllbck, bouncetime=50)
  G.setup(I3,G.IN,pull_up_down=G.PUD_UP)
  G.add_event_detect(I3, G.BOTH, callback=hlt_cllbck, bouncetime=50)
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
  zm.add_log(prnt)
  zm.add_observer(mailCllb)
  #check inet
  checkTime()
  status = ST_IDLE
  if(G.input(I1) == 0 and G.input(I2) == 0):
    prnt('off')
    res = False
  else:
    startCheckMailPeriodic()
    #startUpdateHtmlPeriodic()
    updateHtml()
    startUpdateUiPeriodic()
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
  global screen,fnt,VERBOSE,L0,L1,mailTimer,status
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
      L0.grn()
      while(dT < 5):
        readMS()
        prnt('while dT ' + str(dT))
        try:
          wrtMode()
          #wrtTft('wait trigger, mod=' + str(nMod) + ' set=' + str(nSet))
          waitTrg()
          cam = picamera.PiCamera()
          #cam.resolution = (2592,1944)
          cam.resolution = (160,128)
          cam.start_preview()
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
          pass
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
  #screen.fill(WHITE)
  time.sleep(1.0)
  pygame.quit()
  if(dT > 15.0):
    prnt('normal exit')
  elif(dT > 10.0):
    sysCall('reboot')
  elif(dT > 5.0):
    sysCall('halt')
  if(wd != 0):
    wd.magic_close()
  #main

if __name__ == "__main__":
    main(sys.argv[1:])
