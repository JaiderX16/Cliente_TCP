// Variables globales
const MAX_HISTORIAL = 10;
let historialLecturas = [];
let intervaloActualizacion = null;

// Elementos del DOM
const velocidadValor = document.getElementById('velocidad-valor');
const velocidadBarra = document.getElementById('velocidad-barra');
const temperaturaValor = document.getElementById('temperatura-valor');
const temperaturaBarra = document.getElementById('temperatura-barra');
const timestamp = document.getElementById('timestamp');
const estadoConexion = document.getElementById('estado-conexion');
const btnActualizar = document.getElementById('btn-actualizar');
const mensajeError = document.getElementById('mensaje-error');

// Elementos de configuración
const sensorIp = document.getElementById('sensor-ip');
const sensorPort = document.getElementById('sensor-port');
const slaveId = document.getElementById('slave-id');
const btnVerificar = document.getElementById('btn-verificar');
const btnGuardar = document.getElementById('btn-guardar');
const sensorStatus = document.getElementById('sensor-status');
const configMensaje = document.getElementById('config-mensaje');

// Elementos de actualización automática
const autoRefresh = document.getElementById('auto-refresh');
const refreshInterval = document.getElementById('refresh-interval');
const statusIndicator = document.getElementById('status-indicator');
const indicatorContainer = document.getElementById('indicator-container');

// Función para cargar la configuración actual
async function cargarConfiguracion() {
    try {
        const response = await fetch('/api/configuracion');
        const config = await response.json();
        
        // Actualizar campos del formulario
        sensorIp.value = config.sensor_ip || '';
        sensorPort.value = config.sensor_port || '';
        slaveId.value = config.slave_id || '';
        
        // Verificar conexión
        verificarConexion();
    } catch (error) {
        console.error('Error al cargar configuración:', error);
        mostrarMensajeConfig('Error al cargar la configuración', 'error');
    }
}

// Función para guardar la configuración
async function guardarConfiguracion() {
    try {
        // Deshabilitar botón mientras se guarda
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Guardando...';
        
        // Preparar datos
        const config = {
            sensor_ip: sensorIp.value,
            sensor_port: parseInt(sensorPort.value),
            slave_id: parseInt(slaveId.value)
        };
        
        // Enviar al servidor
        const response = await fetch('/api/configuracion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const resultado = await response.json();
        
        if (resultado.success) {
            mostrarMensajeConfig(resultado.mensaje, 'success');
            actualizarEstadoSensor(resultado.sensor_online);
            
            // Actualizar datos
            obtenerDatos();
        } else {
            mostrarMensajeConfig(resultado.mensaje, 'error');
        }
    } catch (error) {
        console.error('Error al guardar configuración:', error);
        mostrarMensajeConfig('Error al guardar la configuración', 'error');
    } finally {
        // Restaurar botón
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="fas fa-save mr-1"></i> Guardar Configuración';
    }
}

// Función para verificar la conexión con el sensor
async function verificarConexion() {
    try {
        // Cambiar estado del botón
        btnVerificar.disabled = true;
        btnVerificar.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Verificando...';
        
        // Consultar API
        const response = await fetch('/api/verificar-conexion');
        const data = await response.json();
        
        // Actualizar estado
        actualizarEstadoSensor(data.online);
    } catch (error) {
        console.error('Error al verificar conexión:', error);
        actualizarEstadoSensor(false);
    } finally {
        // Restaurar botón
        btnVerificar.disabled = false;
        btnVerificar.innerHTML = '<i class="fas fa-sync-alt mr-1"></i> Verificar Conexión';
    }
}

// Función para actualizar el indicador de estado del sensor
function actualizarEstadoSensor(online) {
    if (online) {
        sensorStatus.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
        sensorStatus.innerHTML = '<i class="fas fa-circle text-green-500 mr-1"></i> En línea';
    } else {
        sensorStatus.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800';
        sensorStatus.innerHTML = '<i class="fas fa-circle text-red-500 mr-1"></i> Desconectado';
    }
}

// Función para mostrar mensajes en el panel de configuración
function mostrarMensajeConfig(mensaje, tipo) {
    configMensaje.textContent = mensaje;
    configMensaje.classList.remove('hidden');
    
    if (tipo === 'success') {
        configMensaje.className = 'mt-4 p-3 bg-green-100 text-green-700 rounded-lg';
    } else {
        configMensaje.className = 'mt-4 p-3 bg-red-100 text-red-700 rounded-lg';
    }
    
    // Ocultar después de 5 segundos
    setTimeout(() => {
        configMensaje.classList.add('hidden');
    }, 5000);
}

// Función para obtener datos del sensor
async function obtenerDatos() {
    try {
        // Mostrar indicador de carga
        btnActualizar.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Cargando...';
        btnActualizar.disabled = true;
        
        const response = await fetch('/api/lecturas');
        const datos = await response.json();
        
        // Actualizar la interfaz con los datos recibidos
        actualizarInterfaz(datos);
        
        // Actualizar estado del sensor
        actualizarEstadoSensor(datos.sensor_online);
    } catch (error) {
        console.error('Error al obtener datos:', error);
        mostrarError('Error de conexión con el servidor');
    } finally {
        // Restaurar botón
        btnActualizar.innerHTML = '<i class="fas fa-sync-alt mr-2"></i> Actualizar Datos';
        btnActualizar.disabled = false;
    }
}

// Función para actualizar la interfaz con los datos recibidos
function actualizarInterfaz(datos) {
    // Actualizar valores
    velocidadValor.textContent = datos.velocidad ? datos.velocidad.toFixed(2) : '--';
    temperaturaValor.textContent = datos.temperatura ? datos.temperatura.toFixed(2) : '--';
    
    // Actualizar barras de progreso (asumiendo valores máximos)
    const maxVelocidad = 30; // m/s
    const maxTemperatura = 100; // °C
    
    if (datos.velocidad) {
        const porcentajeVelocidad = Math.min(100, (datos.velocidad / maxVelocidad) * 100);
        velocidadBarra.style.width = `${porcentajeVelocidad}%`;
    } else {
        velocidadBarra.style.width = '0%';
    }
    
    if (datos.temperatura) {
        const porcentajeTemperatura = Math.min(100, (datos.temperatura / maxTemperatura) * 100);
        temperaturaBarra.style.width = `${porcentajeTemperatura}%`;
    } else {
        temperaturaBarra.style.width = '0%';
    }
    
    // Actualizar timestamp y estado
    timestamp.textContent = datos.timestamp || '--';
    estadoConexion.textContent = datos.sensor_online ? 'Conectado' : 'Desconectado';
    estadoConexion.className = datos.sensor_online ? 'font-medium text-green-600' : 'font-medium text-red-600';
    
    // Ocultar mensaje de error si existe
    mensajeError.classList.add('hidden');
}

// Función para mostrar mensajes de error
function mostrarError(mensaje) {
    mensajeError.textContent = mensaje;
    mensajeError.classList.remove('hidden');
}

// Función para iniciar/detener la actualización automática
function toggleAutoRefresh() {
    if (autoRefresh.checked) {
        // Cambiar color del indicador a azul
        statusIndicator.classList.remove('bg-red-600');
        statusIndicator.classList.add('bg-osinergmin-blue');
        
        // Obtener el intervalo en segundos y convertirlo a milisegundos
        const intervalo = parseInt(refreshInterval.value) * 1000;
        
        // Validar el intervalo (mínimo 5 segundos)
        if (intervalo < 5000) {
            refreshInterval.value = 5;
            intervalo = 5000;
        }
        
        // Detener cualquier intervalo existente
        if (intervaloActualizacion) {
            clearInterval(intervaloActualizacion);
        }
        
        // Iniciar nuevo intervalo
        intervaloActualizacion = setInterval(obtenerDatos, intervalo);
        console.log(`Actualización automática activada cada ${refreshInterval.value} segundos`);
    } else {
        // Cambiar color del indicador a rojo
        statusIndicator.classList.remove('bg-osinergmin-blue');
        statusIndicator.classList.add('bg-red-600');
        
        // Detener intervalo
        if (intervaloActualizacion) {
            clearInterval(intervaloActualizacion);
            intervaloActualizacion = null;
            console.log('Actualización automática desactivada');
        }
    }
}

// Configurar eventos
btnActualizar.addEventListener('click', obtenerDatos);
btnVerificar.addEventListener('click', verificarConexion);
btnGuardar.addEventListener('click', guardarConfiguracion);
autoRefresh.addEventListener('change', toggleAutoRefresh);
indicatorContainer.addEventListener('click', function() {
    autoRefresh.checked = !autoRefresh.checked;
    toggleAutoRefresh();
});
refreshInterval.addEventListener('change', function() {
    // Si la actualización automática está activada, reiniciarla con el nuevo intervalo
    if (autoRefresh.checked) {
        toggleAutoRefresh();
    }
});

// Cargar datos iniciales
document.addEventListener('DOMContentLoaded', () => {
    // Cargar configuración
    cargarConfiguracion();
    
    // Cargar datos iniciales
    obtenerDatos();
});