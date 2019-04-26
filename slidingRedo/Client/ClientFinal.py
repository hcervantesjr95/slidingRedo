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
                    return "None", "Fail"
                else:
                    header, payload, Hash = self.splitPacket(packet)
                    headerFields = self.splitHeader(header)
                    return packet, headerFields, Hash  
            except timeout:
                self.socket.sendto(self.lastPcktSnt, self.serverAddr)
    
    def sendPackets(self, header, payload):
        packet = self.buildPacket(header, payload)
        packet = packet + "******" + str(abs(hash(payload)))
        self.lastPcktSnt = packet
        self.socket.sendto(packet, self.serverAddr)
        print("sending packets")
    
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
                if(headerFields[0] == "SYN-ACK"):
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
        print("handshake success")
        print("Getting file from server: " + fileName)
        print("fileName: " + self.fileName)
        print("file Size: " + str(self.fileSize))
        print("window size: " + str(self.windowSize))
        print("packetNumber: " + str(self.packetNumber))
        packet, headerFields, HASH = self.receivePackets()
    
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