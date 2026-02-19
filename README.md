# Bot de Trading Bybit - Estrategia Bidireccional

Bot automatizado para Bybit Futures que implementa la estrategia nueva del gafas (el ejercicio).

## 📋 Descripción

Este bot ejecuta la siguiente estrategia:

1. **Coloca 2 órdenes limit simultáneamente:**
   - Orden de COMPRA al 1% por debajo del precio actual en el primer ciclo
   - Orden de VENTA al 1% por encima del precio actual en el primer ciclo
   - Orden de COMPRA al 2% por encima del precio actual en el segundo ciclo
   - Orden de VENTA al 2% por encima del precio actual en el segundo ciclo

2. **Cuando una orden se ejecuta:**
   - Cancela automáticamente la orden contraria
   - Ya tiene configurado el Stop Loss al 1% de distancia
   - Coloca un Take Profit del 2% como "reduce only"

3. **Gestión de riesgo:**
   - Tamaño de posición: $50 USD
   - Stop Loss: 1% de la entrada
   - Take Profit: 2% de la entrada
   - Apalancamiento configurable (default: 10x)

## 🚀 Instalación

### Requisitos previos
- Python 3.9.1 o superior
- Cuenta en Bybit (Testnet o Mainnet)
- API Keys generadas

### Paso 1: Clonar o descargar los archivos

Necesitas los siguientes archivos:
- `bybit_bot.py` - Script principal del bot
- `config.py` - Archivo de configuración
- `requirements.txt` - Dependencias

### Paso 2: Instalar dependencias

```bash
pip install pybit
```

### Paso 3: Generar API Keys

**Para Testnet (recomendado para pruebas):**
1. Ir a: https://testnet.bybit.com/app/user/api-management
2. Crear nueva API Key
3. Habilitar permisos: `Trade` y `Read`
4. Guardar API Key y Secret (no se pueden recuperar después)

**Para Mainnet (cuenta real):**
1. Ir a: https://www.bybit.com/app/user/api-management
2. Seguir los mismos pasos que testnet
3. ⚠️ **IMPORTANTE:** Configurar whitelist de IP para mayor seguridad

### Paso 4: Configurar el bot

**1. Configurar API Keys en `config.py`:**

```python
# Configuración de API de Bybit
api_key = "TU_API_KEY_AQUI"  # ← Colocar tu API key
api_secret = "TU_API_SECRET_AQUI"  # ← Colocar tu API secret
```

**2. Ajustar parámetros del bot en `bybit_bot.py`:**

Al inicio del archivo `bybit_bot.py` encontrarás la sección de configuración:

```python
# ============================================================
# CONFIGURACIÓN DEL BOT
# ============================================================

# Configuración general
TESTNET = True  # False para cuenta real
SYMBOL = "BTCUSDT"  # Moneda a operar
CATEGORY = "linear"  # Tipo de contrato

# Parámetros de trading
POSITION_SIZE_USD = 50  # Tamaño en USD
DISTANCE_PERCENT = 1.0  # Distancia de órdenes (1%)
STOP_LOSS_PERCENT = 1.0  # Stop loss (1%)
TAKE_PROFIT_PERCENT = 2.0  # Take profit (2%)

# Apalancamiento
LEVERAGE = 10

# Monitoreo
CHECK_INTERVAL = 5  # Segundos entre revisiones
```

**Nota:** Si usas `monitor_positions.py`, también debes ajustar las constantes de configuración en ese archivo.

## ▶️ Uso

### Ejecutar el bot

```bash
python bybit_bot.py
```

### Flujo de ejecución

1. El bot se conecta a Bybit
2. Obtiene el precio actual de la moneda configurada
3. Calcula los precios de las órdenes limit
4. Coloca ambas órdenes con SL configurado
5. Monitorea las órdenes cada 5 segundos
6. Cuando una se ejecuta:
   - Cancela la orden opuesta
   - Configura el TP como reduce only
7. La posición queda abierta con SL y TP

### Ejemplo de salida

```
============================================================
  BOT DE TRADING BYBIT - ESTRATEGIA BIDIRECCIONAL
============================================================

2025-02-11 10:30:45 - INFO - ============================================================
2025-02-11 10:30:45 - INFO - BOT DE TRADING BYBIT INICIADO
2025-02-11 10:30:45 - INFO - Modo: TESTNET
2025-02-11 10:30:45 - INFO - Símbolo: BTCUSDT
2025-02-11 10:30:45 - INFO - Tamaño de posición: $50
2025-02-11 10:30:45 - INFO - ============================================================
2025-02-11 10:30:46 - INFO - 💰 Precio actual de BTCUSDT: $50,000.00
2025-02-11 10:30:46 - INFO - ✅ Apalancamiento configurado: 10x
2025-02-11 10:30:46 - INFO - ============================================================
2025-02-11 10:30:46 - INFO - 📊 CONFIGURACIÓN DE ÓRDENES:
2025-02-11 10:30:46 - INFO - Precio actual: $50,000.00
2025-02-11 10:30:46 - INFO - ------------------------------------------------------------
2025-02-11 10:30:46 - INFO - 🟢 ORDEN DE COMPRA (BUY):
2025-02-11 10:30:46 - INFO -    Precio entrada: $49,500.00 (1.0% abajo)
2025-02-11 10:30:46 - INFO -    Cantidad: 0.001
2025-02-11 10:30:46 - INFO -    Stop Loss: $49,005.00 (1.0% abajo)
2025-02-11 10:30:46 - INFO -    Take Profit: $50,490.00 (2.0% arriba)
2025-02-11 10:30:46 - INFO - ------------------------------------------------------------
2025-02-11 10:30:46 - INFO - 🔴 ORDEN DE VENTA (SELL):
2025-02-11 10:30:46 - INFO -    Precio entrada: $50,500.00 (1.0% arriba)
2025-02-11 10:30:46 - INFO -    Cantidad: 0.001
2025-02-11 10:30:46 - INFO -    Stop Loss: $51,005.00 (1.0% arriba)
2025-02-11 10:30:46 - INFO -    Take Profit: $49,490.00 (2.0% abajo)
2025-02-11 10:30:46 - INFO - ============================================================
2025-02-11 10:30:47 - INFO - 📤 Colocando orden de COMPRA...
2025-02-11 10:30:47 - INFO - ✅ Orden de COMPRA colocada: abc123def456
2025-02-11 10:30:47 - INFO - 📤 Colocando orden de VENTA...
2025-02-11 10:30:48 - INFO - ✅ Orden de VENTA colocada: xyz789uvw012
2025-02-11 10:30:48 - INFO - ✅ Ambas órdenes colocadas exitosamente
2025-02-11 10:30:48 - INFO - 👀 Iniciando monitoreo de órdenes...
2025-02-11 10:30:48 - INFO - Revisando cada 5 segundos...
```

## 📊 Características

### ✅ Implementadas
- ✅ Órdenes limit bidireccionales
- ✅ Cálculo automático de cantidades basado en USDT
- ✅ Stop Loss configurado directamente en la orden
- ✅ Take Profit como reduce only
- ✅ Cancelación automática de orden opuesta
- ✅ Redondeo correcto de precios y cantidades
- ✅ Logging detallado
- ✅ Manejo de errores robusto
- ✅ Apalancamiento configurable
- ✅ Soporte para Testnet y Mainnet

### 🔧 Configuración personalizable
- Símbolo a operar (BTCUSDT, ETHUSDT, etc.)
- Tamaño de posición en USD
- Porcentaje de distancia de órdenes
- Porcentaje de Stop Loss
- Porcentaje de Take Profit
- Apalancamiento
- Intervalo de monitoreo
