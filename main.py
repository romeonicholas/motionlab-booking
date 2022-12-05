#Built-in modules
import utime
from machine import Pin #temp, remove after external audio/video cues added

#External modules, sources noted in each module
import logging
from mfrc522 import MFRC522

#User-created helpers and files specifically for this program
from helper_functions import get_membership_id,get_current_booking,create_booking,update_booking,delete_booking,get_checkin_token_from_badge
from helper_functions import get_now,create_formatted_time_string,get_time_from_string,file_or_dir_exists,is_booking_less_than_five_minutes_old,configure_device,set_time_to_UTC,connect_to_wifi,update_or_delete_booking
import secrets


##### STARTUP #####

#Logging
logging.basicConfig(filename="log_{}.txt".format(secrets.RESOURCE_ID), filemode='w', format="%(asctime)s:%(levelname)-7s:%(name)s:%(message)s")
logger = logging.getLogger("main_logger")

#Hardware
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
led = Pin("LED", machine.Pin.OUT) #temp, remove after external audio/video cues added

#Wifi and time
connect_to_wifi()
set_time_to_UTC()

#Cobot access token and current availability
OAUTH_TOKEN = configure_device()
current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)
#is_device_available: no current booking, no booking for next 36 minutes (30 + 5 for API refresh + 1 for wiggle room)

booking_end_time = 0
if current_booking != {}:
    booking_end_time = get_time_from_string(current_booking["to"])
    

previous_card = [0] #Limits rapid re-reading of RFID badges
is_user_checked_in_to_booking = False #Tracks whether user with active booking has badged in
last_user_token_and_id = {} #Limits unecessary API calls when same user badges concurrently
membership_id = ""

#Timer-related
onsite_booking_creation_time = utime.ticks_ms() #Tracks whether enough time has passed for API ping or booking cancellation                
availability_update_timer_start = utime.ticks_ms() #Timer for spacing out API calls to check resource availability
#TIMER_MS = 300000 #5 minutes in MS
TIMER_MS = 60000 #1 minute in MS


##### BEGINNING OF INTERACTABLE PROGRAM #####

try:
    print("RFID reader active\n")

    #This section updates constantly until a card is detected
    while True:        
        if current_booking == {}:
            print("There is no current booking")
            if (utime.ticks_diff(utime.ticks_ms(), availability_update_timer_start) > TIMER_MS):
                print("Checking for booking after given time\n")
                current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)
                availability_update_timer_start = utime.ticks_ms()
                
                if current_booking != {}:
                    booking_end_time = get_time_from_string(current_booking["to"])
    
        else:
            print(utime.mktime(get_now()), booking_end_time)
            if utime.mktime(get_now()) > booking_end_time:
                print("Booking cleared because it's end time had been reached\n")
                current_booking = {}

        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
         
        if stat != reader.OK:
            previous_card = [0]
        else:
            (stat, uid) = reader.SelectTagSN()
            
            #Prevents immediate re-read on same card
            if uid == previous_card:
                continue
            
            if stat != reader.OK:
                pass
            else:
                #This section will only run when an acceptable RFID card is detected
                led.on() #temp, remomve after external feedback added, stays on until program has finished processing badge swipe

                user_checkin_token = get_checkin_token_from_badge(uid)
                membership_id = get_membership_id(user_checkin_token, OAUTH_TOKEN, last_user_token_and_id)
                last_user_token_and_id = {user_checkin_token: membership_id}
                
                if membership_id is "":
                    print("Membership ID is invalid, cannot book resource\n")
                else:
                    if current_booking == {}:
                        current_booking = create_booking(
                            membership_id,
                            OAUTH_TOKEN,
                            secrets.RESOURCE_ID,
                        )
                        
                        booking_end_time = get_time_from_string(current_booking["to"])
                        #availability_update_timer_start = utime.ticks_ms()
                        
                        if current_booking == {}:
                            print("Booking creation failed\n")
                        else:
                            print("User is checked in for the booking they just created\n")
                            is_user_checked_in_to_booking = True
                            onsite_booking_creation_time = utime.ticks_ms()
                    else:
                        print("Resource is currently booked\n")
                        
                        if membership_id == current_booking["membership_id"]:
                            print("User who swiped badge has the current booking\n")
                            
                            if is_user_checked_in_to_booking == False:
                                print("User is now checked in for their booking\n")
                                is_user_checked_in_to_booking = True
                                update_booking(current_booking["id"], OAUTH_TOKEN, "start_time")

                                #TODO: Show something to confirm the user has started their booking
                            else:
                                print("User was already checked in for their booking, booking will be updated or deleted\n")
                                update_or_delete_booking(current_booking["id"], OAUTH_TOKEN, onsite_booking_creation_time, TIMER_MS)
                                current_booking = {}
                                is_user_checked_in_to_booking = False
                                
                                #TODO: Show something to confirm the user has ended their booking
                        else:
                            print("This member ID does not match the member ID of the current booking\n")

                previous_card = uid
                led.off() #temp, remomve after external feedback added, turns off after actions post-badging are finished
        utime.sleep_ms(50)

except KeyboardInterrupt:
    pass

