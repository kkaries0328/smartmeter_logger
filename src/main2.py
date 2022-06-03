import configparser
import sys
import serial
import time
import datetime
import csv
#import slackweb
import logging
import shutil

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

from utils import *
import smtmeter_logger

if __name__=="__main__":
    config_file_path = "/home/pi/work/smartmeter_logger/config/smart_meter_config.ini"

    # 設定情報取得
    config_file = configparser.ConfigParser()
    config_file.read(config_file_path, "utf-8")
    
    broute_id = config_file.get("settings", "broute_id")
    broute_pw = config_file.get("settings", "broute_pw")

    # echonetlite_frame = config_file.get("echonetlite", "echonetlite_frame")
    echonetlite_frame = b"\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x01\xE7\x00"

    serial_device_name = config_file.get("device", "serial_device_name")
    baudrate = int(config_file.get("device", "baudrate"))

    # slack_webhook_url = config_file.get("slack", "slack_webhook_url")

    print("ロガーオブジェクト生成")
    smtmeterlogger = smtmeter_logger.SmtmeterLogger(serial_device_name, baudrate)

    print("アクティブスキャンシーケンス")
    d = smtmeterlogger.scan(broute_id, broute_pw)
    channel = d["Channel"]
    pan_id = d["Pan ID"]
    address = d["address"]

    print("PANA認証シーケンス")
    smtmeterlogger.pana_auth(broute_id, broute_pw, channel, pan_id, address)

    print("電力値取得")
    try:
        while True:
            dt, power = smtmeterlogger.get_power(echonetlite_frame, address)
            #text = f"Power: {power} W"
            #print(power)

            # print("ディスプレイ表示")
            smtmeterlogger.display_text(power)

            time.sleep(60)
        
    except KeyboardInterrupt:
        smtmeterlogger.close_display()
