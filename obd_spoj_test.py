import obd

connection = obd.OBD("COM3")  # zamijeni s tvojim brojem
print(connection.status())

speed = connection.query(obd.commands.SPEED)
rpm = connection.query(obd.commands.RPM)
print(speed.value)
print(rpm.value)