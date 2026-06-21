"""
DocuPi-3000 Watchdog Manager
Waveshare RTC Watchdog HAT (B) - STM32 hardware watchdog via I2C + GPIO
- Configures watchdog timeout
- Background thread feeds the dog via GPIO4
- If DocuPi service hangs → watchdog cuts power → Pi reboots
"""

import threading
import logging
import time

logger = logging.getLogger("docupi.watchdog")

# I2C address of the STM32 watchdog controller
WD_ADDR = 0x67
WD_I2C_BUS = 1

# Registers
REG_ON_OFF      = 0x01
REG_TIMEOUT     = 0x02
REG_REMAIN_TIME = 0x03
REG_STATE       = 0x04
REG_FW_VERSION  = 0x05

# Values
WD_ON  = 0x03
WD_OFF = 0x02
WD_NO_TIMEOUT  = 0x02
WD_TIMEOUT_FLAG = 0x03
LED_ON  = 0x10
LED_OFF = 0x00

# Config
FEED_GPIO_PIN = 4
DEFAULT_TIMEOUT = 120  # seconds - generous for service restarts
FEED_INTERVAL = 10     # feed every 10 seconds

# State
_wd_thread = None
_wd_running = False
_wd_enabled = False
_wd_available = False
_bus = None
_feed_pin = None
_last_feed = 0
_fw_version = 0


def _i2c_read(register):
    """Read single byte from watchdog."""
    data = _bus.read_i2c_block_data(WD_ADDR, register, 1)
    return data[0]


def _i2c_read_word(register):
    """Read 16-bit word from watchdog."""
    data = _bus.read_i2c_block_data(WD_ADDR, register, 2)
    return (data[1] << 8) | data[0]


def _i2c_write(register, value):
    """Write single byte to watchdog."""
    _bus.write_i2c_block_data(WD_ADDR, register, [value & 0xFF])


def _i2c_write_word(register, value):
    """Write 16-bit word to watchdog."""
    _bus.write_i2c_block_data(WD_ADDR, register, [value & 0xFF, (value >> 8) & 0xFF])


def detect_watchdog():
    """Check if the Waveshare watchdog HAT is present."""
    global _bus, _wd_available, _fw_version
    try:
        import smbus2
        _bus = smbus2.SMBus(WD_I2C_BUS)
        fw = _i2c_read(REG_FW_VERSION)
        if fw > 0:
            _fw_version = fw
            _wd_available = True
            logger.info(f"Watchdog HAT erkannt (FW v{fw})")
            return True
        else:
            logger.warning("Watchdog HAT: ungueltige Firmware-Version")
            return False
    except FileNotFoundError:
        logger.info("I2C Bus nicht verfuegbar - Watchdog nicht nutzbar")
        return False
    except Exception as e:
        logger.info(f"Watchdog HAT nicht erkannt: {e}")
        _wd_available = False
        return False


def init_watchdog(timeout=DEFAULT_TIMEOUT):
    """Initialize and enable the hardware watchdog."""
    global _feed_pin, _wd_enabled
    if not _wd_available:
        if not detect_watchdog():
            return False

    try:
        from gpiozero import DigitalOutputDevice
        _feed_pin = DigitalOutputDevice(FEED_GPIO_PIN, active_high=True, initial_value=False)
    except Exception as e:
        logger.error(f"GPIO {FEED_GPIO_PIN} Init fehlgeschlagen: {e}")
        return False

    try:
        # Enable watchdog
        _i2c_write(REG_ON_OFF, WD_ON)
        time.sleep(0.3)

        # Turn on LED, clear timeout flag
        _i2c_write(REG_STATE, LED_ON | WD_NO_TIMEOUT)

        # Set timeout
        _i2c_write_word(REG_TIMEOUT, timeout)

        _wd_enabled = True
        logger.info(f"Watchdog aktiviert (Timeout: {timeout}s, Feed: alle {FEED_INTERVAL}s)")
        return True
    except Exception as e:
        logger.error(f"Watchdog Init fehlgeschlagen: {e}")
        return False


def disable_watchdog():
    """Disable the hardware watchdog."""
    global _wd_enabled
    if not _wd_available or not _bus:
        return
    try:
        _i2c_write(REG_ON_OFF, WD_OFF)
        _wd_enabled = False
        logger.info("Watchdog deaktiviert")
    except Exception as e:
        logger.error(f"Watchdog deaktivieren fehlgeschlagen: {e}")


def feed():
    """Feed the watchdog (toggle GPIO4)."""
    global _last_feed
    if not _feed_pin:
        return
    try:
        _feed_pin.on()
        time.sleep(0.05)
        _feed_pin.off()
        _last_feed = time.time()
    except Exception as e:
        logger.error(f"Watchdog feed fehlgeschlagen: {e}")


def get_remaining_time():
    """Get remaining time before watchdog triggers."""
    if not _wd_available or not _bus:
        return -1
    try:
        return _i2c_read_word(REG_REMAIN_TIME)
    except:
        return -1


def get_status():
    """Get watchdog status dict for API."""
    status = {
        "available": _wd_available,
        "enabled": _wd_enabled,
        "fw_version": _fw_version,
        "timeout": DEFAULT_TIMEOUT,
        "feed_interval": FEED_INTERVAL,
        "last_feed": _last_feed,
        "remaining": -1
    }
    if _wd_available and _wd_enabled:
        status["remaining"] = get_remaining_time()
    return status


def _feed_loop():
    """Background thread that feeds the watchdog periodically."""
    global _wd_running
    logger.info("Watchdog Feed-Thread gestartet")
    while _wd_running:
        if _wd_enabled:
            feed()
        for _ in range(FEED_INTERVAL):
            if not _wd_running:
                break
            time.sleep(1)


def start_watchdog_thread(timeout=DEFAULT_TIMEOUT):
    """Start watchdog with background feed thread."""
    global _wd_thread, _wd_running

    if not detect_watchdog():
        logger.info("Kein Watchdog HAT - Thread nicht gestartet")
        return False

    if not init_watchdog(timeout):
        return False

    if _wd_running:
        return True

    _wd_running = True
    _wd_thread = threading.Thread(target=_feed_loop, daemon=True)
    _wd_thread.start()

    # Initial feed
    feed()
    return True


def stop_watchdog_thread():
    """Stop the feed thread and disable watchdog."""
    global _wd_running
    _wd_running = False
    disable_watchdog()
    if _feed_pin:
        _feed_pin.close()
    if _bus:
        _bus.close()
    logger.info("Watchdog Thread gestoppt")
