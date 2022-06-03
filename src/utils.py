SERIAL_PORT_DEV = "/dev/ttyS0"


def str2byte(str):
    return str.encode()

def byte2str(byte):
    return byte.decode(encoding='utf-8')

def close_display(oled):
    oled.fill(0)
    oled.show()
    
