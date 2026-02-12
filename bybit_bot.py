import config
import time
from pybit.unified_trading import HTTP
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
import threading
import telebot
from typing import Dict, Optional

# Inicializar sesión de Bybit
session = HTTP(
    testnet=config.TESTNET,
    api_key=config.api_key,
    api_secret=config.api_secret,
)

# ==================== CONFIGURACIÓN DEL BOT ====================
SYMBOLS = ["LINKUSDT"]  # Símbolos a operar
AMOUNT_USDT = Decimal(20)  # Monto en USDT por orden
DISTANCE_1_PERCENTAGE = Decimal(1) / Decimal(100)  # 1% de distancia primer ciclo
DISTANCE_2_PERCENTAGE = Decimal(2.5) / Decimal(100)  # 2.5% de distancia segundo ciclo
STOP_LOSS_PERCENTAGE = Decimal(1) / Decimal(100)  # 1% de stop loss
TAKE_PROFIT_PERCENTAGE = Decimal(2) / Decimal(100)  # 1% de take profit

# Telegram Bot
bot_token = config.token_telegram
bot = telebot.TeleBot(bot_token)
chat_id = config.chat_id

# Control de órdenes activas y ciclos
active_orders = {}  # {symbol: {'long_order_id': '', 'short_order_id': '', 'has_position': False}}
cycle_control = {}  # {symbol: 'distance_1' o 'distance_2'} para alternar distancias

# ==================== FUNCIONES DE TELEGRAM ====================
def enviar_mensaje_telegram(mensaje):
    """Envía mensaje a Telegram"""
    try:
        bot.send_message(chat_id, mensaje, parse_mode='HTML')
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

# ==================== FUNCIONES AUXILIARES ====================
def adjust_price(symbol, price):
    """Ajusta el precio según el tick size del símbolo"""
    try:
        instrument_info = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = Decimal(instrument_info['result']['list'][0]['priceFilter']['tickSize'])
        price_decimal = Decimal(str(price))
        adjusted_price = (price_decimal / tick_size).quantize(Decimal('1'), rounding=ROUND_FLOOR) * tick_size
        return str(adjusted_price)
    except Exception as e:
        print(f"Error al ajustar el precio para {symbol}: {e}")
        return str(price)

def adjust_quantity(symbol, quantity):
    """Ajusta la cantidad según el qty step del símbolo"""
    try:
        instrument_info = session.get_instruments_info(category="linear", symbol=symbol)
        qty_step = Decimal(instrument_info['result']['list'][0]['lotSizeFilter']['qtyStep'])
        quantity_decimal = Decimal(str(quantity))
        
        # Redondear hacia abajo según el qty_step
        adjusted_qty = (quantity_decimal / qty_step).quantize(Decimal('1'), rounding=ROUND_FLOOR) * qty_step
        
        # Determinar el número de decimales
        qty_step_str = str(qty_step)
        if '.' in qty_step_str:
            decimals = len(qty_step_str.split('.')[1])
            return str(round(float(adjusted_qty), decimals))
        else:
            return str(int(adjusted_qty))
    except Exception as e:
        print(f"Error al ajustar cantidad para {symbol}: {e}")
        return str(quantity)

def get_current_price(symbol):
    """Obtiene el precio actual del mercado"""
    try:
        tickers = session.get_tickers(symbol=symbol, category="linear")
        last_price = Decimal(tickers["result"]["list"][0]["lastPrice"])
        return last_price
    except Exception as e:
        print(f"Error al obtener precio actual de {symbol}: {e}")
        return None

def calculate_quantity(symbol, amount_usdt):
    """Calcula la cantidad a operar basado en el monto en USDT"""
    try:
        current_price = get_current_price(symbol)
        if current_price is None:
            return None
        
        quantity = amount_usdt / current_price
        adjusted_qty = adjust_quantity(symbol, quantity)
        return adjusted_qty
    except Exception as e:
        print(f"Error al calcular cantidad para {symbol}: {e}")
        return None

def get_open_orders(symbol):
    """Obtiene las órdenes abiertas de un símbolo"""
    try:
        response = session.get_open_orders(category="linear", symbol=symbol)
        if response['retCode'] == 0:
            return response['result']['list']
        return []
    except Exception as e:
        print(f"Error al obtener órdenes abiertas de {symbol}: {e}")
        return []

def get_position(symbol):
    """Obtiene la posición actual de un símbolo"""
    try:
        response = session.get_positions(category="linear", symbol=symbol)
        if response['retCode'] == 0:
            positions = response['result']['list']
            if positions and Decimal(positions[0]['size']) != 0:
                return positions[0]
        return None
    except Exception as e:
        print(f"Error al obtener posición de {symbol}: {e}")
        return None

def cancel_order(symbol, order_id):
    """Cancela una orden específica"""
    try:
        response = session.cancel_order(
            category="linear",
            symbol=symbol,
            orderId=order_id
        )
        if response['retCode'] == 0:
            print(f"Orden {order_id} cancelada exitosamente para {symbol}")
            return True
        else:
            print(f"Error al cancelar orden {order_id}: {response['retMsg']}")
            return False
    except Exception as e:
        print(f"Error al cancelar orden {order_id} de {symbol}: {e}")
        return False
    
def get_pnl(symbol):
    closed_orders_response = session.get_closed_pnl(category="linear", symbol=symbol, limit=1)
    closed_orders_list = closed_orders_response['result']['list']

    for order in closed_orders_list:
        pnl_cerrada = float(order['closedPnl'])
        emoji = "✅" if pnl_cerrada >= 0 else "❌"
        mensaje_pnl = (
            f"<b>{emoji} PNL Realizado</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Resultado:</b> {pnl_cerrada:.2f} USDT\n"
            f"━━━━━━━━━━━━━━━"
        )
        enviar_mensaje_telegram(mensaje_pnl)
        print(mensaje_pnl)

# ==================== FUNCIONES PRINCIPALES ====================
def place_limit_orders_with_sl(symbol, distance_percentage=None):
    """
    Coloca dos órdenes limit (long y short) a la distancia especificada del precio actual,
    cada una con su stop loss al 1%
    
    Args:
        symbol: Símbolo a operar
        distance_percentage: Distancia personalizada (si es None, usa el ciclo actual)
    """
    try:
        # Verificar si ya hay órdenes activas para este símbolo
        if symbol in active_orders and active_orders[symbol].get('has_position', False):
            print(f"Ya hay una posición activa para {symbol}. No se colocarán nuevas órdenes.")
            return
        
        # Determinar la distancia a usar
        if distance_percentage is None:
            # Usar el ciclo guardado o iniciar en distance_1
            if symbol not in cycle_control:
                cycle_control[symbol] = 'distance_1'
            
            if cycle_control[symbol] == 'distance_1':
                distance_percentage = DISTANCE_1_PERCENTAGE
                cycle_name = "1%"
            else:
                distance_percentage = DISTANCE_2_PERCENTAGE
                cycle_name = "2.5%"
        else:
            cycle_name = f"{distance_percentage * 100}%"
        
        # Obtener precio actual
        current_price = get_current_price(symbol)
        if current_price is None:
            print(f"No se pudo obtener el precio actual de {symbol}")
            return
        
        # Calcular cantidad
        quantity = calculate_quantity(symbol, AMOUNT_USDT)
        if quantity is None:
            print(f"No se pudo calcular la cantidad para {symbol}")
            return
        
        # Calcular precios de las órdenes limit
        long_price = current_price * (Decimal(1) - distance_percentage)
        short_price = current_price * (Decimal(1) + distance_percentage)
        
        # Calcular precios de stop loss
        long_sl_price = long_price * (Decimal(1) - STOP_LOSS_PERCENTAGE)
        short_sl_price = short_price * (Decimal(1) + STOP_LOSS_PERCENTAGE)
        
        # Ajustar precios
        long_price_adjusted = adjust_price(symbol, long_price)
        short_price_adjusted = adjust_price(symbol, short_price)
        long_sl_adjusted = adjust_price(symbol, long_sl_price)
        short_sl_adjusted = adjust_price(symbol, short_sl_price)
        
        print(f"\n{'='*60}")
        print(f"🔄 Ciclo actual: {cycle_name}")
        print(f"Colocando órdenes para {symbol}")
        print(f"Precio actual: {current_price}")
        print(f"Cantidad: {quantity}")
        print(f"\nORDEN LONG:")
        print(f"  - Precio Limit: {long_price_adjusted}")
        print(f"  - Stop Loss: {long_sl_adjusted}")
        print(f"\nORDEN SHORT:")
        print(f"  - Precio Limit: {short_price_adjusted}")
        print(f"  - Stop Loss: {short_sl_adjusted}")
        print(f"{'='*60}\n")
        
        # Colocar orden LONG con stop loss
        try:
            long_order = session.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                orderType="Limit",
                qty=quantity,
                price=long_price_adjusted,
                timeInForce="GTC",
                stopLoss=long_sl_adjusted,
                slOrderType="Market",
                slTriggerBy="LastPrice",
                tpslMode="Full"
            )
            
            if long_order['retCode'] == 0:
                long_order_id = long_order['result']['orderId']
                print(f"✅ Orden LONG colocada: ID {long_order_id}")
            else:
                print(f"❌ Error al colocar orden LONG: {long_order['retMsg']}")
                long_order_id = None
        except Exception as e:
            print(f"❌ Error al colocar orden LONG: {e}")
            long_order_id = None
        
        # Colocar orden SHORT con stop loss
        try:
            short_order = session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                orderType="Limit",
                qty=quantity,
                price=short_price_adjusted,
                timeInForce="GTC",
                stopLoss=short_sl_adjusted,
                slOrderType="Market",
                slTriggerBy="LastPrice",
                tpslMode="Full"
            )
            
            if short_order['retCode'] == 0:
                short_order_id = short_order['result']['orderId']
                print(f"✅ Orden SHORT colocada: ID {short_order_id}")
            else:
                print(f"❌ Error al colocar orden SHORT: {short_order['retMsg']}")
                short_order_id = None
        except Exception as e:
            print(f"❌ Error al colocar orden SHORT: {e}")
            short_order_id = None
        
        # Guardar IDs de órdenes
        if long_order_id or short_order_id:
            active_orders[symbol] = {
                'long_order_id': long_order_id,
                'short_order_id': short_order_id,
                'has_position': False
            }
            
            # Mensaje de Telegram
            mensaje = (
                f"<b>🎯 Órdenes colocadas para {symbol}</b>\n\n"
                f"🔄 <b>Ciclo: {cycle_name}</b>\n"
                f"💰 Precio actual: <b>${current_price}</b>\n"
                f"📊 Cantidad: <b>{quantity}</b>\n\n"
                f"<b>🟢 ORDEN LONG:</b>\n"
                f"  └ Precio: ${long_price_adjusted}\n"
                f"  └ Stop Loss: ${long_sl_adjusted}\n\n"
                f"<b>🔴 ORDEN SHORT:</b>\n"
                f"  └ Precio: ${short_price_adjusted}\n"
                f"  └ Stop Loss: ${short_sl_adjusted}\n\n"
                f"✅ Estado: Órdenes activas"
            )
            enviar_mensaje_telegram(mensaje)
        
    except Exception as e:
        print(f"Error en place_limit_orders_with_sl para {symbol}: {e}")

def place_take_profit(symbol, side, entry_price, quantity):
    """
    Coloca una orden take profit reduce only después de que se abre una posición
    """
    try:
        # Calcular precio del take profit
        if side == "Buy":
            tp_price = Decimal(entry_price) * (Decimal(1) + TAKE_PROFIT_PERCENTAGE)
        else:  # Sell
            tp_price = Decimal(entry_price) * (Decimal(1) - TAKE_PROFIT_PERCENTAGE)
        
        tp_price_adjusted = adjust_price(symbol, tp_price)
        
        # Determinar el lado opuesto para cerrar la posición
        close_side = "Sell" if side == "Buy" else "Buy"
        
        # Colocar orden take profit
        tp_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=close_side,
            orderType="Limit",
            qty=quantity,
            price=tp_price_adjusted,
            timeInForce="GTC",
            reduceOnly=True
        )
        
        if tp_order['retCode'] == 0:
            tp_order_id = tp_order['result']['orderId']
            print(f"✅ Take Profit colocado para {symbol}: ID {tp_order_id} a precio ${tp_price_adjusted}")
            
            mensaje = (
                f"<b>🎯 Take Profit colocado</b>\n\n"
                f"🪙 Símbolo: <b>{symbol}</b>\n"
                f"📊 Lado: <b>{side}</b>\n"
                f"💰 Precio entrada: ${entry_price}\n"
                f"🎯 Precio TP: <b>${tp_price_adjusted}</b>\n"
                f"✅ Orden: Reduce Only"
            )
            enviar_mensaje_telegram(mensaje)
            return True
        else:
            print(f"❌ Error al colocar Take Profit: {tp_order['retMsg']}")
            return False
            
    except Exception as e:
        print(f"Error al colocar Take Profit para {symbol}: {e}")
        return False

def monitor_positions():
    """
    Monitorea las posiciones para:
    1. Detectar cuando se ejecuta una orden limit
    2. Cancelar la orden opuesta
    3. Colocar el take profit
    """
    print("🔍 Iniciando monitoreo de posiciones...")
    
    while True:
        try:
            for symbol in SYMBOLS:
                if symbol not in active_orders:
                    continue
                
                # Verificar si ya se procesó esta posición
                if active_orders[symbol].get('has_position', False):
                    continue
                
                # Obtener posición actual
                position = get_position(symbol)
                
                if position:
                    side = position['side']
                    size = position['size']
                    entry_price = position['avgPrice']
                    
                    print(f"\n🚨 Posición detectada para {symbol}!")
                    print(f"   Lado: {side}, Tamaño: {size}, Precio: {entry_price}")
                    
                    # Marcar que ya tiene posición
                    active_orders[symbol]['has_position'] = True
                    
                    # Cancelar la orden opuesta
                    if side == "Buy" and active_orders[symbol].get('short_order_id'):
                        print(f"   Cancelando orden SHORT opuesta...")
                        cancel_order(symbol, active_orders[symbol]['short_order_id'])
                    elif side == "Sell" and active_orders[symbol].get('long_order_id'):
                        print(f"   Cancelando orden LONG opuesta...")
                        cancel_order(symbol, active_orders[symbol]['long_order_id'])
                    
                    # Colocar Take Profit
                    print(f"   Colocando Take Profit...")
                    time.sleep(1)  # Pequeña pausa
                    place_take_profit(symbol, side, entry_price, size)
                    
                    # Mensaje de Telegram
                    emoji = "🟢" if side == "Buy" else "🔴"
                    mensaje = (
                        f"<b>{emoji} ¡Posición abierta!</b>\n\n"
                        f"🪙 Símbolo: <b>{symbol}</b>\n"
                        f"📊 Lado: <b>{side}</b>\n"
                        f"💰 Precio entrada: <b>${entry_price}</b>\n"
                        f"📈 Tamaño: <b>{size}</b>\n\n"
                        f"✅ Orden opuesta cancelada\n"
                        f"🎯 Take Profit colocado"
                    )
                    enviar_mensaje_telegram(mensaje)
            
            time.sleep(3)  # Revisar cada 3 segundos
            
        except Exception as e:
            print(f"Error en monitor_positions: {e}")
            time.sleep(5)

def check_closed_positions():
    """
    Monitorea posiciones cerradas y vuelve a colocar órdenes
    alternando entre distancias de 1% y 2.5%
    """
    print("📊 Iniciando monitoreo de posiciones cerradas...")
    processed_symbols = set()
    
    while True:
        try:
            for symbol in SYMBOLS:
                if symbol not in active_orders:
                    continue
                
                # Si el símbolo tenía posición
                if active_orders[symbol].get('has_position', False):
                    # Verificar si la posición se cerró
                    position = get_position(symbol)
                    
                    if position is None:  # Posición cerrada
                        if symbol not in processed_symbols:
                            print(f"\n✅ Posición cerrada para {symbol}")
                            
                            # Alternar el ciclo
                            if symbol not in cycle_control:
                                cycle_control[symbol] = 'distance_1'
                            
                            # Cambiar al siguiente ciclo
                            if cycle_control[symbol] == 'distance_1':
                                next_cycle = 'distance_2'
                                next_distance_text = "2.5%"
                            else:
                                next_cycle = 'distance_1'
                                next_distance_text = "1%"
                            
                            cycle_control[symbol] = next_cycle
                            
                            mensaje = (
                                f"<b>✅ Posición cerrada</b>\n\n"
                                f"🪙 Símbolo: <b>{symbol}</b>\n"
                                f"🔄 Siguiente ciclo: <b>{next_distance_text}</b>\n"
                                f"⏳ Preparando nuevas órdenes..."
                            )
                            get_pnl(symbol) 
                            enviar_mensaje_telegram(mensaje)
                            
                            processed_symbols.add(symbol)
                            
                            # Limpiar el registro de órdenes activas
                            del active_orders[symbol]
                            
                            # Esperar un poco antes de volver a colocar órdenes
                            time.sleep(5)
                            
                            # Colocar nuevas órdenes con el nuevo ciclo
                            print(f"🔄 Cambiando a ciclo {next_distance_text} para {symbol}")
                            place_limit_orders_with_sl(symbol)
                            
                            # Remover del set de procesados después de colocar nuevas órdenes
                            processed_symbols.discard(symbol)
            
            time.sleep(5)  # Revisar cada 5 segundos
            
        except Exception as e:
            print(f"Error en check_closed_positions: {e}")
            time.sleep(10)

# ==================== FUNCIÓN PRINCIPAL ====================
def main():
    """Función principal del bot"""
    try:
        print("=" * 80)
        print("🤖 BOT DE TRADING BYBIT - ÓRDENES LIMIT BIDIRECCIONALES CON CICLOS")
        print("=" * 80)
        print(f"📊 Símbolos: {', '.join(SYMBOLS)}")
        print(f"💰 Monto por orden: {AMOUNT_USDT} USDT")
        print(f"🔄 Ciclo 1: {DISTANCE_1_PERCENTAGE * 100}% de distancia")
        print(f"🔄 Ciclo 2: {DISTANCE_2_PERCENTAGE * 100}% de distancia")
        print(f"🛡️ Stop Loss: {STOP_LOSS_PERCENTAGE * 100}%")
        print(f"🎯 Take Profit: {TAKE_PROFIT_PERCENTAGE * 100}%")
        print(f"🌐 Modo: {'TESTNET' if config.TESTNET else 'MAINNET'}")
        print("=" * 80)
        
        mensaje_inicio = (
            f"<b>🤖 Bot iniciado</b>\n\n"
            f"📊 Símbolos: {', '.join(SYMBOLS)}\n"
            f"💰 Monto: {AMOUNT_USDT} USDT\n"
            f"🔄 Ciclo 1: {DISTANCE_1_PERCENTAGE * 100}%\n"
            f"🔄 Ciclo 2: {DISTANCE_2_PERCENTAGE * 100}%\n"
            f"🛡️ Stop Loss: {STOP_LOSS_PERCENTAGE * 100}%\n"
            f"🎯 Take Profit: {TAKE_PROFIT_PERCENTAGE * 100}%\n\n"
            f"ℹ️ El bot alterna entre ambos ciclos"
        )
        enviar_mensaje_telegram(mensaje_inicio)
        
        # Colocar órdenes iniciales para todos los símbolos
        print("\n🚀 Colocando órdenes iniciales...\n")
        for symbol in SYMBOLS:
            place_limit_orders_with_sl(symbol)
            time.sleep(2)  # Pequeña pausa entre símbolos
        
        # Iniciar threads de monitoreo
        print("\n🔄 Iniciando threads de monitoreo...\n")
        
        monitor_thread = threading.Thread(target=monitor_positions, daemon=True)
        monitor_thread.start()
        
        closed_positions_thread = threading.Thread(target=check_closed_positions, daemon=True)
        closed_positions_thread.start()
        
        print("✅ Bot en funcionamiento. Presiona Ctrl+C para detener.\n")
        
        # Mantener el programa corriendo
        while True:
            time.sleep(60)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Bot activo - Órdenes: {len(active_orders)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Deteniendo bot...")
        mensaje_fin = "<b>⚠️ Bot detenido</b>"
        enviar_mensaje_telegram(mensaje_fin)
        print("✅ Bot detenido correctamente")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        mensaje_error = f"<b>❌ Error crítico en el bot</b>\n\n{str(e)}"
        enviar_mensaje_telegram(mensaje_error)

if __name__ == "__main__":
    main()