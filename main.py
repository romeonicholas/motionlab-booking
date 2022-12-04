#Built-in modules
import utime
import ntptime
import network
from machine import Pin #temp, remove after external audio/video cues added

#External modules, sources noted in each module
import logging
from mfrc522 import MFRC522

#User-created helpers and files specifically for this program
from helper_functions import get_membership_id,get_current_booking,create_booking,update_booking,delete_booking,read_user_checkin_token,get_now,create_formatted_time_string,file_or_dir_exists,is_booking_less_than_five_minutes_old,configure_device
import secrets

#Due to space and security constraints, logging will only contain exceptions, not the
#printed info messages more useful for active debugging
logging.basicConfig(filename="log_{}.txt".format(secrets.RESOURCE_ID), filemode='w', format="%(asctime)s:%(levelname)-7s:%(name)s:%(message)s")
logger = logging.getLogger("main_logger")

led = Pin("LED", machine.Pin.OUT)

### CLASSES ###

#Access tokens required for interacting with the Cobot API
class Tokens:
    def __init__(self, client_id, client_secret, scope, usr, pwd):
        self.id = client_id
        self.secret = client_secret
        self.scope = scope
        self.usr = usr
        self.pwd = pwd
        
        print("Attempting to retrieve Token with scope: %s",(scope))

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
                print("Successfully retrieved access token with scope: %s\n",(scope))

            else:
                logging.error("Failed to retrieve token, status code: %s ",(request.status_code))
                logging.error(request.json())
        except Exception as e:
            logging.error("Error in token creation: %s" % e)


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

try:
  ntptime.settime()
  print("UTC Time：{}".format(utime.localtime()))
except Exception as e:
  logging.error("Error syncing time: %s" % e)

OAUTH_TOKEN = ""

#On first boot no token exists, run through configuration
if not file_or_dir_exists("token.txt"):
    print("*** First boot, configuring device ***")
    OAUTH_TOKEN = configure_device()
else:
    #Already configured, read from file to get OAUTH token
    f = open("token.txt")
    OAUTH_TOKEN = f.read()
    f.close()    

#Set up RFID reader with specific I/O
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)

#Used to limit unecessary instant re-reading of RFID badges
previous_card = [0]

#Used to determine whether a booking is currently active at startup
current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)

#Timer for cancelling booking, initalize at startup so ongoing bookings can be canceled after reboot
onsite_booking_creation_time = utime.ticks_ms()
                
#Enables ending a booking early (badging again after being checked in)
is_user_checked_in_to_booking = False

#Limits unecessary API calls when same user badges concurrently
last_user_token_and_id = {}
membership_id = ""

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
                current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)
                availability_update_timer_start = time_now

        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
                
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if uid == previous_card:
                continue
            
            if stat == reader.OK:
                #This section will only run when an acceptable RFID card is detected
                led.on() #temp, remomve after external feedback added, turns on after badge detected

                #Get check-in token from RFID badge
                user_checkin_token = read_user_checkin_token(uid)
                
                
                #If user has already badged in, use existing ID, if not, get it
                if user_checkin_token in last_user_token_and_id:
                    membership_id = last_user_token_and_id[user_checkin_token]
                    print("Membership ID was already locally available: {}\n".format(membership_id))
                #Get member id using check-in token
                else:
                    membership_id = get_membership_id(user_checkin_token, OAUTH_TOKEN)
                    
                    
                #If membership id exists, can book new reservation    
                if membership_id != "":
                    #Store member ID in case they badge in again
                    last_user_token_and_id = {
                        user_checkin_token: membership_id,
                        }
                    print("Membership ID was not previously locally available, but will be until current booking ends\n")
                
                    #If resource is available and member ID exists, create booking
                    if current_booking == {}:
                        current_booking = create_booking(
                            membership_id,
                            OAUTH_TOKEN,
                            secrets.RESOURCE_ID,
                        )
                        
                        #TODO add logic for if booking creation fails
                        
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
                                update_booking(current_booking["id"], OAUTH_TOKEN, "start_time")

                                print("User is now checked in for their booking\n")
                                
                                #TODO: Show something to confirm the user has started their booking
                            else:
                                if (utime.ticks_diff(time_now, onsite_booking_creation_time) < TIMER_MS):
                                    #Booking is less than 5 minutes old
                                    delete_booking(current_booking["id"], OAUTH_TOKEN)
                                else:
                                    update_booking(current_booking["id"], OAUTH_TOKEN, "end_time")

                                #Reset status of booking device
                                current_booking = {}
                                is_user_checked_in_to_booking = False
                                last_user_token_and_id = {}
                                
                                #TODO: Show something to confirm the user has ended their booking
                        else:
                            #User who swiped does not have current reservation
                            print("A different member has reserved this machine\n")
                else:
                    print("Membership ID is 0, can't book")
                previous_card = uid
                
                led.off() #temp, remomve after external feedback added, turns off after actions post-badging are finished
            else:
                pass
        else:
            previous_card = [0]
        
        utime.sleep_ms(50)

except KeyboardInterrupt:
    pass

