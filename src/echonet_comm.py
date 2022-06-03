#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
import datetime
import logging
import sys

def connect(serial, cmd):
    # TODO: FAIL時のシーケンス実装
    # 失敗時はFAIL ER**がresultに格納される
    serial.write(str2byte(cmd))
    serial.readline()
    result = byte2str(serial.readline())
    logging.debug(result)
    return result

def scan(serial, broute_id, broute_pw):

    # TODO スキャン結果を書き出し、内容が十分な時は設定ファイルの内容を返すだけの処理にしたい。

    logging.info("Bルートパスワード設定")
    cmd = "SKSETPWD C " + broute_pw + "\r\n"
    connect(serial, cmd)

    logging.info("Bルート認証ID設定")
    cmd = "SKSETRBID " + broute_id + "\r\n"
    connect(serial, cmd)

    scan_duration = 6 # スキャン時間
    scan_result_dict = {} # スキャン結果の入れ物

    # Active scan
    logging.info("Active Scan")
    while ("Channel" not in scan_result_dict):
        cmd = str2byte("SKSCAN 2 FFFFFFFF " + str(scan_duration) + "\r\n")
        serial.write(cmd)
        scan_end = False
        while not scan_end:
            line = byte2str(serial.readline())
            if line.startswith("EVENT 22"):
                logging.debug(line)
                scan_end = True
            elif line.startswith("  "):
                logging.debug(line)
                cols = line.strip().split(":")
                #logging.info(cols[0] + ":" + cols[1])
                scan_result_dict[cols[0]] = cols[1]
        scan_duration += 1

        if "Addr" in scan_result_dict.keys():
            logging.info("MacアドレスをIPV6リンクローカルアドレスに変換")
            # MacアドレスをIPV6リンクローカルアドレスに変換する。
            cmd = "SKLL64 " + scan_result_dict["Addr"] + "\r\n"
            ipv6_address = connect(serial, cmd).strip()
            scan_result_dict["address"] = ipv6_address
        else:
            logging.error("Fail to get addr")
            serial.close()
            sys.exit()

        # 2回スキャンして見つからなければ終了　
        if 7 < scan_duration and ("Channel" not in scan_result_dict):
            logging.error("Scan retry over")
            serial.close()
            sys.exit()

    return scan_result_dict


def pana_auth(serial, broute_id, broute_pw, channel, pan_id, address):
    # TODO 接続失敗時の処理実装
    logging.info("Bルートパスワード設定")
    cmd = "SKSETPWD C " + broute_pw + "\r\n"
    connect(serial, cmd)

    logging.info("Bルート認証ID設定")
    cmd = "SKSETRBID " + broute_id + "\r\n"
    connect(serial, cmd)

    logging.info('Channel設定')
    cmd = "SKSREG S2 " + channel + "\r\n"
    connect(serial, cmd)

    logging.info("PanID設定")
    cmd = "SKSREG S3 " + pan_id + "\r\n"
    connect(serial, cmd)

    logging.info('PANA接続シーケンス')
    cmd = "SKJOIN " + address + "\r\n"
    connect(serial, cmd)

    #PANA接続完了待ち
    be_connected = False
    while not be_connected:
        result = serial.readline()
        line = byte2str(result)
        logging.debug(line)
        if line.startswith("EVENT 24"):
            logging.error("PANA 接続失敗")
            serial.close()
            sys.exit()
        elif line.startswith("EVENT 25"):
            logging.info("PANA 接続成功")
            be_connected = True

    serial.readline() # インスタンスリストダミーリード


def get_power(serial, echonetlite_frame, address):
    response_list = []
    # コマンド送信
    cmd = "SKSENDTO 1 {0} 0E1A 1 {1:04X} ".format(address, len(echonetlite_frame))
    cmd = str2byte(cmd) + echonetlite_frame
    serial.write(cmd)

    # 返答受信(4つ分の応答をリスト格納)
    response_list.append(byte2str(serial.readline()))
    response_list.append(byte2str(serial.readline()))
    response_list.append(byte2str(serial.readline()))
    response_list.append(byte2str(serial.readline()))

    # データチェック
    for response in response_list:
        # コマンドのレスポンス取得にタイムアウトをもうけた。応答がない場合、空文字列が返ってくるので、
        # その時はプログラムを終了する。
        # これは暫定的に処理の動きを見るための処理なので、実際はこれを通信途絶として検出し、自動再接続
        # できるようにして半永久的に動作させたい。
        if len(response) == 0:
            logging.error("Don't come data")
            serial.close()
            sys.exit()
        else:
            logging.debug(response)
            if response.startswith("ERXUDP"):
                data = response
            #else:
            #    logging.error("Don't come data starting 'ERXUDP'")
            #    serial.close()
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
        logging.error("Don't match currect data in 'seoj' and/or 'esv'")
        serial.close()
        sys.exit()

    if epc == "E7":
        power_hex = data[-8:]
        power_int = int(power_hex, 16)
    else:
        logging.error("Don't match currect data in 'epc'")
        serial.close()
        sys.exit()

    current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    return [current_time, power_int]
