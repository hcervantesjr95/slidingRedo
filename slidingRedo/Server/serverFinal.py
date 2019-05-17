from socket import *
import os, sys, time 

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
                packet, self.clientAddr = self.socket.recvfrom(2048)
                if(packet == ""):
                    return "None", "Fail"
                else:
                    header, payload, Hash = self.splitPacket(packet)
                    headerFields = self.splitHeader(header)
                    return packet, headerFields, Hash
            except timeout:
                self.socket.sendto(self.lastPcktSnt, self.clientAddr) 
    
    def sendPackets(self, header, payload):
        packet = self.buildPacket(header, payload)
        packet = packet + "******" + str(abs(hash(payload)))
        self.lastPcktSnt = packet
        self.socket.sendto(packet, self.clientAddr)
        print("sending packets")
    
    
    def listenHandshake(self):
        while(1):
            packet, header, HASH = self.receivePackets()
            if(header[0] == "SYN"):
                if(header[1] == "GET"):
                    #sending ACK
                    self.fileName = header[2]
                    self.fileSize = self.getSize(self.fileName)
                    self.packetNumber = 0
                    self.windowSize = 5
                    header = self.buildHeader("SYN-ACK", "GET", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                    self.sendPackets(header, "READY TO SEND")
                    while(1):
                        print("Waiting for ACK")
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
                    header = self.buildHeader("SYN-ACK", "PUT", self.fileName, self.fileSize, self.windowSize , self.packetNumber, time.time())
                    self.sendPackets(header, "READY TO RECIEVE")
                    while(1):
                        packet, header, HASH = self.receivePackets()
                        if(header[0] == "ACK"):
                            self.PUT(header[2])
                            break
                        else:
                            self.socket.sendto(self.lastPcktSnt, self.clientAddr)
                     



    ########################### GET and PUT ############################
    
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
                self.socket.sendto(x, self.clientAddr)

                
    def GET(self, fileName):
        file = open(fileName, "r")
        done = False     
        ackCounter = 0
        while(not done):
            window = []
            start = time.time()
            for x in range(0, self.windowSize):
                payload = file.read(100)
                header = self.buildHeader("DATA", "GET", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                self.sendPackets(header, payload)
                window.insert(x, self.lastPcktSnt)
                self.packetNumber += 1
            while(1):
                self.socket.settimeout(10) 
                packet, headerFields, HASH = self.receivePackets()
                if(packet == "LOST"):
                    Done = True
                    break 
                if(headerFields[0] == "ACK" ):
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
                    header = self.buildHeader("ACK", "GET", self.fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                    self.sendPackets(header, payload)
                    for x in range(0, 5):
                        time.sleep(.002)
                        self.socket.sendto(self.lastPcktSnt, self.clientAddr)
                    file.close()
                    done = True 
                    break
        self.getRTTAVG()
        self.socket.settimeout(300)
        self.reset()
    
    def PUT(self, fileName):
        print("Getting file from client")
        file = open(fileName, "w+")
        windowCounter = 0
        byteCounter = 0
        recPackets = []
        self.socket.settimeout(.002) 
        time.sleep(3)
        startPUT = time.time()
        while(1):
            packet, headerFields, HASH = self.receivePackets()
            print("GETTING PACKET: " + str(packet))
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
                            endPUT = time.time()
                            print("PUT TOTAL TIME: " + str(endPUT - startPUT))
                            self.packetNumber = int(headerFields[5])
                            header = self.buildHeader("CLOSE", "PUT", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                            self.sendPackets(header, "DONE!")
                            while(1):
                                try:
                                    self.socket.settimeout(5)
                                    packet, headerFields, HASH = self.receivePackets()
                                    if(headerFields[0] == "ACK"):
                                        break
                                except timeout:
                                    continue
                            file.close()
                            break
                        elif(windowCounter == self.windowSize - 1):
                            print("GOT WINDOW, SENDING ACK for" + str(self.packetNumber))
                            self.packetNumber = int(headerFields[5])
                            header = self.buildHeader("ACK", "PUT", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                            self.sendPackets(header, "DONE!")
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter = 0
                        else:
                            self.packetNumber = int(headerFields[5]) + 1
                            windowCounter += 1  
                    else:
                        print("PACKET #: " + headerFields[5] + "is corrupted")
                        header = self.buildHeader("NAK", "PUT", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                        self.sendPackets(header, "Payload Corrupted!")
                else:
                    print("PACKET expected packet #: " + str(self.packetNumber) + "got packet #: " + headerFields[5])
                    header = self.buildHeader("NAK", "PUT", fileName, self.fileSize, self.windowSize, self.packetNumber, time.time())
                    self.sendPackets(header, "Missing Packet #: " + str(self.packetNumber))
                print("EXPECTING PACKET #: " + str(self.packetNumber))
        self.socket.settimeout(300)
        self.reset()

    ########################### server logic###########################
    def reset(self):
        self.clientAddr = None 
        #globals
        self.lastPcktSnt = ""
        self.lastPcktRcvd = ""
        self.packetNumber = 0
        self.fileSize = 0
        self.windowSize = 0
        self.fileName = ""
        self.rtt = []
    
    def getRTTAVG(self):
        sum = 0
        for x in range(0, len(self.rtt)):
            sum += self.rtt[x]
        avg = sum / len(self.rtt)
        print("Average RTT time: " + str(avg))
        return 

    def start(self):
        self.listenHandshake()
serverAddr = ("", 50001)


serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(serverAddr)
server = Server(serverSocket, serverAddr)
server.start()