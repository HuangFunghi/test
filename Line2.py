#!/usr/bin/env python
import LCD1602
import time
import Adafruit_DHT
import mysql.connector
import requests
import RPi.GPIO as GPIO
import threading
# 初始化LCD1602模組
LCD1602.init(0x27, 1)   # init(slave address, background light)

# 定義DHT11傳感器所連接的GPIO引腳
GPIO_PIN = 4
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO_TRIGGER = 23   
GPIO_ECHO = 24
BUZZER_PIN = 17


# 建立與MySQL數據庫的連接
mydb = mysql.connector.connect(
  host="localhost",
  user="chung",
  password="chungpw",
  database="dhtdb"
)

GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# 獲取數據庫遊標
mycursor = mydb.cursor()

# 設定LINE Notify的權杖（Token）
line_notify_token = 'JA5JGI1UXy0VD3eLSiM8zk8nmzHvBeUPdvNfcabZLcu'

buzzer_should_be_on = False

def buzzer_on():
    """啟動蜂鳴器"""
    global buzzer_should_be_on   
    print(f"buzzer0 On and flag is {buzzer_should_be_on}!")
    
    while True:
        if buzzer_should_be_on:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(0.5)            
        else:
            GPIO.output(BUZZER_PIN, GPIO.LOW)   
            time.sleep(0.1)

def set_trigger_pulse():
    GPIO.output(GPIO_TRIGGER, GPIO.LOW)
    time.sleep(0.000005)
    GPIO.output(GPIO_TRIGGER, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, GPIO.LOW)


def wait_for_echo(value, timeout):
    count = timeout
    while GPIO.input(GPIO_ECHO) == value and count > 0 :
        count = count - 1

def sr04():
    """超聲波模組"""
    while True:
        set_trigger_pulse()
        global buzzer_should_be_on 
        h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, GPIO_PIN)
        print(t,h) 
        if t > 27 or h < 30 or h > 80:
            buzzer_should_be_on = True
       
            wait_for_echo(GPIO.LOW, 5000)
            start = time.time()
            
            wait_for_echo(GPIO.HIGH, 5000)
            finish = time.time()
            
            pulse_len = finish - start
            
            v = 331+0.6*25
            
            distance_cm = pulse_len * v *100         
            
            if (pulse_len * v * 100 ) <=20:
                print(distance_cm)
                print("8")
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(1)
                buzzer_should_be_on = False

            else:
                time.sleep(0.1)
        t = 0
        print("sr04 loop")
            


try:
    print('Press Ctrl-C To Stop')
    
    last_delete_time = time.time()  # 記錄上一次刪除數據的時間
    t1 = threading.Thread(target=buzzer_on)
    t2 = threading.Thread(target=sr04)
    
    t1.start()
    t2.start()
    while True:

        h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, GPIO_PIN)
        LCD1602.write(0, 0,"Time: {}".format(time.strftime("%H:%M:%S")))
        LCD1602.write(0, 1,"T={0:0.1f}C H={1:0.1f}%".format(t, h))
        
        # 將溫度數據寫入MySQL數據庫中
        sql = "INSERT INTO temperature (time, temperature, humidity) VALUES (%s, %s, %s)"
        val = (time.strftime("%Y-%m-%d %H:%M:%S"), t, h)
        mycursor.execute(sql, val)
        mydb.commit()

        # 檢查是否需要刪除數據
        if time.time() - last_delete_time > 60:  # 判斷是否到了定時刪除數據的時間點
            sql_delete = "DELETE FROM temperature WHERE time < NOW() - INTERVAL 1 MINUTE"
            mycursor.execute(sql_delete)
            mydb.commit()
            last_delete_time = time.time()  # 更新上一次刪除數據的時間

        # 判斷溫度和濕度是否超出閾值
        if t > 27 or h < 30 or h > 80:
            
            message = "溫度：{}度，濕度：{}%".format(t, h)
            payload = {'message': message}
            headers = {
            'Authorization': 'Bearer JA5JGI1UXy0VD3eLSiM8zk8nmzHvBeUPdvNfcabZLcu',
             'Content-Type': 'application/x-www-form-urlencoded'}
            r = requests.post('https://notify-api.line.me/api/notify', data=payload, headers=headers)
            print(r.text) 

        time.sleep(1)

except KeyboardInterrupt:
    print('Close Program')
finally:
    GPIO.cleanup()
    LCD1602.clear()
    mydb.close()