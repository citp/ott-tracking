#!/bin/bash

read -p "Cert file name?" CERT_FILE
HASH=`openssl x509 -inform PEM -subject_hash_old -in $CERT_FILE | head -1`.0
cat $CERT_FILE > $HASH
openssl x509 -inform PEM -text -in $CERT_FILE -out /dev/null >> $HASH


:'
#Copy the cert you created using "create_cert.sh" to the AmazonFire sdcard (e.g. /sdcard0/c8750f0d.0)
#Run adb shell and su
adb shell
su

#Make the /system folder writable (will return to read-only upon reboot):
mount -o remount,rw /system

#Copy the new certificate files to the correct folder on your Android device:
cp /sdcard0/c8750f0d.0 /system/etc/security/cacerts/

#Correct the file permissions to u=rw, g=r, o=r:
cd /system/etc/security/cacerts/
chmod 644 c8750f0d.0

#Check if the files are ok:
ls -al -Z

#The certificates will be loaded upon the next boot of your device, so reboot your device:
reboot
'