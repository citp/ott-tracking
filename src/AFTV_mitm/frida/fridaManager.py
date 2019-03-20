import subprocess
import threading
import urllib
import time
import json

sslPinningDisable = True
rootDetectionDisable = True
logLibraries = True
logListeners = True
verbose = False
fridaStartingPort = 45000
serviceBlacklistJSON = "serviceBlacklist.json"

fridaPorts = {}
appRunning = {}
appsPreviouslyRunning = {}
serviceBlacklist = {}
lock = threading.Lock()

def verifyFridaGadgetInjection(process):
    jobs = subprocess.run("curl -s http://127.0.0.1:%s/rpc/invoke/jobsGet" % fridaPorts[process],  
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    jobsUTF = jobs.stdout.decode('utf-8')
    try:
        jobList = json.loads(jobsUTF)
    except JSONDecodeError:
        print("\033[91m \t \t Gadgets did not spawn correctly\033[0m")
        return False

    for job in jobList:
        try:
            if (job['type'] == "android-sslpinning-disable"):
                if sslPinningDisable:
                    continue
            if (job['type'] == "root-detection-disable"):
                if rootDetectionDisable:
                    continue
        except TypeError:
            pass
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
    lock.release()
    

def objectionHandler(objectionCall, process):
    for line in iter(objectionCall.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        if "Debug mode" in lineUTF:
            serviceBlacklist[process] = False
            fridaGadgetInject(process)

        if "frida.NotSupportedError" in lineUTF:
            serviceBlacklist[process] = True
            lock.release()
            return
        if "Error" in lineUTF:
            lock.release()
            return

def objectionStart(process):
    global fridaStartingPort
    try:
        if serviceBlacklist[process] == True:
            lock.release()
            return
    except KeyError:
        serviceBlacklist[process] = False
    fridaPorts[process] = fridaStartingPort
    fridaStartingPort += 1
    objection = subprocess.Popen(['objection', '-g', process, '--api-port', str(fridaPorts[process]), 'api'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    objectionThread = threading.Thread(target=objectionHandler, args=(objection, process,))
    try:
        objectionThread.start()
    except Exception as error:
        print("\033[91m- Error starting objection thread\033[0m")
        print("\033[91m \t" + error + "\033[0m")
        lock.release()

def startObjectionThreads():
    for appName, status in appsPreviouslyRunning.items():
        if appRunning[appName]:
            print("\033[92m \t - Spawning objection thread for %s\033[0m" % appName)
            lock.acquire()
            objectionStart(appName)

def processWatch(proc):
    for line in iter(proc.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        if "Start proc " in lineUTF:
            process = lineUTF[lineUTF.find("Start proc "):]
            process = process[:process.find('/')]
            process = process.replace("Start proc ", "")
            processInfo = process.split(":")
            print("\033[93m- Watchdog - process spawned: \t %s \033[0m" % processInfo[1])
            appRunning[processInfo[1]] = True
            lock.acquire()
            objectionStart(processInfo[1])
        if "Killing " in lineUTF:
            process = lineUTF[lineUTF.find("Killing "):]
            process = process[:process.find('/')]
            process = process.replace("Killing ", "")
            processInfo = process.split(":")
            print("\033[93m- Watchdog - process killed: \t %s \033[0m" % processInfo[1])
            appRunning[processInfo[1]] = False

def flagPreviouslyRunningProcesses():
    runningProcesses = subprocess.Popen(['frida-ps', '-U', '-i', '-a'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    for line in iter(runningProcesses.stdout.readline, b''):
        lineUTF = line.decode('utf-8').strip()
        process =  lineUTF.split(" ")
        try:
            int(process[0])
        except ValueError:
            continue
        if verbose:
            print("\033[92m \t Process: \t %s \033[0m" % process[-1])
        appRunning[process[-1]] = True
        appsPreviouslyRunning[process[-1]] = True       

def loadServiceBlacklist():
    global serviceBlacklist
    try:
        blacklistFile = open(serviceBlacklistJSON, 'r')
    except FileNotFoundError:
        return

    with open(serviceBlacklistJSON) as serviceBlacklistFile:
        serviceBlacklist = json.load(serviceBlacklistFile)

def writeServiceBlacklist():
    with open(serviceBlacklistJSON, 'w') as serviceBlacklistFile:
        json.dump(serviceBlacklist, serviceBlacklistFile)

def main():
    loadServiceBlacklist()
    clearLogcat = subprocess.run("adb logcat -c",  
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    processWatchdog = subprocess.Popen(['adb', 'logcat', '-v', 'brief', 'ActivityManager:I', 'MyApp:D', '*:S'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    watchdogThread = threading.Thread(target=processWatch, args=(processWatchdog,))
    try:
        watchdogThread.start()
        print("\033[92m- Process watchdog started\033[0m")
    except Exception as error:
        print("\033[91m- Process watchdog startup failed\033[0m")
        print("\033[91m \t" + error + "\033[0m")
        exit()
    try:
        print("\033[92m- Collecting currently running processes\033[0m")
        flagPreviouslyRunningProcesses()
        print("\033[92m- Successfully collected currently running processes\033[0m")
    except Exception as error:
        print("\033[91m- Failed to collect currently running processes\033[0m")
        print("\033[91m \t" + error + "\033[0m")

    print("\033[92m- Spawning objection threads\033[0m")
    objectionService = threading.Thread(target=startObjectionThreads())
    objectionService.start()
    objectionService.join()

    time.sleep(2)

    print("\033[92m- Successfully injected Frida gadgets\033[0m")

    time.sleep(2)
    writeServiceBlacklist()

if __name__ == "__main__": main()

