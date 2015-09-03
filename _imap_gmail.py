import imaplib
import smtplib
import email
import sys
import time
from datetime import datetime
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
from email.MIMEBase import MIMEBase
from email.utils import COMMASPACE, formatdate
from array import array
from subprocess import call
from threading import Thread

VERBOSE = 1

def prnt(text):
  if(VERBOSE and text):
    print(text)

class ZenitMail():
  def __init__(self):
    self.observers = []
    self.frma = ''
    self.pswd = ''
    self.toa = ''
    self.rdAuth()
    #
  def rdAuth(self):
    l = []
    with open('pass.txt', 'r') as f:
      l = list(f)
      f.close()
    prnt(l)
    self.frma = l[0]
    self.pswd = l[1]
    self.toa = l[2]
  def uniqAppend(self, list, ln):
    if(ln in list):
      prnt('X ' + ln)
    elif(len(ln)<5):
      prnt('invalid ' + ln)
    else:
      list.append(ln)
    #
  def rdLst(self):
    l = []
    try:
      with open('recv.txt', 'r') as f:
        ll = list(f)
        f.close()
      prnt(ll)
      for ln in ll:
        self.uniqAppend(l,ln.rstrip())
    except:
      prnt('exc rdLst')
    return l
    #
  def wrtLst(self, _lst):
    try:
      call(['rm','recv.txt'])
    except:
      prnt('exc wrtLst')
    with open('recv.txt', 'w+') as f:
      f.seek(0,0)
      for r in _lst:
        f.write(r + '\n')
  #
  def createMsg(self, _send_to, _subj, _text=None, _files=None):
    toa = self.toa
    msg = MIMEMultipart()
    msg['From'] = self.frma
    for r in _send_to:
      toa += (',' + r.rstrip())
      #
    prnt(toa)
    msg['To'] = toa
    #prnt('3 ')
    msg['Date'] = formatdate(localtime = True)
    #prnt('4 ')
    msg['Subject'] = _subj
    #prnt('5 ')
    if (_text != None):
      msg.attach( MIMEText(_text) )
    prnt('6 ')
    prnt('add attachments ... ')
    if(_files != None):
      for f in _files:
        prnt(' + ' + f)
        ext = f.split('.')
        prnt(ext)
        nm = f.split('/')
        prnt(nm)
        if(len(ext)>0):
          ex = ext[len(ext)-1]
          if (ex == 'jpg' or ex == 'png'):
            msg.attach(MIMEImage(file(f).read()))
          else:
            msg.attach( MIMEText(f) )
            att = MIMEBase('application', 'octet-stream')
            att = MIMEBase('application', _subtype=ext[len(ext)-1])
            att.set_payload(file(f).read())
            att.add_header('Content-Disposition', 'attachment', filename=nm[len(nm)-1])
            msg.attach(att)
          #
        #
      #
    return msg
    #
  def sendMail(self, _subj, _text=None, _send_to=None, _files=None):
    prnt('sendMail ' + _subj)
    if(_send_to is None):
      _send_to = self.rdLst()
      #
    _send_to.append(self.toa)
    try:
      prnt('createMsg ')
      msg = self.createMsg(_send_to, _subj, _text, _files)
      usr = self.frma
      pwd = self.pswd
      prnt('create server obj ')
      server = smtplib.SMTP('smtp.gmail.com:587')
      prnt('start tls ')
      server.starttls()
      prnt('login ')
      server.login(usr,pwd)
      prnt('send ' + str(_send_to))
      server.sendmail(usr, _send_to, msg.as_string())
      prnt('quit ')
      server.quit()
      prnt('sent')
    except Exception as ex:
      prnt(ex)
      #
    del _send_to
    #sendMail
  def getSubscribers(self):
    return self.checkInbox('UNSEEN')
  def deleteAllSeen(self):
    return self.checkInbox(_rule='SEEN', _del=True)  
  def checkInbox(self, _rule='UNSEEN', _del=False):
    L=[]
    L=self.rdLst()
    callobs = 0
    frmA = ''
    rcvs = []
    cmds = []
    prnt('old list:')
    for r in L:
      prnt(r)
      #
    prnt('open imap')
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(self.frma, self.pswd)
    prnt('list...')
    mail.list()
    # 
    mail.select("inbox")
    typ, searchData = mail.search(None, _rule)
    prnt('typ='+str(typ))
    prnt('searchData='+str(searchData))
    for num in searchData[0].split():
      result, data = mail.fetch(num,'(RFC822)')
      prnt('result='+str(result))
      if(_del):
        mail.store(num, '+FLAGS', '\\Deleted')
        mail.expunge()
        continue
      if(data == None):
        break
      raw_email = data[0][1]
      #prnt('raw='+str(raw_email))
      email_message = email.message_from_string(raw_email)
      frmN,frmA = email.utils.parseaddr(email_message['From'])
      sbj = email_message['Subject']
      prnt(frmA + ' ' + sbj)
      frmA = frmA.rstrip()
      cmd = sbj.split()
      if(sbj.lower() == 'subscribe'):
        self.uniqAppend(L,frmA)
        #
      elif(sbj.lower() == 'unsubscribe'):
        if((frmA in L)):
          prnt('< ' + frmA + str(L))
          L.remove(frmA)
          #
        #
      elif(len(cmd)>1 and cmd[0].lower() == 'trigger'):
        prnt('click ' + str(cmd))
        rcvs.append(frmA)
        cmds.append(cmd)
        callobs = 1
        #
      elif(len(cmd)>1 and cmd[0].lower() == 'help'):
        prnt('click ' + str(cmd))
        rcvs.append(frmA)
        cmds.append(cmd)
        callobs = 1
        #
      #
    mail.close()
    mail.logout()
    prnt('list before write:')
    for r in L:
      if(len(r) < 5):
        L.remove(r)
      else:
        prnt(r)
      #
    self.wrtLst(L)
    if(callobs):
      for i in range(len(rcvs)):
        self.call_observers(rcvs[i], cmds[i])
    #
    del L
    del rcvs
    del cmds
    #return L
    #
  def add_observer(self, cllbk):
      self.observers.append(cllbk)
    #
  def call_observers(self, addr, cmd):
      for cllbk in self.observers:
        cllbk(addr, cmd)
    #

#zm = ZenitMail()
#zm.checkInbox()

