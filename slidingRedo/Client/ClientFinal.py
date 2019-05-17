from socket import *
import os, sys, time 

class Client():

    def __init__(self, socket, serverAddr):
        self.socket = socket
        self.serverAddr = serverAddr
        #globals 
        self.lastPcktSnt = ""
        self.lastPcktRcvd = ""
        self.packetNumber = 0
        self.fileSize = 0
        self.windowSize = 0
        self.fileName = ""
        self.rtt = []

    ########################Protocol logic################################
    def buildPacket(self, header, payload):
        return header + "******" + payload
    
    def buildHeader(self, packetType, action, fileName, fileSize, windowSize, packetNumber, time):
        return(
            packetType + "*" +
            action + "*" +
            fileName + "*" +
            str(fileSize) + "*" +
            str(windowSize) + "*" +
            str(packetNumber) + "*" + 
            str(time)
        )
    def splitPacket(self, packet):
        header, payload, HASH = packet.split("******")
        return header, payload, HASH 
    
    def getSize(self, fileName):
        file = open(fileName, "rb")
        count = 0
        while(file.read(100) != ""):
            count += 100
        file.close() 
        return count

    def splitHeader(self, header):
        headerFields = header.split("*")
        return headerFields 

    #########################Communication logic##########################
    def receivePackets(self):
        while(1):
            try:
                packet, self.serverAddr = self.socket.recvfrom(2048)
                if(packet == ""):
                    return "None", "Fail", "None"
                else:
                    header, payload, Hash = self.splitPacket(packet)
                    headerFields = self.splitHeader(header)
                    return packet, headerFields, Hash  
            except timeout:
                self.socket.sendto(self.lastPcktSnt, self.serverAddr)
                continue 
    
    def sendPackets(self, header, payload):
        packet = self.buildPacket(header, payload)
        packet = packet + "******" + str(abs(hash(payload)))
        self.lastPcktSnt = packet
        self.socket.sendto(packet, self.serverAddr)
        
    
    def startHandshake(self, fileName, command):
        if(command == "PUT"):
            self.fileName = fileName
            self.fileSize = self.getSize(self.fileName)
            self.windowSize = 5
            self.packetNumber = 0
            header = self.buildHeader("SYN", "PUT", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
            self.sendPackets(header, "Hello")
            while(1):
                packet, headerFields, HASH = self.receivePackets()
                if(headerFields[0] == "SYN-ACK"):
                    header = self.buildHeader("ACK", "PUT", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                    self.sendPackets(header, "Ready to Recieve")
                    return 
                else:
                    self.socket.sendto(self.lastPcktSnt, self.serverAddr)
        elif(command == "GET"):
            print("Starting Handshake GET")
            self.fileName = fileName
            header = self.buildHeader("SYN", "GET", self.fileName, 0, 0, 0, time.time())
            # sending START Packet
            self.sendPackets(header, "Hello")
            while(1):
                #WAITING FOR ACK(SYN-ACK)
                packet, headerFields, HASH = self.receivePackets()
                print("Recvd from client: " + packet)
                if(headerFields[0] == "SYN-ACK"):
                    print("got")
                    self.fileSize = int(headerFields[3])
                    self.windowSize = int(headerFields[4])
                    self.packetNumber = int(headerFields[5])
                    header = self.buildHeader("ACK", "GET",fileName, headerFields[3], 1, 0, time.time())
                    self.sendPackets(header, "READY")
                    return 
                else:
                    self.socket.sendto(self.lastPcktSnt, self.serverAddr)

    ########################### GET and PUT ############################
    
    def startGET(self, files):
        for x in files:
            self.GET(x)

    def delayed(self, timeSent):
        t = time.time() - float(timeSent)
        maxTime = .03
        if(t <= maxTime):
            return True 
        else:
            return False
    
    def resendWindow(self, window):
            for x in window:
                print(x)
                self.socket.sendto(x, self.serverAddr)

    def GET(self, fileName):
        print("Getting file from server")
        self.startHandshake(fileName, "GET")
        file = open(fileName, "w+")
        windowCounter = 0
        byteCounter = 0
        recPackets = []
        self.socket.settimeout(.002) 
        startGET = time.time()
        while(1):
            packet, headerFields, HASH = self.receivePackets()
            if(packet in recPackets):
                continue
            if(headerFields[0] == "DATA"):
                header, payload, HASH = self.splitPacket(packet)
                if(self.packetNumber == int(headerFields[5])):
                    print("PACKETS MATCH")
                    if(int(HASH) == abs(hash(payload))):
                        print("PACKET IS NOT CORRUPTED")
                        file.write(payload)
                        byteCounter += 100 
                        recPackets.append(packet)
                        if(byteCounter > self.fileSize):
                            print("GOT ALL BYTES, CLOSING CONNECTION")
                            self.packetNumber = int(headerFields[5])
                            time.sleep(.1)
                            header = self.buildHeader("CLOSE", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                            self.sendPackets(header, "DONE!")
                            while(1):
                                packet, headerFields, HASH = self.receivePackets()
                                if(headerFields[0] == "ACK"):
                                    break
                            file.close()
                            break
                        elif(windowCounter == self.windowSize - 1):
                            print("GOT WINDOW, SENDING ACK for" + str(self.packetNumber))
                            self.packetNumber = int(headerFields[5])
                            header = self.buildHeader("ACK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                            self.sendPackets(header, "DONE!")
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter = 0
                        else:
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter += 1  
                    else:
                        print("PACKET #: " + headerFields[5] + "is corrupted")
                        header = self.buildHeader("NAK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                        self.sendPackets(header, "Payload Corrupted!")
                else:
                    print("PACKET expected packet #: " + str(self.packetNumber) + "got packet #: " + headerFields[5])
                    header = self.buildHeader("NAK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                    self.sendPackets(header, "Missing Packet #: " + str(self.packetNumber))
                print("EXPECTING PACKET #: " + str(self.packetNumber))
        self.reset()
        endGET = time.time()
        print("Total Time: " + str(endGET - startGET))


    
    def startPUT(self, files):
        for x in files:
            self.PUT(x)

    def PUT(self, fileName):
        self.socket.settimeout(5)
        self.startHandshake(fileName, "PUT")
        print("putting file on server")
        file = open(fileName, "r")
        done = False     
        while(not done):
            window = []
            start = time.time()
            for x in range(0, self.windowSize):
                payload = file.read(100)
                header = self.buildHeader("DATA", "PUT", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                self.sendPackets(header, payload)
                window.insert(x, self.lastPcktSnt)
                self.packetNumber += 1
            while(1):
                self.socket.settimeout(10)
                packet, headerFields, HASH = self.receivePackets()
                if(packet == "LOST"):
                    Done = True
                    break 
                if(headerFields[0] == "ACK"):
                    if(int(headerFields[5]) == (self.packetNumber - 1)):
                        end = time.time()
                        self.rtt.append(end - start)
                        print("GOT EXPECTED ACK" + headerFields[5])
                        break  
                    else:
                        print("Expected ACK for packet #: " + str(self.packetNumber - 1) + " got: " + headerFields[5])
                        self.resendWindow(window)
                        
                elif(headerFields[0] == "NAK"):
                    #print("GOT NAK, RESENDING WINDOW")
                    print(str(headerFields[6]))
                    self.resendWindow(window)
                elif(headerFields[0] == "CLOSE"):
                    print("COSING CONNECTION")
                    for x in range(0, 5):
                        time.sleep(.002)
                        self.socket.sendto(self.lastPcktSnt, self.serverAddr)
                    file.close()
                    done = True 
                    break
        self.getRTTAVG()
        self.reset()

    ########################### client logic###########################
    def getRTTAVG(self):
        sum = 0
        for x in range(0, len(self.rtt)):
            sum += self.rtt[x]
        avg = sum / len(self.rtt)
        print("Average RTT time: " + str(avg))
        return 
    def reset(self):
        self.lastPcktSnt = ""
        self.lastPcktRcvd = ""
        self.packetNumber = 0
        self.fileSize = 0
        self.windowSize = 0
        self.fileName = ""
        self.rtt = []
    
    def start(self, files, command):
        if(command == "GET"):
            self.startGET(files)
        elif(command == "PUT"):
            self.startPUT(files)
        else:
            print("Command not found")
        return 

serverAddr = ("localhost", 50001)
files = raw_input("Please enter the name of the text files you want to GET or PUT: \n")
files = files.split(" ")
command = raw_input("Please enter the name of the command you want to execute: GET or PUT: \n")
clientSocket = socket(AF_INET, SOCK_DGRAM)
client = Client(clientSocket, serverAddr)
client.start(files, command)