#!/usr/bin/env python3
"""
ДУЛААНЫ ДАХИН ДАМЖУУЛАХ ТӨВИЙН БОДИТ СИМУЛЯТОР
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Систем:
    Дулааны станц → [Орох шугам] → Бойлер → [Гарах шугам] → Хэрэглэгч
                                                              ↓
    Дулааны станц ← [Буцах шугам] ← Бойлер ← [Ирэх шугам] ← Хэрэглэгч

Шугамууд:
    1. Supply Line (Станцаас ирэх)    - Temp 1, Pressure 1
    2. Forward Line (Хэрэглэгч рүү)   - Temp 2, Pressure 2
    3. Return Line (Хэрэглэгчээс)     - Temp 3, Pressure 3
    4. Return Line (Станц руу)        - Temp 4, Pressure 4

Физик хамаарал:
    • Температур: T1 > T2 > T3 > T4 (дулаан алдагдана)
    • Даралт: P1 > P2 ≈ P3 > P4 (торны эсэргүүцэл)
    • Бойлерийн үр ашиг: 10-15°C температур алдагдал
    • Урсгалын эсэргүүцэл: 0.3-0.5 bar даралт алдагдал
"""

import time
import json
import logging
import random
import math
import requests
from datetime import datetime
from typing import Dict, Tuple
import signal
import sys

# ============================================
# ТОХИРГОО
# ============================================

class Config:
    # Төхөөрөмж
    DEVICE_ID = "SUBSTATION_01"
    LOCATION = "Улаанбаатар, Сүхбаатар дүүрэг"
    
    # Сервер
    SERVER_URL = "http://mysql-server-tailscale.tailb51a53.ts.net:5000/check"
    GET_SENSOR_ID_URL = "http://mysql-server-tailscale.tailb51a53.ts.net:5000/m/sensor-objects-in-measurement-object/1"
    SEND_INTERVAL = 3  # секунд
    
    # Физик параметрүүд
    PHYSICS = {
        # Дулааны станцын температур (гадны температураас хамаарна)
        'station_base_temp': 85.0,      # Үндсэн температур (°C)
        'outdoor_temp_influence': 0.5,  # Гадны температурын нөлөө
        
        # Температурын алдагдал
        'pipe_heat_loss': 2.0,          # Шугам бүрт 2°C
        'boiler_heat_loss': 12.0,       # Бойлерт 12°C
        
        # Даралтын алдагдал
        'supply_pressure': 6.5,         # Орох даралт (bar)
        'pipe_pressure_drop': 0.15,     # Шугам бүрт 0.15 bar
        'boiler_pressure_drop': 0.4,    # Бойлерт 0.4 bar
        
        # Хэлбэлзэл
        'temp_noise': 0.8,              # Температурын шуугиан
        'pressure_noise': 0.1,          # Даралтын шуугиан
    }
    
    # Мэдрэгчийн тодорхойлолт
    SENSORS = {
        # Шугам 1: Станцаас ирэх (Supply from station)
        'supply_from_station_temp': {
            'id':0,
            'sensorObjectLocationId': 1,
            'name': 'Станцаас ирэх температур',
            'typeId': 1,
            'unit': '°C',
            'pipe': 'supply_station'
        },
        'supply_from_station_pressure': {
            'id':0,
            'sensorObjectLocationId': 5,
            'name': 'Станцаас ирэх даралт',
            'typeId': 2,
            'unit': 'bar',
            'pipe': 'supply_station'
        },
        
        # Шугам 2: Хэрэглэгч рүү (Forward to consumer)
        'forward_to_consumer_temp': {
            'id':0,
            'sensorObjectLocationId': 3,
            'name': 'Хэрэглэгч рүү гарах температур',
            'typeId': 1,
            'unit': '°C',
            'pipe': 'forward_consumer'
        },
        'forward_to_consumer_pressure': {
            'id':0,
            'sensorObjectLocationId': 7,
            'name': 'Хэрэглэгч рүү гарах даралт',
            'typeId': 2,
            'unit': 'bar',
            'pipe': 'forward_consumer'
        },
        
        # Шугам 3: Хэрэглэгчээс буцах (Return from consumer)
        'return_from_consumer_temp': {
            'id':0,
            'sensorObjectLocationId': 4,
            'name': 'Хэрэглэгчээс буцах температур',
            'typeId': 1,
            'unit': '°C',
            'pipe': 'return_consumer'
        },
        'return_from_consumer_pressure': {
            'id':0,
            'sensorObjectLocationId': 6,
            'name': 'Хэрэглэгчээс буцах даралт',
            'typeId': 2,
            'unit': 'bar',
            'pipe': 'return_consumer'
        },
        
        # Шугам 4: Станц руу буцах (Return to station)
        'return_to_station_temp': {
            'id':0,
            'sensorObjectLocationId': 2,
            'name': 'Станц руу буцах температур',
            'typeId': 1,
            'unit': '°C',
            'pipe': 'return_station'
        },
        'return_to_station_pressure': {
            'id':0,
            'sensorObjectLocationId': 6,
            'name': 'Станц руу буцах даралт',
            'typeId': 2,
            'unit': 'bar',
            'pipe': 'return_station'
        }
    }
    
    LOG_FILE = "/var/log/heating_simulator/simulator.log"
    LOG_LEVEL = logging.INFO

# ============================================
# LOGGER
# ============================================

def setup_logger():
    logger = logging.getLogger('HeatingSimulator')
    logger.setLevel(Config.LOG_LEVEL)
    
    try:
        file_handler = logging.FileHandler(Config.LOG_FILE)
    except PermissionError:
        file_handler = logging.FileHandler('/tmp/heating_simulator.log')
    
    console_handler = logging.StreamHandler()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

# ============================================
# ФИЗИК ДУЛААНЫ СИСТЕМ
# ============================================

class HeatingSystem:
    """Дулааны системийн физик загвар"""
    
    def __init__(self):
        self.outdoor_temp = -15.0  # Гадны температур (°C)
        self.time_of_day = 0
        
        # Smooth transition-ий төлөв
        self.last_station_temp = Config.PHYSICS['station_base_temp']
        self.last_pressure = Config.PHYSICS['supply_pressure']
    
    def get_outdoor_temperature(self) -> float:
        """
        Гадны температур (өдрийн болон улирлын хэлбэлзэлтэй)
        
        Улаанбаатарын температур:
        - Өвөл: -30°C ... -10°C
        - Өдрийн хэлбэлзэл: ±5°C
        """
        hour = datetime.now().hour
        
        # Өдрийн температурын өөрчлөлт
        daily_variation = 5 * math.sin((hour - 6) * math.pi / 12)
        
        # Улирлын температур (өвөл)
        base_temp = -20.0
        
        return base_temp + daily_variation + random.gauss(0, 2)
    
    def calculate_station_supply_temp(self) -> float:
        """
        Дулааны станцаас ирэх температур
        
        Логик:
        - Гадна хүйтэн → станц илүү халуун ус илгээнэ
        - Гадна дулаан → станц бага халуун ус илгээнэ
        """
        outdoor = self.get_outdoor_temperature()
        
        # Гадны температураас хамааралтай compensation
        # Гадна -30°C → станц 95°C
        # Гадна -10°C → станц 75°C
        temp_compensation = -outdoor * Config.PHYSICS['outdoor_temp_influence']
        
        target_temp = Config.PHYSICS['station_base_temp'] + temp_compensation
        
        # Smooth transition (хурдан өөрчлөгдөхгүй)
        change_rate = 0.05
        new_temp = (
            self.last_station_temp * (1 - change_rate) +
            target_temp * change_rate
        )
        
        # Шуугиан нэмэх
        new_temp += random.gauss(0, Config.PHYSICS['temp_noise'])
        
        # Хязгаарлалт
        new_temp = max(70, min(100, new_temp))
        
        self.last_station_temp = new_temp
        return new_temp
    
    def calculate_all_readings(self) -> Dict[str, float]:
        """
        Бүх 8 мэдрэгчийн утгыг физик хамаарлын дагуу тооцоолох
        
        Урсгал:
        Station (85°C, 6.5bar)
            ↓ -2°C, -0.15bar (шугамын алдагдал)
        Бойлер орох (83°C, 6.35bar)
            ↓ -12°C, -0.4bar (бойлерийн алдагдал)
        Бойлер гарах (71°C, 5.95bar)
            ↓ -2°C, -0.15bar (шугамын алдагдал)
        Consumer (69°C, 5.8bar)
            ↓ Хэрэглэгч дулаан авна
        Consumer return (55°C, 5.8bar)
            ↓ -2°C, -0.15bar (шугамын алдагдал)
        Station return (53°C, 5.65bar)
        """
        
        readings = {}
        
        # 1️⃣ Шугам 1: Станцаас ирэх (Supply from station)
        T1 = self.calculate_station_supply_temp()
        P1 = Config.PHYSICS['supply_pressure'] + random.gauss(0, Config.PHYSICS['pressure_noise'])
        
        readings['supply_from_station_temp'] = round(T1, 2)
        readings['supply_from_station_pressure'] = round(P1, 2)
        
        # 2️⃣ Шугам 2: Бойлер орох = Станцаас шугамын алдагдал хасах
        pipe_loss_1 = Config.PHYSICS['pipe_heat_loss'] + random.gauss(0, 0.3)
        pressure_drop_1 = Config.PHYSICS['pipe_pressure_drop'] + random.gauss(0, 0.02)
        
        T2 = T1 - pipe_loss_1
        P2 = P1 - pressure_drop_1
        
        # 3️⃣ Бойлер боловсруулалт
        boiler_temp_loss = Config.PHYSICS['boiler_heat_loss'] + random.gauss(0, 1.0)
        boiler_pressure_drop = Config.PHYSICS['boiler_pressure_drop'] + random.gauss(0, 0.05)
        
        # 4️⃣ Шугам 3: Хэрэглэгч рүү (Forward to consumer)
        T_forward = T2 - boiler_temp_loss / 2  # Бойлерийн дундах температур
        P_forward = P2 - boiler_pressure_drop / 2
        
        readings['forward_to_consumer_temp'] = round(T_forward, 2)
        readings['forward_to_consumer_pressure'] = round(P_forward, 2)
        
        # 5️⃣ Хэрэглэгч дулаан авна (10-15°C temperature drop)
        consumer_temp_drop = 12 + random.gauss(0, 2)  # Хэрэглэгчийн ачаалал
        
        # 6️⃣ Шугам 4: Хэрэглэгчээс буцах (Return from consumer)
        T_return = T_forward - consumer_temp_drop
        P_return = P_forward - 0.1  # Жижиг даралтын алдагдал
        
        readings['return_from_consumer_temp'] = round(T_return, 2)
        readings['return_from_consumer_pressure'] = round(P_return, 2)
        
        # 7️⃣ Шугам 5: Станц руу буцах шугам
        pipe_loss_2 = Config.PHYSICS['pipe_heat_loss'] + random.gauss(0, 0.3)
        pressure_drop_2 = Config.PHYSICS['pipe_pressure_drop'] + random.gauss(0, 0.02)
        
        T_return_station = T_return - pipe_loss_2
        P_return_station = P_return - pressure_drop_2
        
        readings['return_to_station_temp'] = round(T_return_station, 2)
        readings['return_to_station_pressure'] = round(P_return_station, 2)
        
        return readings
    
    def get_system_efficiency(self, readings: Dict[str, float]) -> float:
        """Системийн үр ашиг тооцоолох"""
        supply_temp = readings['supply_from_station_temp']
        return_temp = readings['return_to_station_temp']
        
        # Delta T - Системийн үр ашигийн үзүүлэлт
        delta_t = supply_temp - return_temp
        
        # Оновчтой delta T = 25-30°C
        return delta_t

# ============================================
# ӨГӨГДӨЛ ИЛГЭЭХ
# ============================================
class GetSensorIDs:
    def __init__(self):
        #self.url = url
        self.base_url = f'http://mysql-server-tailscale.tailb51a53.ts.net:5000'  
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        })
    def fetch(self,url):        
        url = f'http://mysql-server-tailscale.tailb51a53.ts.net:5000/m/sensor-objects-in-measurement-object/1'
        
        try:
            logger.info(url)
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                
                data = response.json()
                sensor_ids = {}
                logger.info("🔍 Мэдрэгчийн ID-үүдийг серверээс авч байна...{data}")
                # for sensor in data.get([]):
                #     for key, config in Config.SENSORS.items():
                #         if Config.SENSORS['sensorObjectLocationId'] == sensor['sensorObjectLocationId']:
                #             Config.SENSORS['id'] = sensor['id']
                # logger.info("✅ Мэдрэгчийн ID-үүдийг амжилттай авлаа")
                
                # for key, config in Config.SENSORS.items():
                #     logger.info(f"   - {key}: ID={config['id']} sensorObjectLocationId={config['sensorObjectLocationId']}")
                return True
            else:
                logger.error(f"❌ HTTP {response.status_code} while fetching sensor IDs")
                return {}
        except Exception as e:
            logger.error(f"❌ Error fetching sensor IDs: {str(e)}")
            return {}
class DataSender:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        self.success_count = 0
        self.failed_count = 0
    
    def send(self, readings: Dict[str, float]) -> bool:
        try:
            payload = {
                'device': Config.DEVICE_ID,
                'location': Config.LOCATION,
                'ts': int(time.time() * 1000),
                'ts_sec': int(time.time()),
                'synced': True,
                'readings': []
            }
            
            for key, value in readings.items():
                sensor_config = Config.SENSORS[key]
                payload['readings'].append({
                    'id': sensor_config['id'],
                    'name': key,
                    'value': value,
                    'unit': sensor_config['unit']
                })
            
            response = self.session.post(self.url, json=payload, timeout=5)
            
            if response.status_code == 200:
                self.success_count += 1
                logger.info(f"✅ Илгээгдлээ: {len(readings)} мэдрэгч")
                return True
            else:
                self.failed_count += 1
                logger.error(f"❌ HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ Алдаа: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict:
        total = self.success_count + self.failed_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0
        return {
            'success': self.success_count,
            'failed': self.failed_count,
            'total': total,
            'success_rate': round(success_rate, 2)
        }

# ============================================
# ҮНДСЭН СИМУЛЯТОР
# ============================================

class HeatingSubstationSimulator:
    def __init__(self):
        GetSensorIDs.fetch(self)
        self.heating_system = HeatingSystem()
        self.data_sender = DataSender(Config.SERVER_URL)
        self.running = False
        self.iteration = 0
        
        logger.info("=" * 70)
        logger.info("🏭 ДУЛААНЫ ДАХИН ДАМЖУУЛАХ ТӨВИЙН СИМУЛЯТОР")
        logger.info("=" * 70)
        logger.info(f"📍 Төхөөрөмж: {Config.DEVICE_ID}")
        logger.info(f"📍 Байршил: {Config.LOCATION}")
        logger.info(f"🌐 Сервер:   {Config.SERVER_URL}")
        logger.info(f"⏱️  Давтамж:  {Config.SEND_INTERVAL} секунд")
        logger.info(f"📊 Мэдрэгч:  8 ширхэг (4 шугам)")
        logger.info("")
        logger.info("🔄 Системийн урсгал:")
        logger.info("   Станц → [Орох] → Бойлер → [Гарах] → Хэрэглэгч")
        logger.info("   Станц ← [Буцах] ← Бойлер ← [Ирэх] ← Хэрэглэгч")
        logger.info("=" * 70)
    
    def run(self):
        self.running = True
        
        try:
            while self.running:
                self.iteration += 1
                
                # Мэдрэгч унших
                readings = self.heating_system.calculate_all_readings()
                
                # Үр ашиг тооцоолох
                efficiency = self.heating_system.get_system_efficiency(readings)
                
                # Дэлгэцэнд харуулах
                self._print_readings(readings, efficiency)
                
                # Сервер лүү илгээх
                self.data_sender.send(readings)
                
                # Статистик (10 удаад нэг)
                if self.iteration % 10 == 0:
                    self._print_statistics()
                
                time.sleep(Config.SEND_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  Ctrl+C - Зогсож байна")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Алдаа: {str(e)}")
            self.stop()
    
    def stop(self):
        self.running = False
        logger.info("\n" + "=" * 70)
        logger.info("🛑 СИМУЛЯТОР ЗОГСЛОО")
        self._print_statistics()
        logger.info("=" * 70)
    
    def _print_readings(self, readings: Dict[str, float], efficiency: float):
        outdoor = self.heating_system.get_outdoor_temperature()
        
        logger.info(f"\n{'━' * 70}")
        logger.info(f"📊 Давталт #{self.iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🌡️  Гадны температур: {outdoor:.1f}°C")
        logger.info(f"{'─' * 70}")
        
        # Шугам 1: Станцаас
        logger.info(f"🔴 Шугам 1 - СТАНЦААС ОРОХ:")
        logger.info(f"   Температур: {readings['supply_from_station_temp']:6.1f}°C")
        logger.info(f"   Даралт:     {readings['supply_from_station_pressure']:6.2f} bar")
        
        # Шугам 2: Хэрэглэгч рүү
        logger.info(f"🟠 Шугам 2 - ХЭРЭГЛЭГЧ РҮҮ:")
        logger.info(f"   Температур: {readings['forward_to_consumer_temp']:6.1f}°C")
        logger.info(f"   Даралт:     {readings['forward_to_consumer_pressure']:6.2f} bar")
        
        # Шугам 3: Хэрэглэгчээс
        logger.info(f"🔵 Шугам 3 - ХЭРЭГЛЭГЧЭЭС БУЦАХ:")
        logger.info(f"   Температур: {readings['return_from_consumer_temp']:6.1f}°C")
        logger.info(f"   Даралт:     {readings['return_from_consumer_pressure']:6.2f} bar")
        
        # Шугам 4: Станц руу
        logger.info(f"🟣 Шугам 4 - СТАНЦ РУУ БУЦАХ:")
        logger.info(f"   Температур: {readings['return_to_station_temp']:6.1f}°C")
        logger.info(f"   Даралт:     {readings['return_to_station_pressure']:6.2f} bar")
        
        # Системийн үр ашиг
        logger.info(f"{'─' * 70}")
        logger.info(f"⚡ ΔT (Үр ашиг):  {efficiency:.1f}°C {'✅' if 25 <= efficiency <= 35 else '⚠️'}")
        logger.info(f"   Оновчтой: 25-35°C")
    
    def _print_statistics(self):
        stats = self.data_sender.get_statistics()
        logger.info(f"\n{'═' * 70}")
        logger.info("📈 СТАТИСТИК")
        logger.info(f"{'─' * 70}")
        logger.info(f"✅ Амжилттай:     {stats['success']:5} удаа")
        logger.info(f"❌ Амжилтгүй:     {stats['failed']:5} удаа")
        logger.info(f"📦 Нийт:          {stats['total']:5} удаа")
        logger.info(f"📊 Амжилтын хувь: {stats['success_rate']:5.1f}%")
        logger.info(f"{'═' * 70}")

# ============================================
# SIGNAL HANDLER
# ============================================

simulator = None

def signal_handler(signum, frame):
    logger.info(f"\n⚠️  Signal {signum} хүлээн авлаа")
    if simulator:
        simulator.stop()
    sys.exit(0)

# ============================================
# MAIN
# ============================================

def main():
    global simulator
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    simulator = HeatingSubstationSimulator()
    simulator.run()

if __name__ == "__main__":
    main()