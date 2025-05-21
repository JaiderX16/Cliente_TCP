from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, Endian
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import os
import json

app = Flask(__name__)

# Archivo para guardar la configuración
CONFIG_FILE = "config.json"

# Cargar configuración o usar valores predeterminados
def cargar_configuracion():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error al cargar configuración: {e}")
    
    # Valores predeterminados
    return {
        "sensor_ip": "192.168.0.101",
        "sensor_port": 502,
        "slave_id": 1
    }

# Guardar configuración
def guardar_configuracion(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False

# Cargar configuración inicial
config = cargar_configuracion()

# --- Parámetros de conexión ---
SENSOR_IP = config["sensor_ip"]
SENSOR_PORT = config["sensor_port"]
SLAVE_ID = config["slave_id"]

# --- Registros según el mapa proporcionado ---
# Para registros Modbus, la dirección real = número de registro - 40001
# Registro 40000 → dirección 0 (Velocidad del aire en m/s)
# Registro 40026 → dirección 25 (Temperatura Climate Probe 1 en °C)
ADDR_VELOCIDAD = 0     
ADDR_TEMPERATURA_CLIMA = 25  # Climate Probe 1 (registro 40026)

def leer_valor_float(client, direccion, nombre):
    try:
        # Leer 2 registros (32 bits float)
        result = client.read_holding_registers(address=direccion, count=2, slave=SLAVE_ID)
        if result.isError():
            raise Exception(f"Error Modbus: {result}")
        
        # Usar Big-Little endianness para todos los valores
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers,
            byteorder=Endian.BIG,
            wordorder=Endian.LITTLE
        )
        return decoder.decode_32bit_float()
    except Exception as e:
        print(f"❌ Error al leer {nombre}: {e}")
        return None

def verificar_conexion():
    client = ModbusTcpClient(host=SENSOR_IP, port=SENSOR_PORT)
    try:
        if client.connect():
            client.close()
            return True
        return False
    except:
        return False

def obtener_lecturas():
    global SENSOR_IP, SENSOR_PORT, SLAVE_ID
    
    # Recargar configuración actual
    config = cargar_configuracion()
    SENSOR_IP = config["sensor_ip"]
    SENSOR_PORT = config["sensor_port"]
    SLAVE_ID = config["slave_id"]
    
    client = ModbusTcpClient(host=SENSOR_IP, port=SENSOR_PORT)
    datos = {
        "velocidad": None,
        "temperatura": None,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "error",
        "mensaje": "",
        "sensor_online": False
    }
    
    try:
        if not client.connect():
            datos["mensaje"] = f"No se pudo conectar a {SENSOR_IP}:{SENSOR_PORT}"
            return datos

        datos["sensor_online"] = True
        
        # Leer valores
        velocidad = leer_valor_float(client, ADDR_VELOCIDAD, "velocidad del aire")
        temperatura = leer_valor_float(client, ADDR_TEMPERATURA_CLIMA, "temperatura")
        
        if velocidad is not None:
            datos["velocidad"] = float(f"{velocidad:.2f}")
        
        if temperatura is not None:
            datos["temperatura"] = float(f"{temperatura:.2f}")
            
        datos["estado"] = "ok"
        
    except Exception as e:
        datos["mensaje"] = f"Error general: {str(e)}"
    finally:
        client.close()
        
    return datos

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lecturas')
def api_lecturas():
    return jsonify(obtener_lecturas())

@app.route('/api/configuracion', methods=['GET'])
def get_configuracion():
    return jsonify(cargar_configuracion())

@app.route('/api/configuracion', methods=['POST'])
def update_configuracion():
    try:
        nueva_config = request.json
        
        # Validar datos
        if not isinstance(nueva_config.get("sensor_ip"), str) or not nueva_config.get("sensor_ip"):
            return jsonify({"success": False, "mensaje": "Dirección IP inválida"}), 400
            
        try:
            port = int(nueva_config.get("sensor_port"))
            if port <= 0 or port > 65535:
                raise ValueError("Puerto fuera de rango")
            nueva_config["sensor_port"] = port
        except:
            return jsonify({"success": False, "mensaje": "Puerto inválido"}), 400
            
        try:
            slave_id = int(nueva_config.get("slave_id"))
            if slave_id <= 0 or slave_id > 255:
                raise ValueError("ID de esclavo fuera de rango")
            nueva_config["slave_id"] = slave_id
        except:
            return jsonify({"success": False, "mensaje": "ID de esclavo inválido"}), 400
        
        # Guardar configuración
        if guardar_configuracion(nueva_config):
            # Actualizar variables globales
            global SENSOR_IP, SENSOR_PORT, SLAVE_ID
            SENSOR_IP = nueva_config["sensor_ip"]
            SENSOR_PORT = nueva_config["sensor_port"]
            SLAVE_ID = nueva_config["slave_id"]
            
            # Verificar conexión con la nueva configuración
            online = verificar_conexion()
            
            return jsonify({
                "success": True, 
                "mensaje": "Configuración actualizada correctamente",
                "sensor_online": online
            })
        else:
            return jsonify({"success": False, "mensaje": "Error al guardar la configuración"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"Error: {str(e)}"}), 500

@app.route('/api/verificar-conexion')
def api_verificar_conexion():
    return jsonify({"online": verificar_conexion()})

if __name__ == "__main__":
    # Asegurarse de que existan las carpetas necesarias
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    
    # Iniciar el servidor Flask
    app.run(debug=True, host='0.0.0.0', port=5000)
