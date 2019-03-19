import subprocess
import threading
import urllib
import time
import json

sslPinningDisable = True
rootDetectionDisable = True
logLibraries = True
logListeners = True
verbose = True
fridaStartingPort = 45000

fridaThreads = []
fridaPorts = {}


def verifyFridaGadgetInjection(process):
    jobs = subprocess.run("curl -s http://127.0.0.1:%s/rpc/invoke/jobsGet" % fridaPorts[process],  
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    jobsUTF = jobs.stdout.decode('utf-8')
    jobList = json.loads(jobsUTF)
    
    for job in jobList:
        if (job['type'] == "android-sslpinning-disable"):
            if sslPinningDisable:
                continue
        if (job['type'] == "root-detection-disable"):
            if rootDetectionDisable:
                continue
        print("\033[91m \t \t Gadgets did not spawn correctly\033[0m")
        return False
    print("\033[92m \t \t Gadgets verified\033[0m")
    return True


def fridaGadgetInject(process):
    if sslPinningDisable:
        sslPinning = subprocess.run("curl -s http://127.0.0.1:%s/rpc/invoke/androidSslPinningDisable" % fridaPorts[process], 
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
        result = sslPinning.stdout.decode('utf-8')
        if (sslPinning.returncode != 0):
            print("\033[91m \t \t Error disabling SSL Pinning in app\033[0m")
        else:
            if verbose:
                print("\033[92m \t \t Successfully disabled SSL Pinning in app\033[0m")
    if rootDetectionDisable:
        rootDetection = subprocess.run("curl -s http://127.0.0.1:%s/rpc/invoke/androidRootDetectionDisable" % fridaPorts[process], 
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
        result = rootDetection.stdout.decode('utf-8')
        if (rootDetection.returncode != 0):
            print("\033[91m \t \t Error disabling Root Detection in app\033[0m")
        else:
            if verbose:
                print("\033[92m \t \t Successfully disabled Root Detection in app\033[0m")
    verifyFridaGadgetInjection(process)
    

def objectionHandler(objectionCall, process):
    for line in iter(objectionCall.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        if "Debug mode" in lineUTF:
            fridaGadgetInject(process)


def objectionStart(process):
    global fridaStartingPort
    fridaPorts[process] = fridaStartingPort
    fridaStartingPort += 1
    objection = subprocess.Popen(['objection', '-g', process, '--api-port', str(fridaPorts[process]), 'api'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    objectionThread = threading.Thread(target=objectionHandler, args=(objection, process,))
    objectionThread.start()
    time.sleep(6)
    

def processWatch(proc):
    for line in iter(proc.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        if "Start proc " in lineUTF:
            process = lineUTF[lineUTF.find("Start proc "):]
            process = process[:process.find('/')]
            process = process.replace("Start proc ", "")
            processInfo = process.split(":")
            print("\033[92mProcess spawned: \t %s \033[0m" % processInfo[1])
            if(verifyFridaGadgetInjection(processInfo[1]) == False):
                objectionStart(processInfo[1])
        if "Killing " in lineUTF:
            process = lineUTF[lineUTF.find("Killing "):]
            process = process[:process.find('/')]
            process = process.replace("Killing ", "")
            processInfo = process.split(":")
            print("\033[91mProcess killed: \t %s \033[0m" % processInfo[1])

def getRunningProcesses(proc):
    for line in iter(proc.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        process =  lineUTF.split(" ")
        try:
            int(process[0])
        except ValueError:
            continue
        print("\033[92m \t Process: \t %s \033[0m" % process[-1])
        objectionStart(process[-1])

def main():

    print("\033[92m- Injecting into running processes\033[0m")
    runningProcesses = subprocess.Popen(['frida-ps', '-U', '-i', '-a'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    processThread = threading.Thread(target=getRunningProcesses, args=(runningProcesses,))
    processThread.start()

    time.sleep(60)
    clearLogcat = subprocess.run("adb logcat -c",  
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    processWatchdog = subprocess.Popen(['adb', 'logcat', '-v', 'brief', 'ActivityManager:I', 'MyApp:D', '*:S'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    watchdogThread = threading.Thread(target=processWatch, args=(processWatchdog,))
    watchdogThread.start()
    try:
        time.sleep(0.2)
        for i in range(4):
            time.sleep(2000)
    finally:
        processThread.terminate()
        try:
            processThread.wait(timeout=20)
            print('== subprocess exited with rc =', proc.returncode)
        except subprocess.TimeoutExpired:
            print('subprocess did not terminate in time')
    watchdogThread.join()


if __name__ == "__main__": main()

