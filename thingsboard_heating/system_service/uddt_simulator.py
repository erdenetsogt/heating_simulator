#Ус дулаан дамжуулах төвийн (УДТ) симулятор
import time
import json
import random
import paho.mqtt.client as mqtt

# --- ТОХИРГОО ХЭСЭГ ---
THINGSBOARD_HOST = "localhost"  # Хэрэв үүлэн систем бол IP эсвэл домэйн хаягийг бичнэ
THINGSBOARD_PORT = 1883
ACCESS_TOKEN = "gbSCVaMbHKstw0G45bxy"  # 1-р алхмаас авсан токен

# MQTT холболт үүсгэх
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(ACCESS_TOKEN)

try:
    client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
    client.loop_start()
    print("ThingsBoard-той амжилттай холбогдлоо. Өгөгдөл илгээж байна...")

    while True:
        # 4 температурын мэдрэгчийн виртуал өгөгдөл (Цельс)
        # Жишээ: Төвийн шугам, Хэрэглээний халуун ус, Халаалтын өгөх/буцах шугам
        telemetry_data = {
            "temp_in_fac": round(random.uniform(70.0, 85.0), 2),
            "temp_out_fac": round(random.uniform(50.0, 65.0), 2),
            "temp_in_cus": round(random.uniform(60.0, 75.0), 2),
            "temp_out_cus": round(random.uniform(40.0, 55.0), 2),
            
            # 4 даралтын мэдрэгчийн виртуал өгөгдөл (Бар эсвэл Паскаль)
            "press_in_fac": round(random.uniform(4.5, 6.0), 2),
            "press_out_fac": round(random.uniform(3.0, 4.5), 2),
            "press_in_cus": round(random.uniform(4.0, 5.5), 2),
            "press_out_cus": round(random.uniform(2.5, 3.8), 2)
        }

        # Өгөгдлийг JSON хэлбэрт шилжүүлж, ThingsBoard-ын стандарт сэдэв (topic) рүү илгээх
        payload = json.dumps(telemetry_data)
        client.publish("v1/devices/me/telemetry", payload, qos=1)
        
        print(f"Илгээсэн өгөгдөл: {payload}")
        time.sleep(5)  # 5 секунд тутамд илгээнэ

except KeyboardInterrupt:
    print("\nСимулятор зогслоо.")
finally:
    client.loop_stop()
    client.disconnect()
