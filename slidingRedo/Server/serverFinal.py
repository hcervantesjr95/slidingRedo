from socket import *
import os, sys

class Server():

    def __init__(self, socket, serverAddr):
        self.socket = socket
        self.serverAddr = serverAddr
        self.clientAddr = None 
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
            packet, self.clientAddr = self.socket.recvfrom(2048)
            if(packet == ""):
                return "None", "Fail"
            else:
                header, payload, Hash = self.splitPacket(packet)
                headerFields = self.splitHeader(header)
                return packet, headerFields, Hash  
    
    def sendPackets(self, header, payload):
        packet = self.buildPacket(header, payload)
        packet = packet + "******" + str(abs(hash(payload)))
        self.lastPcktSnt = packet
        self.socket.sendto(packet, self.clientAddr)
        print("sending packets")
    
    
    def listenHandshake(self):
        while(1):
            packet, header, HASH = self.receivePackets()
            print("PACKET: " + packet)
            if(header[0] == "SYN"):
                if(header[1] == "GET"):
                    #sending ACK
                    self.fileName = header[2]
                    self.fileSize = self.getSize(self.fileName)
                    self.packetNumber = 0
                    self.windowSize = 1 
                    header = self.buildHeader("SYN-ACK", "GET", self.fileName, self.fileSize, self.windowSize, self.packetNumber)
                    self.sendPackets(header, "READY TO SEND")
                    while(1):
                        packet, header, HASH = self.receivePackets()
                        if(header[0] == "ACK"):
                            self.GET(header[2])
                            break
                        else:
                            self.socket.sendto(self.lastPcktSnt, self.clientAddr)
                elif(header[1] == "PUT"):
                    self.fileName = header[2]
                    self.fileSize = int(header[3])
                    self.windowSize = int(header[4])
                    self.packetNumber = int(header[5])
                    header = self.buildHeader("SYN-ACK", "PUT", self.fileName, self.fileSize, self.windowSize , self.packetNumber)
                    self.sendPackets(header, "READY TO RECIEVE")
                    while(1):
                        packet, header, HASH = self.receivePackets()
                        if(header[0] == "ACK"):
                            self.PUT(header[2])
                            break
                        else:
                            self.socket.sendto(self.lastPcktSnt, self.clientAddr)
                     



    ########################### GET and PUT ############################
    

                
    def GET(self, fileName):
        print("Getting file from server: " + fileName)
        print("fileName: " + self.fileName)
        print("file Size: " + str(self.fileSize))
        print("window size: " + str(self.windowSize))
        print("packetNumber: " + str(self.packetNumber))
    
    def PUT(self, fileName):
        print("Putting file on server")
        print("Getting file from server: " + fileName)
        print("fileName: " + self.fileName)
        print("file Size: " + str(self.fileSize))
        print("window size: " + str(self.windowSize))
        print("packetNumber: " + str(self.packetNumber))

    ########################### server logic###########################
    def start(self):
        self.listenHandshake()
serverAddr = ("", 50000)


serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(serverAddr)
server = Server(serverSocket, serverAddr)
server.start()