from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, Endian
from datetime import datetime

# --- Parámetros de conexión ---
SENSOR_IP   = "192.168.0.101"
SENSOR_PORT = 502
SLAVE_ID    = 1

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

def main():
    client = ModbusTcpClient(host=SENSOR_IP, port=SENSOR_PORT)
    try:
        if not client.connect():
            print(f"❌ No se pudo conectar a {SENSOR_IP}:{SENSOR_PORT}")
            return

        # Leer valores
        velocidad = leer_valor_float(client, ADDR_VELOCIDAD, "velocidad del aire")
        temperatura = leer_valor_float(client, ADDR_TEMPERATURA_CLIMA, "temperatura")
        
        # Mostrar resultados
        print("\n=== LECTURAS DEL SENSOR FLOWTRAX ===")
        print(f"Fecha y hora: {datetime.now():%Y-%m-%d %H:%M:%S}")
        
        if velocidad is not None:
            print(f"📊 Velocidad del aire: {velocidad:.2f} m/s")
        
        if temperatura is not None:
            print(f"🌡️ Temperatura (Climate Probe): {temperatura:.2f} °C")

    except Exception as e:
        print(f"⚠️ Error general: {e}")
    finally:
        client.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    main()
