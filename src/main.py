#!/usr/bin/env python
# -*- coding: utf-8 -*-

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

import configparser
import sys
import serial
import time
import datetime
import csv
import slackweb
import logging
import shutil

from utils import *
import echonet_comm

config_file_path = "/home/pi/work/smartmeter_logger/config/smart_meter_config.ini"
echonetlite_frame = b"\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x01\xE7\x00"

# ロガー設定
formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='../log/logger.log', level=logging.DEBUG, format=formatter)

# 設定情報取得
config_file = configparser.ConfigParser()
config_file.read(config_file_path, "utf-8")
broute_id = config_file.get("settings", "broute_id")
broute_pw = config_file.get("settings", "broute_pw")
slack_webhook_url = config_file.get("slack", "slack_webhook_url")

# SS1306初期設定
# setting some variables for our reset_pin etc...
RESET_PIN = digitalio.DigitalInOut(board.D4)
# Very Important... This lets py-gaugette "know" what pins to use in order to reset the display
i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(DISP_WIDTH, DISP_HEIGHT, i2c, addr=DEVICE_ADR)
# clear display
oled.fill(0)
oled.show()
# Load default font.
font = ImageFont.load_default()

# シリアルポート初期化
# 受信のtimeoutは60秒
ser = serial.Serial("/dev/ttyS0", 115200, timeout=10)

# アクティブスキャンシーケンス
d = echonet_comm.scan(ser, broute_id, broute_pw)
channel = d["Channel"]
pan_id = d["Pan ID"]
address = d["address"]

# PANA認証シーケンス
echonet_comm.pana_auth(ser, broute_id, broute_pw, channel, pan_id, address)

# 瞬間電力量取得シーケンス
try:
    while True:
        l = echonet_comm.get_power(ser, echonetlite_frame, address)
        logging.info(str(l[0]) + ", " +str(l[1]))

        # csvファイルに書き込み
        # with open("/home/pi/work/smartmeter_logger/data/power.csv", "a") as f:
        #     writer = csv.writer(f)
        #     writer.writerow(l)

        # ディスク使用率をチェック
        # free_disk = int(shutil.disk_usage("/").free/1024/1024)

        ## TODO: SSLのモジュールが入っていないので、httpsでの通信ができず、slackに送れない。
        ## 結構根っこから環境を変えないといけないっぽい(詳細は下記URL参照)ので、slackに送る機能は一時保留とする。
        ## https://www.secat-blog.net/wordpress/python3-cannot-install-numpy-by-pip-fix/
        ## -> 仮想環境にSSL環境を入れるところでつまずいたので、環境の仮想化をやめた。
        ##    デフォルトのpython環境にはSSLモジュールがはいっていたので問題は解決。
        # slack = slackweb.Slack(url=slack_webhook_url)
        # message = "時刻: "+l[0]+", 瞬時電力量: "+str(l[1])+"W, ディスク残容量: "+str(free_disk)+"MB"
        # #message = "時刻: "+l[0]+", 瞬時電力量: "+str(l[1])+"W"
        # slack.notify(text=message)

        # create blank image for drawing
        image = Image.new("1", (oled.width, oled.height))
        draw = ImageDraw.Draw(image)
        # Draw Some Text
        text = f"Power: {l[1]} W"
        (font_width, font_height) = font.getsize(text)
        #(font_width, font_height) = (100, 50)
        draw.text(
            (oled.width // 2 - font_width // 2, oled.height // 2 - font_height // 2),
            text,
            font=font,
            fill=255,
            )

        # Display image
        oled.image(image)
        oled.show()

        time.sleep(60)

except KeyboardInterrupt:
    ser.close()
    #Clear display
    close_display(oled)
