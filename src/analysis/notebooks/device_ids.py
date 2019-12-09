###########################
# IDs used for leak detection
###########################
# To get Roku device IDs visit the following endpoint: http://ROKU_IP:8060/query/device-info  # noqa
# to get Fire TV android ID run: `adb shell settings get secure android_id`
###########################

ROKU_IDS = {
    "Serial No": "...",
    "AD ID": "...",
    "Device ID": "...",
    "MAC": "d8:31:34...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Email": "...@gmail.com",
    "Password": "...",
    "Build Number": "519.00E04142A",
    "Device Name": "Office tv",
    "Wifi SSID": "...",
}

# Used in the manual crawls
ROKU_IDS_2 = {
    "Serial No": "...",
    "AD ID": "...",
    "Device ID": "...",
    "MAC": "d8:31:34...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Email": "...",
    "Password": "...",
    "Build Number": "519.10E04111A",
    "Device Name": "Express",
    "Wifi SSID": "...",
    "Profile Username": "...",
    "Profile Firstname": "...",
    "Profile Lastname": "...",
    "Profile Email": "...",
    "Profile Email (Alt)": "...",
    "Profile Password": "...",
    "Profile Zip": "...",
    "comcast_email": "...",
    "comcast_password": "...",
    "directtv_email": "...",
    "directtv_password": "...",
    "PayPal email": "...",
    "cc1": "...",
    "cc2": "...",
    "cc3": "...",
    "cc4": "...",
    "cc5": "...",
    "cc6": "...",
}



AMAZON_FIRE_TV_CUBE_IDS = {
    "MAC": "...",
    "AD ID": "...",
    "Device name": "...",
    "Amazon account": "...",
    "Serial No": "G090...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Software version": "Fire OS 6.2.6.0 (NS6260/1840)",
    "Fire TV Home Version": "6.1.5.1-002",
    "Email": "...",
    "Password": "...",
    "Wifi SSID": "...",
}


AMAZON_FIRE_TV_STICK_IDS = {
    "MAC": "...",
    "AD ID": "...",
    "Android ID": "...",
    "Bluetooth MAC": "68:9A:87...",
    "Device name": "...",
    "Amazon account": "...i",
    "Serial No": "...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Software version": "Fire OS 5.2.6.9 (6325552020)",
    # "Fire TV Home Version": "",  TODO
    "Email": "...",
    "Password": "...",
    "Wifi SSID": "...",
}

# Used in the manual crawls
AMAZON_FIRE_TV_STICK_IDS_FACTORY_RESET = {
    "MAC": "68:9a:87...",
    "AD ID": "...",
    "Android ID": "...",
    "Bluetooth MAC": "...",
    "Device name": "...",
    "Amazon account": "...",
    "Serial No": "...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Software version": "Fire OS 5.2.6.9 (6325552020)",
    "Email": "...",
    "Password": "...",
    "Wifi SSID": "...",
    "Profile Username": "...",
    "Profile Firstname": "...",
    "Profile Lastname": "...",
    "Profile Email": "...",
    "Profile Email (Alt)": "...",
    "Profile Password": "...",
    "Profile Zip": "40505",
    "comcast_email": "...",
    "comcast_password": "...",
    "directtv_email": "...",
    "directtv_password": "...",
    "PayPal email": "...",
    "cc1": "...",
    "cc2": "...",
    "cc3": "...",
    "cc4": "...",
    "cc5": "...",
    "cc6": "...",
}


AMAZON_FIRE_TV_STICK_2_IDS = {
    "MAC": "1c:12:b0...",
    "AD ID": "...",
    "Android ID": "...",
    "Bluetooth MAC": "1C:12:B0...",
    "Device name": "...",
    "Amazon account": "...",
    "Serial No": "...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Software version": "Fire OS 5.2.6.9 (6325552020)",
    "Email": "...",
    "Password": "...",
    "Wifi SSID": "...",
}


AMAZON_FIRE_TV_STICK_3_IDS = {
    "MAC": "68:9a:87...",
    "AD ID": "...",
    "Bluetooth MAC": "CC:9E:A2...",
    "Android ID": "...",
    "Device name": "...",
    "Amazon account": "...",
    "Serial No": "...",
    "City": "Princeton",
    "State": "New Jersey",
    "Zip": "08540",
    "Software version": "Fire OS 5.2.6.9 (6325552020)",
    "Email": "...",
    "Password": "...",
    "Wifi SSID": "...",
}


MANUAL_ROKU_CRAWL = {
    "first_name1": "...",
    "last_name1": "...",
    "full_name1": "......",
    "address_line1": "...",
    "address_line2": "...",
    "address_line3": "...",
    "address_line4": "...",
    "address_line5": "...",
    "zip_code1": "...",
    "first_name2": "...",
    "last_name2": "...",
    "full_name2": "...",
    "zip_code2": "08544",
    "phone1": "1234567890",
    "phone2": "123-456-7890",
    "phone3": "+1-123-456-7890",
    "phone4": "2345678901",
    "phone5": "234-567-8901",
    "phone6": "+1-234-567-8901",
    "credit_card1": "0000-0000-0000-0000",
    "credit_card2": "0000000000000000",
    "gender": "male",
    "email1": "...",
    "email2": "...",
    "username1": "...",
    "username2": "...",
    "password1": "...",
    "password2": "...",
    "password3": "...",
    "dob1": "04/04/1990",
    "dob2": "04/04/90",
    "dob3": "04-04-1990",
    "dob4": "04-04-90",
    "first_name3": "...",
    "last_name3": "...",
}

MANUAL_AMAZON_CRAWL = {
    "email3": "...",
    "email4": "...",
    "username3": "...",
    "username4": "...", #typo
    "credit_card3": "0000000000000000",
    "credit_card4": "0000-0000-0000-0000"
}

# Uncomment the following lines when detecting manual crawl leaks
# ROKU_IDS.update(MANUAL_ROKU_CRAWL)
# AMAZON_FIRE_TV_STICK_3_IDS.update(MANUAL_ROKU_CRAWL)
# AMAZON_FIRE_TV_STICK_3_IDS.update(MANUAL_AMAZON_CRAWL)


TV_ID_MAP_V1 = {
    "b0:fc:0d...": AMAZON_FIRE_TV_CUBE_IDS,
    "68:9a:87...": AMAZON_FIRE_TV_STICK_IDS,
    "d8:31:34...": ROKU_IDS,
    "d8:31:34...": ROKU_IDS_2,
    "1c:12:b0...": AMAZON_FIRE_TV_STICK_2_IDS,
    "68:9a:87...": AMAZON_FIRE_TV_STICK_3_IDS,
}

# IDs updated after the factory reset
TV_ID_MAP = {
    "b0:fc:0d...": AMAZON_FIRE_TV_CUBE_IDS,
    "68:9a:87...": AMAZON_FIRE_TV_STICK_IDS_FACTORY_RESET,
    "d8:31:34...": ROKU_IDS,
    "d8:31:34...": ROKU_IDS_2,
    "1c:12:b0...": AMAZON_FIRE_TV_STICK_2_IDS,
    "68:9a:87...": AMAZON_FIRE_TV_STICK_3_IDS,
}

