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
    self.logCllBks = []
    self.auth = []
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
    self.log(l)
    self.frma = l[0].rstrip()
    self.pswd = l[1].rstrip()
    self.toa = l[2].rstrip()
    for ln in l:
      self.uniqAppend(self.auth,ln.rstrip())
  def getAddr(self):
    return self.frma
    #
  def uniqAppend(self, lst, ln):
    if(ln in lst):
      self.log('X ' + ln)
    elif(len(ln)<5):
      self.log('invalid ' + ln)
    else:
      lst.append(ln)
    #
  def rdLst(self):
    l = []
    try:
      with open('recv.txt', 'r') as f:
        ll = list(f)
        f.close()
      self.log(ll)
      for ln in ll:
        self.uniqAppend(l,ln.rstrip())
    except:
      self.log('exc rdLst')
    return l
    #
  def wrtLst(self, _lst):
    try:
      call(['rm','recv.txt'])
    except:
      self.log('exc wrtLst')
    with open('recv.txt', 'w+') as f:
      f.seek(0,0)
      for r in _lst:
        f.write(r + '\n')
  #
  def createMsg(self, _send_to, _subj, _text=None, _files=None):
    self.log('createMsg>')
    toa = self.toa
    self.log('1 ')
    msg = MIMEMultipart()
    msg['From'] = self.frma
    self.log('2 ')
    for r in _send_to:
      self.log(r)
      toa += (',' + r.rstrip())
      #
    self.log(toa)
    msg['To'] = toa
    self.log('3 ')
    msg['Date'] = formatdate(localtime = True)
    #self.log('4 ')
    msg['Subject'] = _subj
    #self.log('5 ')
    if (_text != None):
      msg.attach( MIMEText(_text) )
    self.log('6 ')
    if(_files != None):
      self.log('add attachments ... ')
      for f in _files:
        self.log(' + ' + f)
        ext = f.split('.')
        self.log(str(ext))
        nm = f.split('/')
        self.log(str(nm))
        if(len(ext)>0):
          ex = ext[len(ext)-1]
          if (ex == 'jpg' or ex == 'png'):
            self.log('attach MIMEImage')
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
    else:
      self.log('no attachment')
    return msg
    #
  def sendMail(self, _subj, _text=None, _send_to=None, _files=None):
    self.log('sendMail ' + _subj)
    if(_send_to is None):
      _send_to = self.rdLst()
      #
    _send_to.append(self.toa)
    try:
      self.log('createMsg ')
      msg = self.createMsg(_send_to, _subj, _text, _files)
      usr = self.frma
      pwd = self.pswd
      self.log('create server obj ')
      server = smtplib.SMTP('smtp.gmail.com:587')
      self.log('start tls ')
      server.starttls()
      self.log('login ')
      server.login(usr,pwd)
      self.log('send ' + str(_send_to))
      server.sendmail(usr, _send_to, msg.as_string())
      self.log('quit ')
      server.quit()
      self.log('sent')
    except Exception as ex:
      self.log(str(ex))
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
    sendInstantReply = False
    instantReply = ''
    iRcvs = []
    self.log('old list:')
    for r in L:
      self.log(r)
      #
    self.log('open imap')
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(self.frma, self.pswd)
    self.log('list...')
    mail.list()
    # 
    mail.select("inbox")
    typ, searchData = mail.search(None, _rule)
    self.log('typ='+str(typ))
    self.log('searchData='+str(searchData))
    for num in searchData[0].split():
      result, data = mail.fetch(num,'(RFC822)')
      self.log('result='+str(result))
      if(_del):
        mail.store(num, '+FLAGS', '\\Deleted')
        mail.expunge()
        continue
      if(data == None):
        break
      raw_email = data[0][1]
      #self.log('raw='+str(raw_email))
      email_message = email.message_from_string(raw_email)
      frmN,frmA = email.utils.parseaddr(email_message['From'])
      sbj = email_message['Subject']
      self.log(frmA + ' ' + sbj)
      frmA = frmA.rstrip()
      cmd = sbj.split()
      if(frmA in self.auth):
        if(sbj.lower() == 'subscribe'):
          self.uniqAppend(L,frmA)
          #
        elif(sbj.lower() == 'unsubscribe'):
          if((frmA in L)):
            self.log('< ' + frmA + str(L))
            L.remove(frmA)
            #
          #
        elif(len(cmd)>1 and cmd[0].lower() == 'trigger'):
          self.log('mail cmd ' + str(cmd))
          rcvs.append(frmA)
          cmds.append(cmd)
          callobs = 1
          #
        elif(len(cmd)>1 and cmd[0].lower() == 'help'):
          self.log('mail cmd ' + str(cmd))
          rcvs.append(frmA)
          cmds.append(cmd)
          callobs = 1
          #
        elif(len(cmd)>1 and cmd[0].lower() == 'stream'):
          self.log('mail cmd ' + str(cmd))
          rcvs.append(frmA)
          cmds.append(cmd)
          callobs = 1
          #
        else:
          #invalid command
          iRcvs.append(frmA)
          sendInstantReply = True
          instantReply = 'invalid cmd'
      else:
        self.log('invalid sender ' + frmA)
      #
    mail.close()
    mail.logout()
    self.log('list before write:')
    for r in L:
      if(len(r) < 5):
        L.remove(r)
      else:
        self.log(r)
      #
    self.wrtLst(L)
    if(callobs):
      for i in range(len(rcvs)):
        self.call_observers(rcvs[i], cmds[i])
    #
    if(sendInstantReply):
      self.sendMail(instantReply, _text=instantReply, _send_to=iRcvs)
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
  def add_log(self, cllbk):
    self.logCllBks.append(cllbk)
    #
  def log(self, txt):
    for cllbk in self.logCllBks:
      cllbk(txt)

#zm = ZenitMail()
#zm.checkInbox()
#zm.getSubscribers()
#zm.deleteAllSeen()

