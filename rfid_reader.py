from mfrc522 import MFRC522
import utime
import network
import urequests

import secrets

### CLASSES ###

#Access tokens required for interacting with the Cobot API
class Tokens:
    def __init__(self, client_id, client_secret, scope, usr, pwd):
        self.id = client_id
        self.secret = client_secret
        self.scope = scope
        self.usr = usr
        self.pwd = pwd
        
        print("Attempting to retrieve Token with scope: {}".format(scope))

        try:
            request = urequests.post(
                "https://www.cobot.me/oauth/access_token?scope="
                + self.scope
                + "&grant_type=password&username="
                + self.usr
                + "&password="
                + self.pwd
                + "&client_id="
                + self.id
                + "&client_secret="
                + self.secret
            ) 
            if request.status_code == 200:
                self.access_token = request.json()["access_token"]
                print("Successfully retrieved access token with scope: {}\n".format(scope))

            else:
                print("Failed to retrieve token, status code: {} ".format(request.status_code))
                print(request.json())
        except Exception as e:
            print("Error in token creation: ", e)

### FUNCTIONS ###

## HELPER FUNCTIONS ##
            
#Returns RFID badge UID in format that matches MotionLab's checkin token format
def read_user_checkin_token(uid):
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
    return utime.localtime(utime.time())

def create_formatted_time_string(unformatted_time):
    return "{}/{}/{} {}:{}:00 +0000".format(unformatted_time[0],
                                            unformatted_time[1],
                                            unformatted_time[2],
                                            unformatted_time[3],
                                            unformatted_time[4])

## API FUNCTIONS ##

#Returns membership id from check-in token 
def get_membership_id(user_checkin_token, access_token):
    membership_id = 0
    
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
            print("Getting member ID did not return 200")
            print(request.status_code)
            print(request.json())
    except:
        print("Error in getting member ID: ", e)
        
    return membership_id

def get_current_booking(resource_id, access_token):
    current_booking = {}
    
    now = get_now()
    booking_starting_time = create_formatted_time_string(now)
    
    thirty_one_minutes_from_now = utime.localtime(utime.mktime((now[0],
                                                                now[1],
                                                                now[2],
                                                                now[3],
                                                                now[4] + 31,
                                                                now[5],
                                                                now[6],
                                                                now[7])))
    booking_ending_time = create_formatted_time_string(thirty_one_minutes_from_now)
                
    data = {"from": booking_starting_time, "to": booking_ending_time}
    
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
                print("Resource is available\n")
        else:
            print("Getting resource availability failed with the following status code: {}".format(request.status_code()))
            print(request.json())
    except Exception as e:
            print("Error: ", e)

    return current_booking

def create_booking(membership_id, access_token, resource_id):
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
            print("Successfully created booking: {}".format(request.json()))
            print("")
        elif request.status_code == 422:
            print("Booking request failed")
            print(request.json())
    except Exception as e:
            print("Error: ", e)
    return request.json()

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
    
    #created_at = '2022/12/01 19:30:19 +0000'
    booking_created_time = utime.localtime(utime.mktime((created_at[0,3],
                                                         created_at[5,6],
                                                         created_at[8,9],
                                                         created_at[11,12],
                                                         created_at[14,15],
                                                         0,
                                                         0,
                                                         0)))
    
    
    print(now - five_minutes_ago)


def end_booking(booking_id, access_token):
    updated_booking = {}
    booking_ending_time = create_formatted_time_string(get_now())

    data = {"to": booking_ending_time}
        
    try:
        request = urequests.put("https://members.motionlab.berlin/api/bookings/"
                                + booking_id + "/?access_token="
                                + access_token,
                                json=data)
        if request.status_code == 200:
            updated_booking = request.json()
            print("Successfully ended booking early: {}".format(request.json()))
        elif request.status_code == 422:
            print("Ending booking early failed")
    except Exception as e:
            print("Error: ", e)
    return updated_booking

def delete_booking(booking_id, access_token):
    try:
        request = urequests.delete("https://members.motionlab.berlin/api/bookings/"
                                + booking_id + "/?access_token="
                                + access_token)
        if request.status_code == 204:
            print("Successfully deleted booking within 5 minutes of creation")
        elif request.status_code == 409:
            print("Cannot delete bookings made by an event through this endpoint")
    except Exception as e:
            print("Error: ", e)

###STARTUP###

#Connect to internet

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

wlan.connect(secrets.SSID, secrets.SSID_PASSWORD)

print("Connecting to WiFi...")
while not wlan.isconnected():
    utime.sleep_ms(500)
    print(".")
print("Connected to WiFi")
print("")

#Generate OAuth token for API calls
OAUTH_TOKEN = Tokens(
    secrets.CLIENT_ID,
    secrets.CLIENT_SECRET,
    "checkin_tokens,read_bookings,write_bookings",
    secrets.USER,
    secrets.USER_PASSWORD
)

#Set up RFID reader with specific I/O
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)

#Used to limit unecessary instant re-reading of RFID badges
previous_card = [0]

#Used to determine whether a booking is currently active at startup
current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN.access_token)

#Timer for cancelling booking, initalize at startup so ongoing bookings can be canceled after reboot
onsite_booking_creation_time = utime.ticks_ms()
                
#Enables ending a booking early (badging again after being checked in)
is_user_checked_in_to_booking = False

#Limits unecessary API calls when same user badges concurrently
last_user_token_and_id = {}
membership_id = 0

#Timer for spacing out API calls to check resource availability
availability_update_timer_start = utime.ticks_ms()
TIMER_MS = 300000 #5 minutes

### BEGINNING OF INTERACTABLE PROGRAM ###

#TODO: Explore whether this can be done on single thread so second thread can do something else
#Possibilities: act as a web server to receive booking callbacks to update schedule,
#poll API for availability, flash status lights
try:
    print("RFID reader active\n")

    while True:
        #This section updates constantly until a card is detected
        time_now = utime.ticks_ms()
        
        if current_booking == {}:
            if (utime.ticks_diff(time_now, availability_update_timer_start) > TIMER_MS):
                #enough time has passed to check for availability again
                current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN.access_token)
                availability_update_timer_start = time_now

        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
                
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if uid == previous_card:
                continue
            
            if stat == reader.OK:
                #This section will only run when an acceptable RFID card is detected

                #Get check-in token from RFID badge
                user_checkin_token = read_user_checkin_token(uid)
                
                #Get membership id for user based on check-in token
                if user_checkin_token in last_user_token_and_id:
                    membership_id = last_user_token_and_id[user_checkin_token]
                    print("Membership ID was already locally available: {}\n".format(membership_id))
                else:
                    membership_id = get_membership_id(user_checkin_token, OAUTH_TOKEN.access_token)
                    last_user_token_and_id = {
                        user_checkin_token: membership_id,
                        }
                    print("Membership ID was not previously locally available, but will be until current booking ends\n")
                
                if current_booking == {}:
                    #Resource is available, create booking for user starting now for default length
                    current_booking = create_booking(
                        membership_id,
                        OAUTH_TOKEN.access_token,
                        secrets.RESOURCE_ID,
                    )
                    
                    #Check user in and start timer for cancellation/update check
                    is_user_checked_in_to_booking = True
                    onsite_booking_creation_time = utime.ticks_ms()
                    print("User is checked in for the booking they just created\n")
                else:
                    #Resource is currently booked
                    
                    if membership_id == current_booking["membership_id"]:
                        print("User who swiped badge has the current booking\n")
                        
                        if is_user_checked_in_to_booking == False:
                            is_user_checked_in_to_booking = True
                            print("User is now checked in for their booking\n")
                            
                            #TODO: Show something to confirm the user has started their booking
                        else:
                            if (utime.ticks_diff(time_now, onsite_booking_creation_time) < TIMER_MS):
                                #Booking is less than 5 minutes old
                                delete_booking(current_booking["id"], OAUTH_TOKEN.access_token)
                            else:
                                end_booking(current_booking["id"], OAUTH_TOKEN.access_token)

                            #Reset status of booking device
                            current_booking = {}
                            is_user_checked_in_to_booking = False
                            last_user_token_and_id = {}
                            
                            #TODO: Show something to confirm the user has ended their booking
                    else:
                        #User who swiped does not have current reservation
                        print("A different member has reserved this machine\n")
                previous_card = uid
            else:
                pass
        else:
            previous_card = [0]
        
        utime.sleep_ms(50)

except KeyboardInterrupt:
    pass
