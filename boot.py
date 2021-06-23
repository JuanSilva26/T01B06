from machine import Pin, I2C
from utime import ticks_ms
from time import sleep, time
from math import atan2      #para calcular os graus
import ustruct           #para comprimir/converter diferentes tipos de dados brutos; esta biblioteca implementa o elemento CPython correspondente de um conjunto de sub bibliotecas

print()
print("Iniciando magnetómetro MAG3110 3 eixos...")

i2c = I2C( scl=Pin(25), sda=Pin(26))

WHO_AM_I=0x07 #endereço who_am_i
addr=0x0E #endereço magnetómetro

def whoami():
    data = i2c.readfrom_mem( addr, WHO_AM_I, 1 )
    who=hex(data[0])
    if who=='0xc4':
        return who
    else:
        return 'Não encontrado.'

print( "WHO_AM_I Endereço de Registo:", whoami())
