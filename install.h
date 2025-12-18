#!/bin/bash
# ============================================
# ДУЛААНЫ ТӨВИЙН СИМУЛЯТОР - СУУЛГАХ СКРИПТ
# Ubuntu systemd service
# ============================================

set -e  # Алдаа гарвал зогсох

echo "================================================"
echo "ДУЛААНЫ ТӨВИЙН СИМУЛЯТОР - СУУЛГАЛТ"
echo "================================================"

# ============================================
# 1. СУУРЬ ХАВТАС ҮҮСГЭХ
# ============================================

echo ""
echo "📁 1. Хавтас үүсгэж байна..."

# Үндсэн хавтас
INSTALL_DIR="/opt/heating_simulator"
sudo mkdir -p "$INSTALL_DIR"

# Log хавтас
sudo mkdir -p /var/log/heating_simulator

echo "✅ Хавтас бэлэн: $INSTALL_DIR"

# ============================================
# 2. PYTHON СКРИПТ ХУУЛАХ
# ============================================

echo ""
echo "📄 2. Python скрипт үүсгэж байна..."

sudo cat > "$INSTALL_DIR/simulator.py" << 'EOF'
#!/usr/bin/env python3
"""
ДУЛААНЫ ДАХИН ДАМЖУУЛАХ ТӨВИЙН СИМУЛЯТОР
"""

import time
import json
import logging
import random
import math
import requests
from datetime import datetime
from typing import Dict
import signal
import sys

# ТОХИРГОО
class Config:
    DEVICE_ID = "SUBSTATION_01"
    LOCATION = "Улаанбаатар, Сүхбаатар дүүрэг"
    SERVER_URL = "http://localhost:3000/api/readings/batch"
    SEND_INTERVAL = 3
    LOG_FILE = "/var/log/heating_simulator/simulator.log"
    LOG_LEVEL = logging.INFO
    
    SENSORS = {
        'supply_temp': {'id': 0, 'name': 'Орох температур', 'type': 'temperature', 'unit': '°C', 'base': 75.0, 'variance': 5.0, 'min': 60.0, 'max': 95.0, 'trend_factor': 0.05},
        'return_temp': {'id': 1, 'name': 'Буцах температур', 'type': 'temperature', 'unit': '°C', 'base': 55.0, 'variance': 4.0, 'min': 45.0, 'max': 70.0, 'trend_factor': 0.05},
        'hot_water_temp': {'id': 2, 'name': 'Халуун усны температур', 'type': 'temperature', 'unit': '°C', 'base': 65.0, 'variance': 3.0, 'min': 55.0, 'max': 75.0, 'trend_factor': 0.03},
        'supply_pressure': {'id': 3, 'name': 'Орох даралт', 'type': 'pressure', 'unit': 'bar', 'base': 6.0, 'variance': 0.3, 'min': 5.0, 'max': 8.0, 'trend_factor': 0.02},
        'return_pressure': {'id': 4, 'name': 'Буцах даралт', 'type': 'pressure', 'unit': 'bar', 'base': 4.5, 'variance': 0.2, 'min': 3.5, 'max': 6.0, 'trend_factor': 0.02},
        'system_pressure': {'id': 5, 'name': 'Системийн даралт', 'type': 'pressure', 'unit': 'bar', 'base': 5.2, 'variance': 0.25, 'min': 4.0, 'max': 7.0, 'trend_factor': 0.02}
    }

def setup_logger():
    logger = logging.getLogger('HeatingSimulator')
    logger.setLevel(Config.LOG_LEVEL)
    file_handler = logging.FileHandler(Config.LOG_FILE)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

class SensorSimulator:
    def __init__(self):
        self.last_values = {k: v['base'] for k, v in Config.SENSORS.items()}
    
    def read_sensor(self, sensor_key: str) -> float:
        config = Config.SENSORS[sensor_key]
        hour = datetime.now().hour
        time_trend = math.sin((hour - 6) * math.pi / 12) * config['trend_factor']
        change = random.gauss(0, config['variance'] * 0.1)
        mean_pull = (config['base'] - self.last_values[sensor_key]) * 0.1
        new_value = self.last_values[sensor_key] + change + mean_pull + time_trend * config['base']
        new_value = max(config['min'], min(config['max'], new_value))
        self.last_values[sensor_key] = new_value
        return round(new_value, 2)
    
    def read_all_sensors(self) -> Dict[str, float]:
        return {k: self.read_sensor(k) for k in Config.SENSORS.keys()}

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
                'readings': [{'id': Config.SENSORS[k]['id'], 'name': k, 'v': v, 'unit': Config.SENSORS[k]['unit']} for k, v in readings.items()]
            }
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

class HeatingSubstationSimulator:
    def __init__(self):
        self.sensor_sim = SensorSimulator()
        self.data_sender = DataSender(Config.SERVER_URL)
        self.running = False
        self.iteration = 0
        logger.info("=" * 60)
        logger.info(f"СИМУЛЯТОР ЭХЭЛЛЭЭ - {Config.DEVICE_ID}")
        logger.info("=" * 60)
    
    def run(self):
        self.running = True
        try:
            while self.running:
                self.iteration += 1
                readings = self.sensor_sim.read_all_sensors()
                logger.info(f"📊 #{self.iteration}: {', '.join([f'{k}={v:.1f}' for k, v in readings.items()])}")
                self.data_sender.send(readings)
                time.sleep(Config.SEND_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Ctrl+C - зогсож байна")
            self.stop()
    
    def stop(self):
        self.running = False
        logger.info(f"ЗОГСЛОО: Амжилттай {self.data_sender.success_count}, Алдаа {self.data_sender.failed_count}")

simulator = None

def signal_handler(signum, frame):
    logger.info(f"Signal {signum} - зогсож байна")
    if simulator:
        simulator.stop()
    sys.exit(0)

def main():
    global simulator
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    simulator = HeatingSubstationSimulator()
    simulator.run()

if __name__ == "__main__":
    main()
EOF

sudo chmod +x "$INSTALL_DIR/simulator.py"
echo "✅ Python скрипт үүслээ"

# ============================================
# 3. SYSTEMD SERVICE ҮҮСГЭХ
# ============================================

echo ""
echo "⚙️  3. systemd service үүсгэж байна..."

sudo cat > /etc/systemd/system/heating-simulator.service << EOF
[Unit]
Description=Heating Substation Simulator
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/simulator.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd service үүслээ"

# ============================================
# 4. REQUIREMENTS СУУЛГАХ
# ============================================

echo ""
echo "📦 4. Python сангууд суулгаж байна..."

# Python3 болон pip шалгах


# requests санг суулгах
sudo pip3 install requests

echo "✅ Python сангууд суулгагдлаа"

# ============================================
# 5. ЭРХҮҮД ТОХИРУУЛАХ
# ============================================

echo ""
echo "🔒 5. Эрхүүд тохируулж байна..."

sudo chown -R root:root "$INSTALL_DIR"
sudo chmod 755 "$INSTALL_DIR"
sudo chmod +x "$INSTALL_DIR/simulator.py"
sudo chmod 644 /etc/systemd/system/heating-simulator.service

# Log хавтас эрх
sudo chown -R root:root /var/log/heating_simulator
sudo chmod 755 /var/log/heating_simulator

echo "✅ Эрхүүд тохирлоо"

# ============================================
# 6. SYSTEMD RELOAD
# ============================================

echo ""
echo "🔄 6. systemd reload хийж байна..."

sudo systemctl daemon-reload
sudo systemctl enable heating-simulator.service

echo "✅ systemd бэлэн"

# ============================================
# 7. ТОХИРГООНЫ ФАЙЛ ҮҮСГЭХ (Опци)
# ============================================

echo ""
echo "📝 7. Тохиргооны файл үүсгэж байна..."

sudo cat > "$INSTALL_DIR/config.json" << 'EOF'
{
  "device_id": "SUBSTATION_01",
  "location": "Улаанбаатар, Сүхбаатар дүүрэг",
  "server_url": "http://localhost:3000/api/readings/batch",
  "send_interval": 3,
  "sensors": {
    "supply_temp": {"base": 75.0, "min": 60.0, "max": 95.0},
    "return_temp": {"base": 55.0, "min": 45.0, "max": 70.0},
    "hot_water_temp": {"base": 65.0, "min": 55.0, "max": 75.0},
    "supply_pressure": {"base": 6.0, "min": 5.0, "max": 8.0},
    "return_pressure": {"base": 4.5, "min": 3.5, "max": 6.0},
    "system_pressure": {"base": 5.2, "min": 4.0, "max": 7.0}
  }
}
EOF

sudo chmod 644 "$INSTALL_DIR/config.json"

echo "✅ Тохиргооны файл үүслээ"

# ============================================
# ДУУССАН
# ============================================

echo ""
echo "================================================"
echo "✅ СУУЛГАЛТ АМЖИЛТТАЙ"
echo "================================================"
echo ""
echo "📂 Суулгасан байршил: $INSTALL_DIR"
echo "📄 Python скрипт:      $INSTALL_DIR/simulator.py"
echo "⚙️  Service файл:      /etc/systemd/system/heating-simulator.service"
echo "📝 Лог файл:           /var/log/heating_simulator/simulator.log"
echo ""
echo "================================================"
echo "КОМАНДУУД:"
echo "================================================"
echo ""
echo "# Service эхлүүлэх:"
echo "  sudo systemctl start heating-simulator"
echo ""
echo "# Service зогсоох:"
echo "  sudo systemctl stop heating-simulator"
echo ""
echo "# Service дахин эхлүүлэх:"
echo "  sudo systemctl restart heating-simulator"
echo ""
echo "# Статус харах:"
echo "  sudo systemctl status heating-simulator"
echo ""
echo "# Лог харах (бодит цагт):"
echo "  sudo journalctl -u heating-simulator -f"
echo ""
echo "# Лог файл харах:"
echo "  sudo tail -f /var/log/heating_simulator/simulator.log"
echo ""
echo "# Service идэвхжүүлэх (автомат эхлэх):"
echo "  sudo systemctl enable heating-simulator"
echo ""
echo "# Service идэвхгүй болгох:"
echo "  sudo systemctl disable heating-simulator"
echo ""
echo "================================================"
echo ""
echo "⚙️  ТОХИРГОО ӨӨРЧЛӨХ:"
echo ""
echo "1. Файл засах:"
echo "   sudo nano $INSTALL_DIR/simulator.py"
echo ""
echo "2. Сервер URL өөрчлөх (38-р мөр):"
echo "   SERVER_URL = \"http://YOUR_SERVER:3000/api/readings/batch\""
echo ""
echo "3. Төхөөрөмжийн ID өөрчлөх (36-р мөр):"
echo "   DEVICE_ID = \"SUBSTATION_02\""
echo ""
echo "4. Хадгалаад дахин эхлүүлэх:"
echo "   sudo systemctl restart heating-simulator"
echo ""
echo "================================================"
echo ""

# Одоо эхлүүлэх үү гэж асуух
read -p "Одоо service эхлүүлэх үү? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Service эхлүүлж байна..."
    sudo systemctl start heating-simulator
    sleep 2
    echo ""
    sudo systemctl status heating-simulator
fi

echo ""
echo "✅ Бэлэн!"