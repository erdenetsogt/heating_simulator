#!/usr/bin/env python3
"""
ДУЛААНЫ ДАХИН ДАМЖУУЛАХ ТӨВИЙН СИМУЛЯТОР
6 мэдрэгч (3 температур, 3 даралт)
Ubuntu systemd service
"""

import time
import json
import logging
import random
import math
import requests
from datetime import datetime
from typing import Dict, List
import signal
import sys

# ============================================
# ТОХИРГОО
# ============================================

class Config:
    # Дулааны төв
    DEVICE_ID = "SUBSTATION_01"
    LOCATION = "Улаанбаатар, Сүхбаатар дүүрэг"
    
    # Сервер
    SERVER_URL = "http://mysql-server-tailscale.tailb51a53.ts.net:5000/v/m/current/"
    SEND_INTERVAL = 3  # 3 секунд
    
    # Мэдрэгчийн параметрүүд
    SENSORS = {
        # Температур (°C)
        'supply_temp': {
            'id': 0,
            'name': 'Орох температур',
            'type': 'temperature',
            'unit': '°C',
            'base': 75.0,      # Үндсэн утга
            'variance': 5.0,   # Хэлбэлзэл ±5°C
            'min': 60.0,
            'max': 95.0,
            'trend_factor': 0.05  # Улирлын өөрчлөлт
        },
        'return_temp': {
            'id': 1,
            'name': 'Буцах температур',
            'type': 'temperature',
            'unit': '°C',
            'base': 55.0,
            'variance': 4.0,
            'min': 45.0,
            'max': 70.0,
            'trend_factor': 0.05
        },
        'hot_water_temp': {
            'id': 2,
            'name': 'Халуун усны температур',
            'type': 'temperature',
            'unit': '°C',
            'base': 65.0,
            'variance': 3.0,
            'min': 55.0,
            'max': 75.0,
            'trend_factor': 0.03
        },
        # Даралт (bar)
        'supply_pressure': {
            'id': 3,
            'name': 'Орох даралт',
            'type': 'pressure',
            'unit': 'bar',
            'base': 6.0,
            'variance': 0.3,
            'min': 5.0,
            'max': 8.0,
            'trend_factor': 0.02
        },
        'return_pressure': {
            'id': 4,
            'name': 'Буцах даралт',
            'type': 'pressure',
            'unit': 'bar',
            'base': 4.5,
            'variance': 0.2,
            'min': 3.5,
            'max': 6.0,
            'trend_factor': 0.02
        },
        'system_pressure': {
            'id': 5,
            'name': 'Системийн даралт',
            'type': 'pressure',
            'unit': 'bar',
            'base': 5.2,
            'variance': 0.25,
            'min': 4.0,
            'max': 7.0,
            'trend_factor': 0.02
        }
    }
    
    # Логийн тохиргоо
    LOG_FILE = "/var/log/heating_simulator.log"
    LOG_LEVEL = logging.INFO

# ============================================
# LOGGER ТОХИРГОО
# ============================================

def setup_logger():
    """Логгер тохируулах"""
    logger = logging.getLogger('HeatingSimulator')
    logger.setLevel(Config.LOG_LEVEL)
    
    # Файл handler
    try:
        file_handler = logging.FileHandler(Config.LOG_FILE)
    except PermissionError:
        # Permission алдаа бол /tmp ашиглах
        file_handler = logging.FileHandler('/tmp/heating_simulator.log')
    
    file_handler.setLevel(Config.LOG_LEVEL)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(Config.LOG_LEVEL)
    
    # Формат
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

# ============================================
# МЭДРЭГЧИЙН СИМУЛЯТОР
# ============================================

class SensorSimulator:
    """Мэдрэгчийн хийсвэр загвар"""
    
    def __init__(self):
        self.time_offset = 0
        self.last_values = {}
        
        # Эхний утгууд тохируулах
        for key, config in Config.SENSORS.items():
            self.last_values[key] = config['base']
    
    def read_sensor(self, sensor_key: str) -> float:
        """
        Мэдрэгчийн утга унших (симуляци)
        
        Алгоритм:
        1. Өмнөх утгаас бага зэрэг өөрчлөгдөх (smooth)
        2. Цаг хугацааны trend (өглөө-орой хэлбэлзэл)
        3. Random noise
        4. Min/Max хязгаарлалт
        """
        config = Config.SENSORS[sensor_key]
        
        # 1. Цагийн trend (өглөө бага, орой их)
        hour = datetime.now().hour
        time_trend = math.sin((hour - 6) * math.pi / 12) * config['trend_factor']
        
        # 2. Random walk (өмнөх утгаас бага зэрэг өөрчлөгдөх)
        change = random.gauss(0, config['variance'] * 0.1)
        
        # 3. Үндсэн утга руу татах (mean reversion)
        mean_pull = (config['base'] - self.last_values[sensor_key]) * 0.1
        
        # 4. Шинэ утга тооцоолох
        new_value = (
            self.last_values[sensor_key] + 
            change + 
            mean_pull + 
            time_trend * config['base']
        )
        
        # 5. Min/Max хязгаарлалт
        new_value = max(config['min'], min(config['max'], new_value))
        
        # 6. Хадгалах
        self.last_values[sensor_key] = new_value
        
        return round(new_value, 2)
    
    def read_all_sensors(self) -> Dict[str, float]:
        """Бүх мэдрэгч унших"""
        readings = {}
        for sensor_key in Config.SENSORS.keys():
            readings[sensor_key] = self.read_sensor(sensor_key)
        return readings
    
    def get_sensor_status(self) -> Dict:
        """Мэдрэгчийн статус"""
        status = {}
        for key, value in self.last_values.items():
            config = Config.SENSORS[key]
            
            # Хэвийн эсэхийг шалгах
            is_normal = config['min'] <= value <= config['max']
            
            status[key] = {
                'value': value,
                'unit': config['unit'],
                'status': 'normal' if is_normal else 'warning',
                'min': config['min'],
                'max': config['max']
            }
        
        return status

# ============================================
# ӨГӨГДӨЛ ИЛГЭЭХ
# ============================================

class DataSender:
    """Сервер лүү өгөгдөл илгээх"""
    
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        self.failed_count = 0
        self.success_count = 0
    
    def send(self, readings: Dict[str, float]) -> bool:
        """
        Өгөгдөл илгээх
        
        Returns:
            bool: Амжилттай эсэх
        """
        try:
            # JSON payload бэлтгэх
            payload = {
                'device': Config.DEVICE_ID,
                'location': Config.LOCATION,
                'ts': int(time.time() * 1000),  # Миллисекунд
                'ts_sec': int(time.time()),      # Секунд
                'synced': True,
                'readings': []
            }
            
            # Мэдрэгч бүрийг нэмэх
            for key, value in readings.items():
                sensor_config = Config.SENSORS[key]
                payload['readings'].append({
                    'id': sensor_config['id'],
                    'name': key,
                    'v': value,
                    'unit': sensor_config['unit']
                })
            
            # HTTP POST
            response = self.session.post(
                self.url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                self.success_count += 1
                logger.info(
                    f"✅ Амжилттай илгээгдлээ: {len(readings)} мэдрэгч, "
                    f"нийт: {self.success_count}"
                )
                return True
            else:
                self.failed_count += 1
                logger.error(
                    f"❌ HTTP алдаа: {response.status_code}, "
                    f"хариу: {response.text[:100]}"
                )
                return False
                
        except requests.exceptions.ConnectionError:
            self.failed_count += 1
            logger.error(f"❌ Холболтын алдаа: Сервер рүү холбогдож чадсангүй")
            return False
            
        except requests.exceptions.Timeout:
            self.failed_count += 1
            logger.error(f"❌ Timeout алдаа: Сервер хариу өгөхгүй байна")
            return False
            
        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ Алдаа: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict:
        """Статистик мэдээлэл"""
        total = self.success_count + self.failed_count
        success_rate = (
            (self.success_count / total * 100) if total > 0 else 0
        )
        
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
    """Дулааны төвийн симулятор"""
    
    def __init__(self):
        self.sensor_sim = SensorSimulator()
        self.data_sender = DataSender(Config.SERVER_URL)
        self.running = False
        self.iteration = 0
        
        logger.info("=" * 60)
        logger.info("ДУЛААНЫ ТӨВИЙН СИМУЛЯТОР ЭХЭЛЛЭЭ")
        logger.info("=" * 60)
        logger.info(f"Төхөөрөмж: {Config.DEVICE_ID}")
        logger.info(f"Байршил: {Config.LOCATION}")
        logger.info(f"Сервер: {Config.SERVER_URL}")
        logger.info(f"Илгээх давтамж: {Config.SEND_INTERVAL} секунд")
        logger.info(f"Мэдрэгч: {len(Config.SENSORS)} ширхэг")
        logger.info("=" * 60)
    
    def run(self):
        """Симулятор ажиллуулах"""
        self.running = True
        
        try:
            while self.running:
                self.iteration += 1
                
                # Мэдрэгч унших
                readings = self.sensor_sim.read_all_sensors()
                
                # Дэлгэцэнд харуулах
                self._print_readings(readings)
                
                # Сервер лүү илгээх
                self.data_sender.send(readings)
                
                # Статистик харуулах (10 удаад нэг)
                if self.iteration % 10 == 0:
                    self._print_statistics()
                
                # Хүлээх
                time.sleep(Config.SEND_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Хэрэглэгч зогсоолоо (Ctrl+C)")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Алдаа гарлаа: {str(e)}")
            self.stop()
    
    def stop(self):
        """Симулятор зогсоох"""
        self.running = False
        logger.info("\n" + "=" * 60)
        logger.info("СИМУЛЯТОР ЗОГСЛОО")
        self._print_statistics()
        logger.info("=" * 60)
    
    def _print_readings(self, readings: Dict[str, float]):
        """Мэдрэгчийн утга харуулах"""
        logger.info(f"\n📊 Давталт #{self.iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)
        
        for key, value in readings.items():
            config = Config.SENSORS[key]
            emoji = "🌡️" if config['type'] == 'temperature' else "📊"
            
            logger.info(
                f"{emoji} {config['name']:25} = {value:6.2f} {config['unit']:4} "
                f"[{config['min']:.1f} - {config['max']:.1f}]"
            )
    
    def _print_statistics(self):
        """Статистик харуулах"""
        stats = self.data_sender.get_statistics()
        logger.info("\n" + "=" * 60)
        logger.info("📈 СТАТИСТИК")
        logger.info("-" * 60)
        logger.info(f"✅ Амжилттай:     {stats['success']:5} удаа")
        logger.info(f"❌ Амжилтгүй:     {stats['failed']:5} удаа")
        logger.info(f"📦 Нийт:          {stats['total']:5} удаа")
        logger.info(f"📊 Амжилтын хувь: {stats['success_rate']:5.1f}%")
        logger.info("=" * 60)

# ============================================
# SIGNAL HANDLER
# ============================================

simulator = None

def signal_handler(signum, frame):
    """SIGTERM, SIGINT handler"""
    logger.info(f"\n⚠️ Signal {signum} хүлээн авлаа")
    if simulator:
        simulator.stop()
    sys.exit(0)

# ============================================
# MAIN
# ============================================

def main():
    """Үндсэн функц"""
    global simulator
    
    # Signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Симулятор эхлүүлэх
    simulator = HeatingSubstationSimulator()
    simulator.run()

if __name__ == "__main__":
    main()