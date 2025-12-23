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
sudo cp simulator.py "$INSTALL_DIR/simulator.py"
sudo chmod +x "$INSTALL_DIR/simulator.py"
echo "✅ Python скрипт үүслээ"

# ============================================
# 3. SYSTEMD SERVICE ҮҮСГЭХ
# ============================================
VENV_PATH=$INSTALL_DIR/.venv
Project_DIR=$(pwd)

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
ExecStart=$VENV_PATH/bin/python $INSTALL_DIR/simulator.py
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
sudo apt update
sudo apt install -y python3-venv python3-pip

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

# 3. Install Python packages inside the venv
# Note: Pointing directly to the venv pip avoids needing to 'activate' the script
echo "Installing Python packages..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install requests
# Activate the virtual environment
source "$VENV_PATH/bin/activate"



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