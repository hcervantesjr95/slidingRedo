These are the instructions to run the Server, Client, and Proxy applications.

First run the server file by going into the Server directory and running serverFinal.py on a terminal. This is done by entering the following command: "python serverFinal.py".

Next step would be to run a proxy. To do this open another window and run either of the follwing commands:
    To run the deafault udpProxy, enter "python udpProxy.py"
    To run the udpProxy with the first set of configurations enter "./p1.sh"
    To run the udpProxy with the  second set of configurations enter "./p2.sh"
    To run the Third set of configurations enter "./p3.sh"

Finally run the client application by going into the client folder and running the following command: "python clientFinal.py"

Note:
    * Each test run can only transfer one file per execution.
    * The files needed to be transfered must exist within the directories of their respective applications.
        Example: If wanting to do a GET on "hamlet.txt" then that file needs to exist on the server side, else the connection will disconect and one would need to rerun the applications as described in running server, proxy and client instructions.
    * When entering a file name, the client application does not split white space characters, which can affect file retrievlal. 
    * The program will prompt for a GET or PUT, meaning if you want to either "GET" a file from a server, or "PUT" a file on the server.
    * 
