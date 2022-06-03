# スマートメータBルートを利用したデータロガー

本アプリケーションは、Wi-SUMモジュールBP35A1を用いてスマートメータから
スマートメータのBルートを利用して瞬時消費電力[W]を10分ごとに取得する。データはcsvファイルに保存しつつ、slackの指定チャンネルに送信する。

## バージョン
後日記載

## 準備
Bルートに接続するためには、認証のためのIDとパスワードが必要。これらは東京電力エナジーパートナーズに利用申請をしたのち、送られてくる。

上記手続きで取得したIDとパスワードをconfig/smart_meter_config.iniという名前の設定ファイルに以下のように書き込む。

```
[settings]
broute_id = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
broute_pw = YYYYYYYYYYYY
```

また、slackを利用したデータ送信も行う。これは、slackのwebhook機能を利用する。slack webhookをアクティブにし、Incoming webhook URLを取得し、上記設定ファイルに書き込む。

```
[slack]
slack_webhook_url = https://hooks.slack.com/services/hogehoge
```

## 実行
データ収集は以下のsrc下のmain.pyを実行すればよい。
実行はスクリーンコマンドでプロセスを分けて離脱する。
```
> screen
> python3 main.py
> Ctrl-a d # デタッチで離脱

# 再接続
> screen -ls # pidを確認
> screen -r <pid> # 実行中の処理にアタッチ
```

実行後、log下のlogger.logにログが出力されるので、tailコマンドで監視できる。
```
> tail -f logger.log
```

データはdata下のpower.csvに時刻と一緒に記録される。

8/15: 想定した電文が送られてこなかったり、認証に失敗したりなどしたとき、プログラムが終了するようにしている。その代わり、cronがjobの実行状態を監視しており、停止時に自動実行させることで連続動作を実現している。

2022/6/3: SmtmeterLoggerクラスとして再整理、クラスの処理のデモ実行は以下のコマンドで実行
```
# 単一の処理を回す場合
> python3 smtmeter_logger.py
# データ取得をサイクリックに回す場合
> python3 main2.py
```

### cron設定
crontabにて、以下のコマンドを定期実行するよう設定
```
MAILTO=""
*/1 * * * * ps ax |grep -v grep | grep -q main.py|| python3 /home/pi/work/smartmeter_logger/src/main.py
```

- 1分に一回、プロセス中にあるべきmain.pyのチェックを行う。もしなければ、python3以下のコマンド(main.py実行)を走らせる。
- ログ出力はディスク容量の関係上、メール送信しない。

## Reference
- [東京電力エナジーパートナーズへのBルート申請について](https://www.tepco.co.jp/pg/consignment/liberalization/smartmeter-broute.html)
- [Slack Webhookについて](https://slack.com/intl/ja-jp/help/articles/115005265063-Slack-%E3%81%A7%E3%81%AE-Incoming-Webhook-%E3%81%AE%E5%88%A9%E7%94%A8)
- [raspberry pi上でのcron操作方法](https://k99-tech.com/blog/archives/1141#Cron-3)
- [cronのmailを送信しないようにする](https://ips.nekotype.com/2407/)
