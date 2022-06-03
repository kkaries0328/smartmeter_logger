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

##### ToDo
# - ロギング機能の実装
# - ディスプレイ表示を作り込み

class SmtmeterLogger():
    def __init__(self, serial_device_name, baudrate):
        # シリアルポート初期化
        self.ser = serial.Serial(serial_device_name, baudrate, timeout=10)
        self.oled = self._init_display()
        self.font1 = ImageFont.truetype("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 14)
        # ロガー設定
        # formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # logging.basicConfig(filename='../log/logger.log', 
        #                     level=logging.DEBUG, 
        #                     format=formatter)

    def _init_display(self):
        # ディスプレイ初期設定
        device_adr = 0x3C
        disp_width = 128
        disp_height = 64
        # setting some variables for our reset_pin etc...
        RESET_PIN = digitalio.DigitalInOut(board.D4)
        # Very Important... This lets py-gaugette "know" what pins to use in order to reset the display
        i2c = board.I2C()
        oled = adafruit_ssd1306.SSD1306_I2C(disp_width, disp_height, i2c, addr=device_adr)
        oled.fill(255)
        oled.show()
        time.sleep(5)
        oled.fill(0)
        oled.show()
        return oled


    def display_text(self, power):
        image = Image.new("1", (self.oled.width, self.oled.height))
        draw = ImageDraw.Draw(image)
        
        # Draw the text
        dt_now = datetime.datetime.now()
        draw.text((0, 0), dt_now.strftime('%m/%d %H:%M'), font=self.font1, fill=255)
        draw.text((0, 20), f"消費電力: {power} W", font=self.font1, fill=255)

        # Display image
        self.oled.image(image)
        self.oled.show()


    def close_display(self):
        self.oled.fill(0)
        self.oled.show()


    def _connect(self, cmd):
        # TODO: FAIL時のシーケンス実装
        # 失敗時はFAIL ER**がresultに格納される
        self.ser.write(str2byte(cmd))
        self.ser.readline()
        result = byte2str(self.ser.readline())
        # logging.debug(result)
        return result


    def scan(self, broute_id, broute_pw):

        # TODO スキャン結果を書き出し、内容が十分な時は設定ファイルの内容を返すだけの処理にしたい。

        # logging.info("Bルートパスワード設定")
        cmd = "SKSETPWD C " + broute_pw + "\r\n"
        self._connect(cmd)

        # logging.info("Bルート認証ID設定")
        cmd = "SKSETRBID " + broute_id + "\r\n"
        self._connect(cmd)

        scan_duration = 6 # スキャン時間
        scan_result_dict = {} # スキャン結果の入れ物

        # Active scan
        # logging.info("Active Scan")
        while ("Channel" not in scan_result_dict):
            cmd = str2byte("SKSCAN 2 FFFFFFFF " + str(scan_duration) + "\r\n")
            self.ser.write(cmd)
            scan_end = False
            while not scan_end:
                line = byte2str(self.ser.readline())
                if line.startswith("EVENT 22"):
                    # logging.debug(line)
                    scan_end = True
                elif line.startswith("  "):
                    # logging.debug(line)
                    cols = line.strip().split(":")
                    #logging.info(cols[0] + ":" + cols[1])
                    scan_result_dict[cols[0]] = cols[1]
            scan_duration += 1

            if "Addr" in scan_result_dict.keys():
                # logging.info("MacアドレスをIPV6リンクローカルアドレスに変換")
                # MacアドレスをIPV6リンクローカルアドレスに変換する。
                cmd = "SKLL64 " + scan_result_dict["Addr"] + "\r\n"
                ipv6_address = self._connect(cmd).strip()
                scan_result_dict["address"] = ipv6_address
            else:
                # logging.error("Fail to get addr")
                self.ser.close()
                sys.exit()

            # 2回スキャンして見つからなければ終了　
            if 7 < scan_duration and ("Channel" not in scan_result_dict):
                # logging.error("Scan retry over")
                self.ser.close()
                sys.exit()

        return scan_result_dict


    def pana_auth(self, broute_id, broute_pw, channel, pan_id, address):
        # TODO 接続失敗時の処理実装
        # logging.info("Bルートパスワード設定")
        cmd = "SKSETPWD C " + broute_pw + "\r\n"
        self._connect(cmd)

        # logging.info("Bルート認証ID設定")
        cmd = "SKSETRBID " + broute_id + "\r\n"
        self._connect(cmd)

        # logging.info('Channel設定')
        cmd = "SKSREG S2 " + channel + "\r\n"
        self._connect(cmd)

        # logging.info("PanID設定")
        cmd = "SKSREG S3 " + pan_id + "\r\n"
        self._connect(cmd)

        # logging.info('PANA接続シーケンス')
        cmd = "SKJOIN " + address + "\r\n"
        self._connect(cmd)

        #PANA接続完了待ち
        be_connected = False
        while not be_connected:
            result = self.ser.readline()
            line = byte2str(result)
            # logging.debug(line)
            if line.startswith("EVENT 24"):
                # logging.error("PANA 接続失敗")
                self.ser.close()
                sys.exit()
            elif line.startswith("EVENT 25"):
                # logging.info("PANA 接続成功")
                be_connected = True

        self.ser.readline() # インスタンスリストダミーリード


    def get_power(self, echonetlite_frame, address):
        response_list = []
        # コマンド送信
        cmd = "SKSENDTO 1 {0} 0E1A 1 {1:04X} ".format(address, len(echonetlite_frame))
        #cmd = str2byte(cmd) + str2byte(echonetlite_frame)
        cmd = str2byte(cmd) + echonetlite_frame
        #print("send command as ", byte2str(cmd))
        self.ser.write(cmd)

        # 返答受信(4つ分の応答をリスト格納)
        response_list.append(byte2str(self.ser.readline()))
        response_list.append(byte2str(self.ser.readline()))
        response_list.append(byte2str(self.ser.readline()))
        response_list.append(byte2str(self.ser.readline()))

        # データチェック
        for response in response_list:
            # コマンドのレスポンス取得にタイムアウトをもうけた。応答がない場合、空文字列が返ってくるので、
            # その時はプログラムを終了する。
            # これは暫定的に処理の動きを見るための処理なので、実際はこれを通信途絶として検出し、自動再接続
            # できるようにして半永久的に動作させたい。
            if len(response) == 0:
                # logging.error("Don't come data")
                print("Don't come data")
                self.ser.close()
                sys.exit()
            else:
                # logging.debug(response)
                print(response)
                if response.startswith("ERXUDP"):
                    data = response
                #else:
                #    logging.error("Don't come data starting 'ERXUDP'")
                #    self.ser.close()
                #    sys.exit()

        # 応答から瞬時消費電力の値を取り出す
        power_int = 0
        cols = data.strip().split(" ")
        result = cols[8] # UDPデータ受信部分
        seoj = result[8:8+6]
        esv = result[20:20+2]

        if (seoj == "028801") and (esv == "72"):
            epc = result[24:24+2]
        else:
            # logging.error("Don't match currect data in 'seoj' and/or 'esv'")
            print("Don't match currect data in 'seoj' and/or 'esv'")
            self.ser.close()
            sys.exit()

        if epc == "E7":
            power_hex = data[-8:]
            power_int = int(power_hex, 16)
        else:
            # logging.error("Don't match currect data in 'epc'")
            print("Don't match currect data in 'epc'")
            self.ser.close()
            sys.exit()

        current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        return [current_time, power_int]


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
    smtmeterlogger = SmtmeterLogger(serial_device_name, baudrate)

    print("アクティブスキャンシーケンス")
    d = smtmeterlogger.scan(broute_id, broute_pw)
    channel = d["Channel"]
    pan_id = d["Pan ID"]
    address = d["address"]

    print("PANA認証シーケンス")
    smtmeterlogger.pana_auth(broute_id, broute_pw, channel, pan_id, address)

    print("電力値取得")
    dt, power = smtmeterlogger.get_power(echonetlite_frame, address)
    #text = f"Power: {power} W"
    print(power)

    print("ディスプレイ表示")
    smtmeterlogger.display_text(power)

    time.sleep(10)

    print("ディスプレイ消灯")
    smtmeterlogger.close_display()
            
