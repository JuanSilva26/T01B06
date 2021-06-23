led_red = Pin(21, Pin.OUT)
led_green = Pin(19, Pin.OUT)
button_left = Pin(23, Pin.IN, Pin.PULL_UP)
#button_right = Pin(18, Pin.IN, Pin.PULL_UP)

i2c = I2C( scl=Pin(25), sda=Pin(26))   #implementação barramento i3c

# Endereços do Magnetómetro MAG3110, disponíveis na datasheet
addr=0x0E #endereço principal do magnetómetro

DR_STATUS	= 0x00	 #normal
OUT_X_MSB	= 0x01   #fastmode
OUT_X_LSB	= 0x02
OUT_Y_MSB	= 0x03
OUT_Y_LSB	= 0x04
OUT_Z_MSB	= 0x05
OUT_Z_LSB	= 0x06   #fastmode
WHO_AM_I	= 0x07   #identificação
SYSMOD		= 0x08
OFF_X_MSB	= 0x09	 #medições
OFF_X_LSB	= 0x0A
OFF_Y_MSB	= 0x0B
OFF_Y_LSB	= 0x0C
OFF_Z_MSB	= 0x0D
OFF_Z_LSB	= 0x0E   #medições
DIE_TEMP	= 0x0F	 #temperatura
CTRL_REG1	= 0x10   #registo control 1
CTRL_REG2	= 0x11   #registo control 2

WHO_AM_I_RESP = 0xC4

# Definições CTRL_REG1 
DR_OS_80_16  = 0x00      #Output Data Rate = 80Hz, Oversampling Ratio = 16

# Endereços do CTRL_REG1
ACTIVE_MODE			= 0x01
STANDBY_MODE		= 0x00

# REG1 Bit seq: DR2 | DR1 | DR0 | OS1 | OS0 | FR | TM | AC 
# DR2=0, DR1=0, DR0=0 , OS1=0, OS2=0 --> default para ODR=80 e OSR=16
# FR=0 --> lê os valores de todos os 16 bit
# TM=0 --> condição normal  
# AC=0 --> modo standby (entre medições)

# Endereços do CTRL_REG2 
AUTO_MRST_EN		= 0x80
RAW_MODE			= 0x20
NORMAL_MODE			= 0x00
MAG_RST				= 0x10

# REG2 bit seq.: AUTO_MRST_EN | - | RAW | Mag_RST | - | - | - | - 
# AUTO_MRST_EN = 1 --> reinicio automatico do sensor depois de adquridos novos dados
# RAW     = 0 --> modo normal, dados são corrigidos pelos dados do user offset
# Mag_RST = 0 --> ciclo de reinicio não ativado

# Endereços dos eixos do Magnetómetro
OFFSET_X_AXIS = 0x09 
OFFSET_Y_AXIS = 0x0B 
OFFSET_Z_AXIS = 0x0D 

timeout = 5   #segundos
degporrad = (180.0/3.14159265358979)  #conversão graus-radianos

# Condições Iniciais
calibrationMode = False
activeMode = False
calibrated = False

print("MAG3110 confirmado.")
print()

def reset():
	""" reinicia a biblioteca e inicializa o MAG3110 """
	i2c.writeto_mem(addr, CTRL_REG1, bytes([NORMAL_MODE]) ) # Dados do magnetometro ficam 0
	i2c.writeto_mem(addr, CTRL_REG2, bytes([AUTO_MRST_EN]) ) 
	global calibrationMode   
	calibrationMode = False
	global activeMode     #varáveis globais para se irem alterando na generalidade do código
	activeMode = False
	global calibrated
	calibrated = False
	set_offset( OFFSET_X_AXIS, 0)   #define valor inicial 0 em todos os eixos
	set_offset( OFFSET_Y_AXIS, 0)
	set_offset( OFFSET_Z_AXIS, 0)

def set_offset( axis_register, offset ):
	""" Define um valor inteiro (offest) para todos os eixos do Magnetómetro """
	buff = ustruct.pack('>h', offset)    # formata 2 bits segundo o valor de offset --> MSB primeiro
	#print(buff)
	i2c.writeto_mem( addr, axis_register, bytes([ buff[0] ]) )
	sleep( 0.015 )  	                                      	#escrevem o valor de buff em cada eixo
	i2c.writeto_mem( addr, axis_register+1, bytes([ buff[1] ]) )   

reset()

#sempre que se entra ou sai do modo caliração é necessário ativar/desativar o standby
def enter_standby(): # Necessario para manipular os Registers
	global activeMode
	activeMode = False
	data = i2c.readfrom_mem(addr, CTRL_REG1, 1)   #lê os valores do mag (00)
	#print(data[0])
	atual = data[0] #limpa a cache dos bits para ativar o modo stand-by
	i2c.writeto_mem(addr, CTRL_REG1, bytes([atual])) # bytes = 0x00, entrar no standby

def exit_standby(): #sair do standby para modo ativo
	global activeMode
	activeMode = True
	data = i2c.readfrom_mem(addr, CTRL_REG1, 1)
	#print(data[0])
	atual = data[0] #limpa a cache dos bits para sair do modo stand-by
	i2c.writeto_mem(addr, CTRL_REG1, bytes([ACTIVE_MODE])) # bytes = 0x01, sair do standby

def calibration():
	global calibrationMode
	calibrationMode = True
	global calibrated
	calibrated = False
	# valores iniciais para calibração
	# Notar que o AUTO_MRST_EN irá sempre ser lido como 0
	# Desta forma tem se definir este bit sempre que se modifque CTRL_REG2
	i2c.writeto_mem(addr, CTRL_REG2, bytes([ AUTO_MRST_EN | RAW_MODE ]) ) # | funciona como OU lógico; retorna 1 se um dos bits 1, ou seja, retorna 0x00
	DR_OS(DR_OS_80_16) #DR_OS_80_16	= 0x00
	
	
def DR_OS(dros):
	enter_standby() # para modoficiar o CTRL_REG1 é preciso inicializar e terminar o modo stand_by
	sleep( 0.100 )  #dar tempo ao CTRL_REG1 para modoficar a totalidade de bits; senão pode dar erro a não modificar todos
	# Ler dados atuais 
	data = i2c.readfrom_mem(addr, CTRL_REG1, 1 )
	atual = data[0] & 0x07 # dropa os 5 MSB (remove a configuração DR_OS atual)
	i2c.writeto_mem(addr, CTRL_REG1, bytes([ atual | dros ]) )   #escreve o register com o novo DR_OS, neste caso DR_OS_80_16 = 0x00
	sleep( 0.100 )
	exit_standby() # retorna à amostragem como anteriormente

def read( ):
	""" lê os valores x,y,z do MAG3110, retornando-os num tuplo """ 
	data = i2c.readfrom_mem( addr, OUT_X_MSB, 6 )   #lê os dados com o enredeço X MSB, 6 bits, 2 para cada eixo
	x = ustruct.unpack( '>h', data[0:2] )[0]        # convert 2 bytes, MSB first to integer, signed 2's complement number
	y = ustruct.unpack( '>h', data[2:4] )[0]        #converte 2 bytes (primeiro o MSB) 2 por cada eixo 
	z = ustruct.unpack( '>h', data[4:6] )[0]        
	return x,y,z
	
def step_calibration():
	""" Deeve ser chamdada para recolher os dados da calibração.
	A calibração termina automaticamente quando forem recolhidos dados suficientes (cerca de 5-15 segundos)."""
	# lê os dados com endereço X MSB 
	xyz = read()    #lê os valores do MAG e retorna um tuplo
	global xmin
	global xmax
	global ymin
	global ymax
	global timeChange
	changed = False
	if xyz[0] < xmin:          #deteta aterações nos máximos e mínimos, atualizando os valores (x e y)
		xmin = xyz[0]
		changed = True
	if xyz[0] > xmax:
		xmax = xyz[0]
		changed = True
	if xyz[1] < ymin: 
		ymin = xyz[1]
		changed = True
	if xyz[1] > ymax:
		ymax = xyz[1]
		changed = True
	if changed:
		timeChange = time() # reinicia a contagem do tempo
		print("Calibrando, Tempo de calibração:", timeChange)
		print()
	if ( (time()-timeChange) > timeout ):  #se o tempo de calibração foi esgotado, sai da calibração
		exit_calibration()

def exit_calibration():
	# Calcula offsets
	global xmin
	global xmax
	global ymin
	global ymax
	x_offset = (xmin + xmax)//2
	y_offset = (ymin + ymax)//2
	x_scale = 1.0/(xmax - xmin)
	y_scale = 1.0/(ymax - ymin)
	# define os offsets no magnetómetro
	set_offset( OFFSET_X_AXIS, x_offset )
	set_offset( OFFSET_Y_AXIS, y_offset )
	# (modo normal) usa os offsets definidos na leitura
	i2c.writeto_mem( addr, CTRL_REG2, bytes([ AUTO_MRST_EN ]) )  #ver coisas
	global calibrationMode
	calibrationMode = False
	global calibrated         #atualizar variáveis
	calibrated = True
	enter_standby()
	
#def user_offset(  ):
#	""" Lê o user offset armazenado no mag """
#	data = [0x00] * 2    #2 bits 0
#	data = i2c.readfrom_mem( addr, OFFSET_X_AXIS, 2) # lê 2 bytes
#	x = ustruct.unpack( '>h', data[0:2] )[0] # converte 2 bytes, 2 bytes MSB, MSB primeiro a ser integrado
#	data = i2c.readfrom_mem( addr, OFFSET_Y_AXIS, 2) # lê 2 bytes
#	y = ustruct.unpack( '>h', data[0:2] )[0]
#	data = i2c.readfrom_mem( addr, OFFSET_Z_AXIS, 2) # lê 2 bytes
#	z = ustruct.unpack( '>h', data[0:2] )[0]
#	#WaitMicrosecond(2000)
#	return (x>>1,y>>1,z>>1)		


#print( 'Coorndenadas Iniciais: = %s,%s,%s' % user_offset() ) #lê as coordenaas reais depois do offset
#DR_OS(DR_OS_1_25_32)

def data_ready():
	""" DR sequência de bits (ZYXOW, ZOW, YOW, XOW, ZYXDR, ZDR, YDR, XDR)
	ZYXDR retorna valor lógico 1 se novos dados estão prontos a ser utiizados"""
	data = i2c.readfrom_mem( addr, DR_STATUS, 1 )    #lê os dados endereço dr 
	# Confirma que o bit ZYXDR está ativo
	return data[0] & 1==1   #funciona como E lógico, retorna True

def cardinalpoints(norte):
	if 0<=norte<=90:
		return norte, norte+90, norte+180, norte+270
	elif 0>norte>=-90:
		return norte+360, norte+270, norte+180, norte+90
	elif 90<norte<=180:
		return norte, norte-90, norte+180, norte+90
	elif -90>norte>=-180:
		return norte+360, norte+270, norte+180, norte+450
	#elif 180<norte<=270:
	#	return norte, norte-90, norte-180, norte+90
	#elif -180>norte>=-270:
	#	return norte+360, norte+270, norte+540, norte+450
	#elif 270<norte<=360:
	#	return norte, norte-90, norte-180, norte-270
	#elif -270>norte>=-360:
	#	return norte+360, norte+630, norte+540, norte+450
 
def compass(  ):
	""" Retorna direção dos pontos cardeais """
	assert calibrated, "O dispositivo MAG3110 não está calibrado!"  #se calibrated=true continua, senão retorna aviso
	x,y,z = read()     #lê o tuplo com as coorndeadas cartesianas
	x_offset = (xmin + xmax)//2     #establece coorndendas iniciais
	y_offset = (ymin + ymax)//2
	x_scale = 1.0/(xmax - xmin)
	y_scale = 1.0/(ymax - ymin)
	# Define as coordenadas iniciais no mag
	#set_offset( OFFSET_X_AXIS, x_offset )
	#set_offset( OFFSET_Y_AXIS, y_offset )
	norte = atan2( -1*y*y_scale, x*x_scale) * degporrad    #calcula o norte, ver operação
	#calcula a direção em graus dos pontos cardeais sabendo o norte
	return norte

#codiçoes iniciais
xmin = 30000    #range maxima do magnetometro
xmax = -30000
ymin = 30000
ymax = -30000
last = ticks_ms()

def print_coords():
	xyz=read()      #mostrar as coordenadas durante a calibrção
	print("Coordenadas Magnéticas:")
	print("x: ",xyz[0], "  y: ", xyz[1], "  z: ", xyz[2])
	sleep(1)

		
		
def print_compass():
	if data_ready:    #depois de estar calibrado apresenta a leitura dos dados reais a cada 3 segundos
		#print( 'x,y,z = %s,%s,%s ' % read() )
		norte,este,sul,oeste = cardinalpoints(compass())
		print("Direção Pontos Cardeais:")
		print('   N: ', norte)
		print('   E: ', este)
		print("   S: ", sul)
		print('   W: ', oeste)
		print( '-'*40 )
		sleep( 2 )

def continuous_data():
	global last
	while button_left.value():
		now = ticks_ms()
		if now -last >= 5000:
			last = now
			xyz=read()      #mostrar as coordenadas durante a calibrção
			print("Coordenadas Magnéticas:")
			print("x: ",xyz[0], "  y: ", xyz[1], "  z: ", xyz[2], " |B|: ", (xyz[0]**2+xyz[1]**2)**0.5, "microTesla"  )
			print("Carregar no botão da esquerda caso queira parar a leitura")
		


while True:
#se ainda não está calibrado
	if not calibrated:
		led_red.value(True) 
		led_green.value(False)
		#está em calibração
		if not calibrationMode:
			print("Rode lentamente o dispositivo 360º sobre uma superfície plana durante 10 segundos. ")
			print()
			sleep(4)
			print("Iniciando calibração...")
			sleep(1)
			calibration()
		# recohe dados de calibração
		else:
			step_calibration()
	#está calibrado
	else:   
		print()
		print( "Dispositivo Calibrado." )
		print()
		led_red.value(False)
		led_green.value(True)
		print("Pronto para realizar medições")
		print()
		
		print("Caso queira os valores dos pontos cardeais, digite bussola")
		print("Caso queira os valores do Campo Magnético, digite campo")
		print("Caso queira medições continuas do Campo, digite continuo")
		ordem = str(input("Que deseja medir? : "))
		
		if ordem == "campo":
			print()
			print_coords()
		
		elif ordem == "bussola":
			print()
			print_compass()
		elif ordem == "continuo":
			print()
			continuous_data()
			

print("Dispositivo pronto a calibrar.")
print()
sleep(3)
