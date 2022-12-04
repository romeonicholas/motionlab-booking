import os
import utime
import logging
import urequests

logging.basicConfig(format="%(asctime)s:%(levelname)-7s:%(name)s:%(message)s")
logger = logging.getLogger("api_helper_logger")

##### API FUNCTIONS #####

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
            logging.error("Getting member ID did not return 200")
            logging.error(request.status_code)
            logging.error(request.json())
    except Exception as e:
        logging.error("Error in getting member ID: ", e)
        
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
            logging.error("Getting resource availability failed with the following status code: {}".format(request.status_code()))
            logging.error(request.json())
    except Exception as e:
            logging.error("Error: ", e)

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
            print("Successfully created booking: {}\n".format(request.json()))
        elif request.status_code == 422:
            logging.error("Booking request failed")
            logging.error(request.json())
    except Exception as e:
            logging.error("Error: ", e)
    return request.json()

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
            print("Successfully ended booking early: {}\n".format(request.json()))
        elif request.status_code == 422:
            logging.error("Ending booking early failed\n")
    except Exception as e:
            logging.error("Error: ", e)
    return updated_booking

def delete_booking(booking_id, access_token):
    try:
        request = urequests.delete("https://members.motionlab.berlin/api/bookings/"
                                + booking_id + "/?access_token="
                                + access_token)
        if request.status_code == 204:
            print("Successfully deleted booking within 5 minutes of creation\n")
        elif request.status_code == 409:
            logging.error("Cannot delete bookings made by an event through this endpoint\n")
    except Exception as e:
            logging.error("Error: ", e)
            
##### LOCAL FUNCTIONS #####

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
    
    full_oauth_token = Tokens(
        client_id,
        client_secret,
        "checkin_tokens,read_bookings,write_bookings",
        admin_email,
        admin_password
    )
    
    token_file = open('token.txt', 'w')
    token_file.write(full_oauth_token.access_token)
    token_file.close()
    
    return full_oauth_token.access_token