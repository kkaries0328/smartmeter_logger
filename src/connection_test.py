import serial

print("Communication Start")

s = serial.Serial("/dev/ttyS0", 115200)
s.write(str.encode("SKVER\r\n"))

print(s.readline().decode(encoding="utf-8"), end="")
print(s.readline().decode(encoding="utf-8"), end="")
print(s.readline().decode(encoding="utf-8"), end="")
