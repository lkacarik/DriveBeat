import obd, time

connection = obd.OBD("COM4") #izlazni port od OBD-a
print(connection.status())

#jednokratni ispis
speed = connection.query(obd.commands.SPEED)
#rpm = connection.query(obd.commands.RPM)
print(speed.value)
#print(rpm.value)

#loop ispis
"""while True:
    #speed = connection.query(obd.commands.SPEED)
    rpm = connection.query(obd.commands.RPM)
    #print(speed.value)
    print(rpm.value)
    time.sleep(1)"""