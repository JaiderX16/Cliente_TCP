from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, Endian
from datetime import datetime

# --- Parámetros de conexión ---
SENSOR_IP   = "192.168.0.101"
SENSOR_PORT = 502
SLAVE_ID    = 1

# --- Registros ---
ADDR_VELOCIDAD = 0     # Registro 40000 - Velocidad del aire (m/s)
ADDR_TEMPERATURA = 16  # Registro 40016 - Temperatura Transductor A (°C)

def main():
    client = ModbusTcpClient(host=SENSOR_IP, port=SENSOR_PORT)
    try:
        if not client.connect():
            print(f"❌ No se pudo conectar a {SENSOR_IP}:{SENSOR_PORT}")
            return

        print("\n=== DIAGNÓSTICO DEL SENSOR FLOWTRAX ===")
        print(f"Fecha y hora: {datetime.now():%Y-%m-%d %H:%M:%S}")
        
        # Leer registros crudos
        result_vel = client.read_holding_registers(address=ADDR_VELOCIDAD, count=2, slave=SLAVE_ID)
        result_temp = client.read_holding_registers(address=ADDR_TEMPERATURA, count=2, slave=SLAVE_ID)
        
        if not result_vel.isError() and not result_temp.isError():
            print(f"Registros crudos de velocidad: {result_vel.registers}")
            print(f"Registros crudos de temperatura: {result_temp.registers}")
            
            # Probar todas las combinaciones de endianness
            combinaciones = [
                (Endian.BIG, Endian.BIG, "Big-Big"),
                (Endian.BIG, Endian.LITTLE, "Big-Little"),
                (Endian.LITTLE, Endian.BIG, "Little-Big"),
                (Endian.LITTLE, Endian.LITTLE, "Little-Little")
            ]
            
            print("\n=== INTERPRETACIONES DE VELOCIDAD ===")
            for byte_order, word_order, nombre in combinaciones:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result_vel.registers,
                    byteorder=byte_order,
                    wordorder=word_order
                )
                valor = decoder.decode_32bit_float()
                print(f"{nombre}: {valor:.2f} m/s")
            
            print("\n=== INTERPRETACIONES DE TEMPERATURA ===")
            for byte_order, word_order, nombre in combinaciones:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result_temp.registers,
                    byteorder=byte_order,
                    wordorder=word_order
                )
                valor = decoder.decode_32bit_float()
                print(f"{nombre}: {valor:.2f} °C")
        else:
            print("❌ Error al leer registros")

    except Exception as e:
        print(f"⚠️ Error general: {e}")
    finally:
        client.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    main()