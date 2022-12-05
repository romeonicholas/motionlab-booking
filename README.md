# MotionLab On-Site Booking Companion
> Currently under development

## About
The MotionLab On-Site Booking Companion is a Raspberry Pi Pico W-based solution custom built for creating and updating resource bookings at hardtech coworking space [MotionLab Berlin](https://motionlab.berlin "MotionLab Berlin"). MotionLab uses Cobot to manage their members and resources, which provides a web portal for users for scheduling purposes. That works well for advance notice bookings, but could be more convenient for spur-of-the-moment bookings. MotionLab wanted their members to be able to swipe their member badge at any available machine and get straight to work, so I created a prototype to meet that vision.

## Features
- Create bookings
  - If the resource associated with the Booking Companion is available, swiping a MotionLab badge will create a 30 minute booking for that member at that resource starting immediately.
- Update bookings 
  - If the user has already booked a resource online, swiping their MotionLab badge at the associated Booking Companion after the start time of their booking will update the start time of the reservation online to match when the user swiped (with a five minute grace period)
  - If the user created a booking on-site with the Booking Companion, or has already checked in to the booking they made online, swiping their MotionLab badge will either delete the booking (if done immediately after creation, to undo a mistaken booking) or update the end time of the booking to match when the user swiped.
- First boot configuration
  - On first boot, the Booking Companion will ask for the necessary information to generate a narrowly-scoped OAuth token to accomplish its booking tasks. This means admin credentials, the Cobot client_id, and Cobot client_secret are never stored locally and cannot be discovered even if someone were to steal the Booking Companion.

## Hardware Requirements
- Raspberry Pi Pico W
-  RC522 RFID reader
- 5v power over USB-Micro

## Credits
Developed by Nicholas Romeo, with thanks to the following developers whose modules I used:
- [micropython-mfrc522](https://github.com/danjperron/micropython-mfrc522 "MFRC522")
- [micropython-logging](https://github.com/erikdelange/MicroPython-Logging "micropython-logging")
