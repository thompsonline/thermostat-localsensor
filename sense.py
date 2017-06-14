#!/usr/bin/env python

import time
import logging
import logging.handlers

import ConfigParser
import os
import sys
import MySQLdb
import pywapi

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

config = ConfigParser.ConfigParser()
config.read(dname+"/config.txt")

LOG_LOGFILE = config.get('logging', 'logfile')
logLevelConfig = config.get('logging', 'loglevel')
if logLevelConfig == 'info':
    LOG_LOGLEVEL = logging.INFO
elif logLevelConfig == 'warn':
    LOG_LOGLEVEL = logging.WARNING
elif logLevelConfig ==  'debug':
    LOG_LOGLEVEL = logging.DEBUG

LOGROTATE = config.get('logging', 'logrotation')
LOGCOUNT = int(config.get('logging', 'logcount'))

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LOGLEVEL)
handler = logging.handlers.TimedRotatingFileHandler(LOG_LOGFILE, when=LOGROTATE, backupCount=LOGCOUNT)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class MyLogger(object):
        def __init__(self, logger, level):
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

MYSQL_DATABASE_USER = config.get('main','mysqlUser')
MYSQL_DATABASE_PASSWORD = config.get('main','mysqlPass')
MYSQL_DATABASE_DB = config.get('main','mysqlDatabase')
MYSQL_DATABASE_HOST = config.get('main','mysqlHost')
MYSQL_DATABASE_PORT = int(config.get('main','mysqlPort'))

MODULEID = config.get('main', 'moduleID')
MODULENAME = config.get('main', 'moduleName')

WEB_WEATHER = config.getboolean('main','NOAAWeather')
if WEB_WEATHER:
    WEATHER_ID = config.get('main','NOAACode')

OUTSIDE_ID = config.get('main','WeatherModuleID')

if __name__ == "__main__":

   import time
   import BME280
   import pigpio

   pi = pigpio.pi()

   if not pi.connected:
      exit(0)

   s = BME280.sensor(pi, interface=BME280.SPI)

   logger.info("Starting local sensor")

   cycleCount = 5

   while True:
      t, p, h = s.read_data(BME280.FARENHEIT, BME280.INHG)
      print("h={:.2f} p={:.1f} t={:.2f}".format(h, p/100.0, t))

      try:
        conn = MySQLdb.connect(host=MYSQL_DATABASE_HOST, user=MYSQL_DATABASE_USER, passwd=MYSQL_DATABASE_PASSWORD, db=MYSQL_DATABASE_DB)
        
        cursor = conn.cursor()
        cursor.execute("INSERT INTO SensorData SET location='%s', moduleID=%s, temperature=%f, humidity=%f, light=0, occupied=0"% (MODULENAME, MODULEID, round(t,1), round(h,2)))
        conn.commit()

        if cycleCount >= 5:
          cycleCount = 0
          # Get the outside weather and log it
          logger.info("Getting outside weather")
          weatherDict = pywapi.get_weather_from_noaa(WEATHER_ID)
          #print(weatherDict)
          temp_f = weatherDict['temp_f']
          humid = weatherDict['relative_humidity']

          cursor.execute("INSERT SensorData SET moduleID=%s, location='outside', temperature=%f, humidity=%f "%(OUTSIDE_ID,round(float(temp_f),1), round(float(humid),2)))

          conn.commit()

        cursor.close()
        conn.close()

        cycleCount = cycleCount + 1
      except Exception as err:
        logger.error("Error %s" % (err))

      time.sleep(60)

   s.cancel()

   pi.stop()

   logger.info ("Local sensor stopped")
