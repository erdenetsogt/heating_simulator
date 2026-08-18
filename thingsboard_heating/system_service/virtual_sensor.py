import time
import random
import json
import paho.mqtt.client as mqtt

# --- ТОХИРГООНЫ ХЭСЭГ ---
THINGSBOARD_HOST = "localhost"  # Хэрэв өөр сервер дээр байгаа бол IP хаягийг нь бичнэ (ж-нь: "192.168.1.100")
THINGSBOARD_PORT = 1883         # MQTT-ийн стандарт порт
ACCESS_TOKEN = "3asLDlfyiwBU3InUpYHS"  # 1-р алхам дээр авсан токеноо энд тавина

# MQTT холболт амжилттай болсон эсэхийг шалгах функц
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("ThingsBoard-той амжилттай холбогдлоо!")
    else:
        print(format(rc), f"Холболт амжилтгүй боллоо. Алдааны код: {rc}")

# MQTT клиент үүсгэх
client = mqtt.Client()
client.on_connect = on_connect

# Нэвтрэх нэр (Username) хэсэгт Access Token-ийг заавал тавьж өгнө
client.username_pw_set(ACCESS_TOKEN)

# Сервер рүү холбогдох
print("ThingsBoard-руу холбогдож байна...")
client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)

# Ард талд холболтыг тасралтгүй ажиллуулах
client.loop_start()

try:
    while True:
        # Виртуал температурын өгөгдөл үүсгэх (20.0-оос 30.0 хооронд)
        temperature = round(random.uniform(20.0, 30.0), 2)
        
        # ThingsBoard-д танигдах JSON дата формат
        payload = {
            "temperature": temperature
        }
        
        # 'v1/devices/me/telemetry' гэсэн үндсэн сэдэв (topic) рүү датаг илгээнэ
        client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
        print(f"Илгээсэн өгөгдөл: {payload}")
        
        # 2 секунд тутамд өгөгдөл илгээнэ
        time.sleep(2)

except KeyboardInterrupt:
    print("\nПрограмм зогслоо.")
    client.loop_stop()
    client.disconnect()
