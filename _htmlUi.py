#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime
from PIL import Image

VERBOSE = 0

def prnt(text):
  if(VERBOSE and text):
    print(text)


def createTmb(fn):
  prnt('>createTmb ' + fn)
  im = Image.open(fn)
  im.thumbnail((160,128), Image.ANTIALIAS)
  im.save(outfile, "JPEG")
  prnt('<createTmb')
  #

class HtmlUi:
  def __init__(self, wwwPath, title):
    self.www = wwwPath
    self.title = title
    #
  def writeIndex(self,text):
    with open(self.www + '/index.html', 'w') as f:
      f.write("<html><head><title>" + self.title + "</title></head><body>")
      f.write(text)
      f.write("</body><html>")
    #
  def create(self):
    prnt('create')
    with open(self.www + '/index.html', 'w') as f:
      f.write("<html><head><title>" + self.title + "</title></head><body>\n")
      f.write(str(datetime.now()) + ' img:<br>\n')
      for root, dirs, files in os.walk(self.www+'img/tmb'):
        for name in files:
          f.write('<a href=\"./img/' + name + '\"><img src=\"./img/tmb/'+ name + '\" width=160 alt=\"' + str(time.time()) +  '\" name=\"' + name + '\"/></a>\n')
          prnt(name)
          #
      f.write('<br>\n')
      f.write('video:<br>\n')
      #for root, dirs, files in os.walk(self.www+'vid'):
      files = os.listdir(self.www+'vid')
      if 1:
        for name in files:
          #f.write('<video width="320" height="240" controls><source src=\"./vid/' + name + '\" type=\"video/h264\">Your browser does not support the video tag.</video>\n')
          f.write('<a href=\"./vid/' + name + '\">' + name + '</a><br>\n')
          #print(name)
          #
      f.write('<br>\n')
      f.write('log:<br>\n')
      #for root, dirs, files in os.walk(self.www):
      files = os.listdir(self.www)
      if 1:
        for name in files:
          f.write('<a href=\"' + name + '\">' + name + '</a><br>\n')
          #print(name)
          #
      f.write("</body><html>")
    #self.writeIndex(t)
    #

if __name__ == "__main__":
  # skript geht los
  ui = HtmlUi('/home/www/', 'ZenitPi')
  ui.create()


#<object data="Video.mpg" type="video/mpeg" align="left"></object>
