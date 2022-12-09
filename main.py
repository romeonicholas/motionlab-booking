#Built-in modules
import utime
from machine import Pin, PWM

#External modules, sources noted in each module
import logging
from mfrc522 import MFRC522

#API functions
from helper_functions import get_membership_id,get_current_booking,create_booking,update_booking,delete_booking,get_checkin_token_from_badge,get_bookings_in_range
#Local functions
from helper_functions import get_now,create_formatted_time_string,get_time_from_string,file_or_dir_exists,is_booking_less_than_five_minutes_old,configure_device,set_time_to_UTC,connect_to_wifi,update_or_delete_booking,get_resource_availability,play_song,set_led_lights
#WiFi info, resource ID
import secrets

##### STARTUP #####

#Logging
logging.basicConfig(filename="log_{}.txt".format(secrets.RESOURCE_ID), filemode='w', format="%(asctime)s:%(levelname)-7s:%(name)s:%(message)s")
logger = logging.getLogger("main_logger")

#Hardware
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
buzzer = PWM(Pin(15))
led_available = [Pin(11, Pin.OUT)]
led_booked = [Pin(6, Pin.OUT), Pin(7, Pin.OUT), Pin(8, Pin.OUT)]
led_checked_in = [Pin(22, Pin.OUT)]
led_error = [Pin(20, Pin.OUT)]

led_available[0].value(0)
led_checked_in[0].value(0)
led_error[0].value(0)
for led in led_booked:
    led.value(0)

last_led_status = led_error

#Wifi and time
connect_to_wifi()
set_time_to_UTC()

#Cobot access token and current availability
OAUTH_TOKEN = configure_device()
current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)
is_resource_available = get_resource_availability(current_booking, secrets.RESOURCE_ID, OAUTH_TOKEN)

booking_end_time = 0
if current_booking != {}:
    booking_end_time = get_time_from_string(current_booking["to"])
    

previous_card = [0] #Limits rapid re-reading of RFID badges
is_user_checked_in_to_booking = False #Tracks whether user with active booking has badged in
last_user_token_and_id = {} #Limits unecessary API calls when same user badges concurrently
membership_id = ""

#Timer-related

onsite_booking_creation_time = utime.time() #For checking whether enough time has passed for API ping or booking cancellation                
availability_update_time = utime.time() #For spacing out API calls to check resource availability
TIMER_S = 300 #5 minutes in seconds

#Frequencies for buzzer feedback
card_read_song = [784, 784, 784]
success_song = [440, 523, 698, 698, 698]
error_song = [440, 196, 175, 175, 175]

##### BEGINNING OF INTERACTABLE PROGRAM #####

try:
    print("RFID reader active\n")

    #This section updates constantly until a card is detected
    while True:        
        #if is_resource_available:
        if current_booking == {}:
            last_led_status = set_led_lights(led_available, last_led_status)

            if (utime.time() - availability_update_time) > TIMER_S:
                print("Checking for booking (every {} seconds)\n".format(TIMER_S))
                #is_resource_available = get_resource_availability(current_booking, secrets.RESOURCE_ID, OAUTH_TOKEN)
                current_booking = get_current_booking(secrets.RESOURCE_ID, OAUTH_TOKEN)
                availability_update_time = utime.time()
                
                if current_booking != {}:
                    booking_end_time = get_time_from_string(current_booking["to"])
                    
        else:
            if not is_user_checked_in_to_booking:
                last_led_status = set_led_lights(led_booked, last_led_status)
            if utime.time() > booking_end_time:
                print("Booking cleared because its end time had been reached\n")
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
                play_song(buzzer, card_read_song)

                user_checkin_token = get_checkin_token_from_badge(uid)
                membership_id = get_membership_id(user_checkin_token, OAUTH_TOKEN, last_user_token_and_id)
                last_user_token_and_id = {user_checkin_token: membership_id}
                
                if membership_id is "":
                    print("Membership ID is invalid, cannot book resource\n")
                    play_song(buzzer, error_song)
                else:
                    #if is_resource_available:
                    if current_booking == {}:
                        current_booking = create_booking(
                            membership_id,
                            OAUTH_TOKEN,
                            secrets.RESOURCE_ID,
                        )
                        
                        booking_end_time = get_time_from_string(current_booking["to"])
                        
                        if current_booking == {}:
                            print("Booking creation failed\n")
                            play_song(buzzer, error_song)
                        else:
                            print("User is checked in for the booking they just created\n")
                            play_song(buzzer, success_song)
                            is_user_checked_in_to_booking = True
                            onsite_booking_creation_time = utime.time()
                            is_resource_available = False
                            last_led_status = set_led_lights(led_checked_in, last_led_status)
                    else:
                        print("Resource is currently booked\n")
                        
                        if membership_id == current_booking["membership_id"]:
                            print("User who swiped badge has the current booking\n")
                            
                            if is_user_checked_in_to_booking == False:
                                print("User is now checked in for their booking\n")
                                play_song(buzzer, success_song)
                                is_user_checked_in_to_booking = True
                                last_led_status = set_led_lights(led_checked_in, last_led_status)
                                
                                if(utime.time() - get_time_from_string(current_booking["from"])) > TIMER_S:
                                    update_booking(current_booking["id"], OAUTH_TOKEN, "start_time")

                                #TODO: Show something to confirm the user has started their booking
                            else:
                                print("User was already checked in for their booking, booking will be updated or deleted\n")
                                update_or_delete_booking(current_booking["id"], OAUTH_TOKEN, onsite_booking_creation_time, TIMER_S)
                                current_booking = {}
                                is_user_checked_in_to_booking = False
                                
                                #TODO: Show something to confirm the user has ended their booking
                        else:
                            print("This member ID does not match the member ID of the current booking\n")

                previous_card = uid
        utime.sleep_ms(50)

except KeyboardInterrupt:
    pass

