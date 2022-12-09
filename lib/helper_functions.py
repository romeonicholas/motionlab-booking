import os
import utime
import logging
import urequests
import ntptime
import network

import secrets
  
logging.basicConfig(filename="log_{}.txt".format(secrets.RESOURCE_ID), filemode='w', format="%(asctime)s:%(levelname)-7s:%(name)s:%(message)s")
logger = logging.getLogger("api_helper_logger")

##### API FUNCTIONS #####

#Returns access token required for interacting with the Cobot API
def get_access_token(client_id, client_secret, scope, admin_email, admin_password):
    access_token = ""
    print("Attempting to retrieve Token with scopes: {}".format(scope))

    try:
        request = urequests.post(
            "https://www.cobot.me/oauth/access_token?scope="
            + scope
            + "&grant_type=password&username="
            + admin_email
            + "&password="
            + admin_password
            + "&client_id="
            + client_id
            + "&client_secret="
            + client_secret
        ) 
        if request.status_code == 200:
            access_token = request.json()["access_token"]
            print("Successfully retrieved access token with scopes: {}\n".format(scope))
            return access_token
        else:
            logging.error("get_oauth_token failed withstatus code %d and response %s" % (request.status_code,request.json()))
    except Exception as e:
        logging.error("get_oauth_token failed with exception: %s" % e)

#Returns membership id from check-in token 
def get_membership_id(user_checkin_token, access_token, last_user_token_and_id):
    membership_id = ""
    
    if user_checkin_token in last_user_token_and_id:
        membership_id = last_user_token_and_id[user_checkin_token]
        print("Membership ID was already locally available: {}\n".format(membership_id))
    else:
        try:
            request = urequests.get(
                "https://members.motionlab.berlin/api/check_in_tokens/"
                + user_checkin_token
                + "?access_token="
                + access_token
            )

            if request.status_code == 200:
                membership_id = request.json()["membership"]["id"]
                print("Associated membership id: {}\n".format(membership_id))
            else:
                logging.error("get_membership_id returned status code %d and following response: %s" % (request.status_code, request.json()))
        except Exception as e:
            logging.error("get_membership_id had following exception: %s" % e)
        
    return membership_id

def get_bookings_in_range(resource_id, access_token, time_range_start, time_range_end):
    bookings = []
    
    data = {"from": time_range_start, "to": time_range_end}
    
    try:
        request = urequests.get("https://members.motionlab.berlin/api/resources/"
                                + resource_id
                                + "/bookings?access_token="
                                + access_token,
                                json=data)
        if request.status_code == 200:

            if request.json():
                bookings = request.json()
                print("Resource is booked at some point between {} and {}: {}\n".format(time_range_start, time_range_end, current_booking))
            else:
                print("Resource is not booked at any point between {} and {}\n".format(time_range_start, time_range_end))
        else:
            logging.error("get_booking_in_range failed with the following status code: %d" % request.status_code())
            logging.error(request.json())
    except Exception as e:
            logging.error("get_booking_in_range failed following exception: %s" % e)

    return bookings

def get_current_booking(resource_id, access_token):
    current_booking = {}
    now = get_now()
    time_range_start = create_formatted_time_string(now)
    
    one_minute_from_now = utime.localtime(utime.mktime((now[0],
                                                        now[1],
                                                        now[2],
                                                        now[3],
                                                        now[4] + 1,
                                                        now[5],
                                                        now[6],
                                                        now[7])))
    time_range_end = create_formatted_time_string(one_minute_from_now)
                
    data = {"from": time_range_start, "to": time_range_end}

    try:
        request = urequests.get("https://members.motionlab.berlin/api/resources/"
                                + resource_id
                                + "/bookings?access_token="
                                + access_token,
                                json=data)
        if request.status_code == 200:

            if request.json():
                current_booking = request.json()[0]
                print("Resource is booked: {}\n".format(current_booking))
            else:
                print("Resource is not currently booked\n")
        else:
            logging.error("get_current_booking failed with the following status code: %d" % request.status_code())
            logging.error(request.json())
    except Exception as e:
            logging.error("get_current_booking failed following exception: %s" % e)

    return current_booking

def create_booking(membership_id, access_token, resource_id):
    booking = {}
    now = get_now()
    booking_starting_time = create_formatted_time_string(now)

    thirty_minutes_from_now = utime.localtime(utime.mktime((now[0],
                                                            now[1],
                                                            now[2],
                                                            now[3],
                                                            now[4] + 30,
                                                            now[5],
                                                            now[6],
                                                            now[7])))
    booking_ending_time = create_formatted_time_string(thirty_minutes_from_now)
    
    data = {
        "membership_id": membership_id,
        "from": booking_starting_time,
        "to": booking_ending_time,
        "title": "On-site Booking",
        "comments": "This booking was made on-site at MotionLab using your badge. "
            + "If you'd like to end the booking earlier than the default 30 minutes, "
            + "swipe your badge at the same location when you're finished in order to "
            + "make it available again to other members."
        }
        
    try:
        request = urequests.post("https://members.motionlab.berlin/api/resources/"
                                 + resource_id
                                 + "/bookings?access_token="
                                 + access_token,
                                 json=data)
        if request.status_code == 201:
            booking = request.json()
            print("Successfully created booking: {}\n".format(booking))
        else:
            logging.error("create_booking with following status code %d and response: %s" % (request.status_code, request.json()))
    except Exception as e:
            logging.error("create_booking failed with following exception: %s" % e)
            
    return booking

def update_booking(booking_id, access_token, start_or_end_time):
    updated_booking = {}
    
    data = {}
    now = create_formatted_time_string(get_now())
    
    if start_or_end_time == "start_time":
        data = {"from": now}
    elif start_or_end_time == "end_time":
        data = {"to": now}
                
    try:
        request = urequests.put("https://members.motionlab.berlin/api/bookings/"
                                + booking_id + "/?access_token="
                                + access_token,
                                json=data)
        if request.status_code == 200:
            updated_booking = request.json()
            print("Successfully updated booking {}: {}\n".format(start_or_end_time, updated_booking))
        else:
            logging.error("update_booking failed with status code %d and response %s\n" % (request.status_code, request.json()))
    except Exception as e:
            logging.error("update_booking failed with following exception: %s" % e)
    return updated_booking

def delete_booking(booking_id, access_token):
    try:
        request = urequests.delete("https://members.motionlab.berlin/api/bookings/"
                                + booking_id + "/?access_token="
                                + access_token)
        if request.status_code == 204:
            print("Successfully deleted booking within 5 minutes of creation\n")
        elif request.status_code == 409:
            logging.error("delete_booking failed with status code 409: cannot delete a booking created by an event through this endpoint\n")
    except Exception as e:
            logging.error("delete_booking failed with following exception: %s" % e)
            
##### LOCAL FUNCTIONS #####

#Returns RFID badge UID in format that matches MotionLab's checkin token format
def get_checkin_token_from_badge(uid):
    #print(reader.tohexstring(uid))                             #e.g. [0x04, 0x0F, 0x2C, 0x82, 0xDC, 0x72, 0x80]
    #print(bytes(uid))                                          #e.g. b'\x04\x0f,\x82\xdcr\x80'
    #print(int.from_bytes(bytes(uid),"little",False))           #e.g. 36155088421261060
    #print(hex(int.from_bytes(bytes(uid),"little",False)))      #e.g. 0x8072dc822c0f04
    #print (hex(int.from_bytes(bytes(uid),"little",False))[8:]) #e.g. 822c0f04

    #String representaiton of the decimal value of the last 4 bytes of a 7 byte MiFare RFID badge
                                                                #e.g. 2183925508
    user_checkin_token = str(int(hex(int.from_bytes(bytes(uid), "little", False))[8:], 16))
    
    print("Badge read, user's check-in token: {}\n".format(user_checkin_token))

    return user_checkin_token

#def uidToString(uid):
#    mystring = ""
#    for i in uid:
#        mystring = "%02X" % i + mystring
#    return mystring

def get_now():
    return utime.localtime()

def create_formatted_time_string(unformatted_time):
    return "{}/{}/{} {}:{}:00 +0000".format(unformatted_time[0], #year
                                            unformatted_time[1], #month
                                            unformatted_time[2], #date
                                            unformatted_time[3], #hours
                                            unformatted_time[4]) #minutes

def get_time_from_string(time_string):
    #2022/12/05 09:42:00 +0000 <- format of input strings
    now = get_now()
    new_time = utime.mktime((int(time_string[0:4]),   #year
                             int(time_string[5:7]),   #month
                             int(time_string[8:10]),  #date
                             int(time_string[11:13]), #hours
                             int(time_string[14:16]), #minutes
                             0,                       #seconds
                             now[6],                  #weekday
                             now[7]))                 #yearday
    return new_time

def get_time_in_future(difference_in_minutes):
    now = get_now()
    time_in_future = utime.mktime((now[0],
                                    now[1],
                                    now[2],
                                    now[3],
                                    now[4] + difference_in_minutes,
                                    now[5],
                                    now[6],
                                    now[7]))
    return time_in_future

def get_end_of_day_time():
    now = get_now()
    end_of_day = utime.mktime((now[0],
                                now[1],
                                now[2],
                                20,
                                30,
                                0,
                                now[6],
                                now[7]))
    return end_of_day

#Credit: dhylands at https://forum.micropython.org/viewtopic.php?t=8112#p68368
def file_or_dir_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

#TODO: Finish method, put into program logic
def is_booking_less_than_five_minutes_old(created_at):
    now = get_now()
    five_minutes_ago = utime.localtime(utime.mktime((now[0],
                                                     now[1],
                                                     now[2],
                                                     now[3],
                                                     now[4] - 5,
                                                     now[5],
                                                     now[6],
                                                     now[7])))
    
    booking_created_time = utime.localtime(utime.mktime((created_at[0,3],
                                                         created_at[5,6],
                                                         created_at[8,9],
                                                         created_at[11,12],
                                                         created_at[14,15],
                                                         0,
                                                         0,
                                                         0)))

def configure_device():
    access_token = ""
    
    if file_or_dir_exists("token.txt"):
        f = open("token.txt")
        access_token = f.read()
        f.close()   
    else:
        print("Please answer the following questions to generate an OAUTH token for this client.")
        print("None of your entered data will be stored locally, it will be deleted as soon as a token is generated.\n")
        
        print("Please enter the booking program's client ID (from https://www.cobot.me/oauth2_clients)")
        client_id = input()
        
        print("\nPlease enter the booking program's client secret (from https://www.cobot.me/oauth2_clients)")
        client_secret = input()

        print("\nPlease enter your MotionLab admin account email")
        admin_email = input()
        
        print("\nPlease enter your MotionLab admin account password")
        admin_password = input()
        print("")
        
        access_token = get_access_token(
            client_id,
            client_secret,
            "checkin_tokens,read_bookings,write_bookings",
            admin_email,
            admin_password
        )
        
        try:
            token_file = open('token.txt', 'w')
            token_file.write(access_token)
            token_file.close()
            print("Successfully wrote access token to token.txt\n")
        except Exception as e:
            logging.error("Writing access token to token.txt failed with exception %s" % e)
    
    return access_token

def connect_to_wifi():
    print("Connecting to WiFi...")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    wlan.connect(secrets.SSID, secrets.SSID_PASSWORD)
    while not wlan.isconnected():
        utime.sleep_ms(500)
        print(".")
        
    print("Connected to WiFi\n")
    
def set_time_to_UTC():
    try:
        ntptime.settime()
        print("UTC Time：{}\n".format(utime.localtime()))
    except Exception as e:
        logging.error("Error syncing time: %s" % e)
    
def update_or_delete_booking(booking_id, access_token, onsite_booking_creation_time, update_time_limit):
    if (utime.time() - onsite_booking_creation_time) < update_time_limit:
        delete_booking(booking_id, access_token)
    else:
        update_booking(booking_id, access_token, "end_time")

def get_resource_availability(current_booking, resource_id, access_token):
    if current_booking != {}:
        return False
    else:
        start_time_range = create_formatted_time_string(utime.localtime(utime.time()))
        end_time_range = create_formatted_time_string(utime.localtime((utime.time() + (60*30))))
        booking_in_next_31_minutes = get_bookings_in_range(resource_id, access_token, start_time_range, end_time_range)
        
        if booking_in_next_31_minutes != {}:
            return False
        else:
            return True

#Buzzer functions
def play_song(buzzer, song):
    buzzer.duty_u16(1000)

    for frequency in song:
        buzzer.freq(frequency)
        utime.sleep(0.1)
        
    buzzer.duty_u16(0)
    
def update_availability_display(pixels, resource_id, access_token):
    time_range_start = create_formatted_time_string(utime.localtime())
    time_range_end = create_formatted_time_string(utime.localtie(get_end_of_day))
    
    bookings = get_bookings_in_range(resource_id, access_token, time_range_start, time_range_end)
    half_hour_slots_from_6_to_20_30 = [0] * 30
    
def set_led_lights(new_status, last_status):
    if new_status != last_status:
        for led in last_status:
            led.value(0)
        for led in new_status:
            led.value(1)
        
    return new_status
    
