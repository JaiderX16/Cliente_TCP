from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, Endian
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import os
import json
import requests
import logging

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URLs de la API
API_BASE_URL = "https://apisensoresmina-production.up.railway.app/api"
API_VARIABLES_URL = f"{API_BASE_URL}/variables-entorno/2"
API_MEDICIONES_URL = f"{API_BASE_URL}/mediciones"
API_MEDICIONES_TIEMPO_REAL_URL = f"{API_BASE_URL}/mediciones-tiempo-real"

# Archivo para guardar la configuración
CONFIG_FILE = "config.json"

# Cargar configuración o usar valores predeterminados
def cargar_configuracion():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
    
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
        logger.error(f"Error al guardar configuración: {e}")
        return False

# Cargar configuración inicial
config = cargar_configuracion()

# --- Parámetros de conexión ---
SENSOR_IP = config["sensor_ip"]
SENSOR_PORT = config["sensor_port"]
SLAVE_ID = config["slave_id"]

# --- Registros según el mapa proporcionado ---
ADDR_VELOCIDAD = 0     
ADDR_TEMPERATURA_CLIMA = 25  

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
        logger.error(f"Error al leer {nombre}: {e}")
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

def obtener_datos_api():
    """Obtener datos de variables de entorno desde la API"""
    try:
        response = requests.get(API_VARIABLES_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error API GET: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener datos de API: {e}")
        return None

def actualizar_caudal_api(caudal_medido):
    """Actualizar el caudal medido en la API"""
    try:
        data = {"caudal_medido": caudal_medido}
        response = requests.patch(API_VARIABLES_URL, json=data, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"Caudal actualizado en API: {caudal_medido}")
            return True
        else:
            logger.error(f"Error API PATCH: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error al actualizar caudal en API: {e}")
        return False

def enviar_medicion_api(data):
    """Enviar medición completa a la API"""
    success_mediciones = False
    success_tiempo_real = False
    
    try:
        # 1. Enviar a la API de mediciones (POST - crear nuevo registro)
        response = requests.post(API_MEDICIONES_URL, json=data, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"Medición enviada a API mediciones: {data}")
            success_mediciones = True
        else:
            logger.error(f"Error API POST mediciones: {response.status_code}")
        
        # 2. Enviar a la API de mediciones en tiempo real (PUT - actualizar)
        tiempo_real_url = f"{API_BASE_URL}/mediciones-tiempo-real/2"  # URL fija para área 2
        response_tr = requests.put(tiempo_real_url, json=data, timeout=10)
        if response_tr.status_code in [200, 201, 204]:
            logger.info(f"Medición actualizada en API tiempo real: {data}")
            success_tiempo_real = True
        else:
            logger.error(f"Error API PUT mediciones tiempo real: {response_tr.status_code}")
        
        return success_mediciones and success_tiempo_real
    except Exception as e:
        logger.error(f"Error al enviar medición a APIs: {e}")
        return False

def procesar_y_enviar_datos(velocidad_ms, temperatura):
    """Procesar datos del sensor y enviarlos a la API"""
    try:
        # 1. Obtener datos iniciales de la API
        datos_api = obtener_datos_api()
        if not datos_api:
            logger.warning("No se pudieron obtener datos de la API, usando valores por defecto")
            superficie_area = 120.0  # Valor por defecto
            caudal_requerido = 50.0  # Valor por defecto
        else:
            superficie_area = float(datos_api.get('superficie_area', 120.0))
            caudal_requerido = float(datos_api.get('caudal_requerido', 50.0))

        # 2. Conversión de unidades (m/s a m/min)
        velocidad_convertida = velocidad_ms * 60

        # 3. Cálculo del caudal medido
        caudal_medido = velocidad_convertida * superficie_area

        # 4. Actualizar caudal en la base de datos
        actualizar_caudal_api(caudal_medido)

        # 5. Cálculo de cobertura
        if caudal_requerido > 0:
            cobertura = (caudal_medido / caudal_requerido) * 100
        else:
            cobertura = 0
            logger.warning("Caudal requerido es 0, cobertura establecida en 0%")

        # 6. Estructura de datos final
        medicion_data = {
            "area_id": 2,
            "temperature": temperatura,
            "velocity": velocidad_convertida,  # en m/min
            "flow": caudal_medido,
            "coverage": cobertura
        }

        # 7. Enviar resultados
        enviar_medicion_api(medicion_data)

        return {
            "superficie_area": superficie_area,
            "caudal_requerido": caudal_requerido,
            "velocidad_convertida": velocidad_convertida,
            "caudal_medido": caudal_medido,
            "cobertura": cobertura,
            "api_success": True
        }

    except Exception as e:
        logger.error(f"Error en procesamiento de datos: {e}")
        return {"api_success": False, "error": str(e)}

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
        "sensor_online": False,
        "nombre_area": "Área 2",
        "superficie": "120",
        "caudal_requerido": "50"
    }
    
    try:
        if not client.connect():
            datos["mensaje"] = f"No se pudo conectar a {SENSOR_IP}:{SENSOR_PORT}"
            return datos

        datos["sensor_online"] = True
        
        # Leer valores del sensor
        velocidad = leer_valor_float(client, ADDR_VELOCIDAD, "velocidad del aire")
        temperatura = leer_valor_float(client, ADDR_TEMPERATURA_CLIMA, "temperatura")
        
        if velocidad is not None:
            datos["velocidad"] = float(f"{velocidad:.2f}")
        
        if temperatura is not None:
            datos["temperatura"] = float(f"{temperatura:.2f}")
            
        # Procesar y enviar datos a la API si tenemos lecturas válidas
        if velocidad is not None and temperatura is not None:
            try:
                resultado_api = procesar_y_enviar_datos(velocidad, temperatura)
                if resultado_api.get("api_success"):
                    # Actualizar datos con información de la API
                    datos["superficie"] = str(int(resultado_api.get("superficie_area", 120)))
                    datos["caudal_requerido"] = str(int(resultado_api.get("caudal_requerido", 50)))
                    datos["caudal_medido"] = resultado_api.get("caudal_medido", 0)
                    datos["cobertura"] = resultado_api.get("cobertura", 0)
                    datos["velocidad_convertida"] = resultado_api.get("velocidad_convertida", 0)
                    logger.info("Datos procesados y enviados a API exitosamente")
                else:
                    logger.warning(f"Error en procesamiento API: {resultado_api.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error en procesamiento de datos para API: {e}")
            
        datos["estado"] = "ok"
        
    except Exception as e:
        datos["mensaje"] = f"Error general: {str(e)}"
    finally:
        client.close()
        
    return datos

@app.route('/')
def index():
    # Leer el archivo HTML directamente
    try:
        with open('./templates/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Error: Archivo paste.txt no encontrado"

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
    # Verificar que el archivo HTML exista
    if not os.path.exists('paste.txt'):
        logger.error("Error: Archivo paste.txt no encontrado. Asegúrate de que esté en el mismo directorio.")
        exit(1)
    
    logger.info("Iniciando servidor FlowTrax con integración API...")
    logger.info(f"API Base URL: {API_BASE_URL}")
    
    # Iniciar el servidor Flask
    app.run(debug=True, host='0.0.0.0', port=5000)