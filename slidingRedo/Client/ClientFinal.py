from socket import *
import os, sys

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

    ########################Protocol logic################################
    def buildPacket(self, header, payload):
        return header + "******" + payload
    
    def buildHeader(self, packetType, action, fileName, fileSize, windowSize, packetNumber):
        return(
            packetType + "*" +
            action + "*" +
            fileName + "*" +
            str(fileSize) + "*" +
            str(windowSize) + "*" +
            str(packetNumber)
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
                self.socket.settimeout(1)
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
            self.windowSize = 1
            self.packetNumber = 0
            header = self.buildHeader("SYN", "PUT", self.fileName, self.fileSize, self.windowSize, self.packetNumber)
            self.sendPackets(header, "Hello")
            while(1):
                packet, headerFields, HASH = self.receivePackets()
                if(headerFields[0] == "SYN-ACK"):
                    header = self.buildHeader("ACK", "PUT", self.fileName, self.fileSize, self.windowSize, self.packetNumber)
                    self.sendPackets(header, "Ready to Recieve")
                    return 
                else:
                    self.socket.sendto(self.lastPcktSnt, self.serverAddr)
        elif(command == "GET"):
            print("Starting Handshake GET")
            self.fileName = fileName
            header = self.buildHeader("SYN", "GET", self.fileName, 0, 0, 0)
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
                    header = self.buildHeader("ACK", "GET",fileName, headerFields[3], 1, 0)
                    self.sendPackets(header, "READY")
                    return 
                else:
                    self.socket.sendto(self.lastPcktSnt, self.serverAddr)

    ########################### GET and PUT ############################
    
    def startGET(self, files):
        for x in files:
            self.GET(x)

    def GET(self, fileName):
        print("Getting file from server")
        self.startHandshake(fileName, "GET")
        file = open(fileName, "w+")
        windowCounter = 0
        byteCounter = 0
        recPackets = [] 
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
                            header = self.buildHeader("CLOSE", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber)
                            self.sendPackets(header, "DONE!")
                            file.close()
                            break
                        elif(windowCounter == self.windowSize - 1):
                            print("GOT WINDOW, SENDING ACK")
                            self.packetNumber = int(headerFields[5])
                            header = self.buildHeader("ACK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber)
                            self.sendPackets(header, "DONE!")
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter = 0
                        else:
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter += 1  
                    else:
                        print("PACKET #: " + headerFields[5] + "is corrupted")
                        header = self.buildHeader("NAK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber)
                        self.sendPackets(header, "Payload Corrupted!")
                else:
                    print("PACKET expected packet #: " + str(self.packetNumber) + "got packet #: " + headerFields[5])
                    header = self.buildHeader("NAK", "GET", fileName, self.fileSize, self.windowSize, self.packetNumber)
                    self.sendPackets(header, "Missing Packet #: " + str(self.packetNumber))
                print("EXPECTING PACKET #: " + str(self.packetNumber))
        self.reset()


    
    def startPUT(self, files):
        for x in files:
            self.PUT(x)

    def PUT(self, fileName):
        print("Putting file on server")
        self.startHandshake(fileName, "PUT")
        print("handshake successful")
        print("Getting file from server: " + fileName)
        print("fileName: " + self.fileName)
        print("file Size: " + str(self.fileSize))
        print("window size: " + str(self.windowSize))
        print("packetNumber: " + str(self.packetNumber))

    ########################### client logic###########################
    def reset(self):
        self.lastPcktSnt = ""
        self.lastPcktRcvd = ""
        self.packetNumber = 0
        self.fileSize = 0
        self.windowSize = 0
        self.fileName = ""
    
    def start(self, files, command):
        if(command == "GET"):
            self.startGET(files)
        elif(command == "PUT"):
            self.startPUT(files)
        else:
            print("Command not found")
        return 

serverAddr = ("localhost", 50000)
files = ["hamlet.txt"]
command = "GET"
clientSocket = socket(AF_INET, SOCK_DGRAM)
client = Client(clientSocket, serverAddr)
client.start(files, command)