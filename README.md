# MotionLab On-Site Booking Companion
> Currently under development

## About
The MotionLab On-Site Booking Companion is an IoT solution custom-built for creating and updating resource bookings at hardtech coworking space [MotionLab Berlin](https://motionlab.berlin "MotionLab Berlin"). MotionLab uses [Cobot](https://www.cobot.me) to manage their members and resources, which provides a web portal for users for scheduling purposes, but provides no physical on-site support for or access to bookings. MotionLab wanted their members to be able to walk up to an available resource like a 3D printer or meeting room, swipe their member badge, and get straight to work; so I created a prototype to meet that vision. The device uses a RFID reader to identify users and manage bookings on a per-resource configurable basis, making it incredibly flexible while still easy to deploy and maintain. The Booking Companion is also cheap, made up of less than €15 of easily sourced microprocessors (the Raspberry Pi Pico W) and components. And because this device would be deployed in a business environment, special care has been taken to keep PII and sensitive data/credentials off the device in the case that a bad actor accessed or stole the device. 

## Features
- Create bookings
  - If the resource associated with the Booking Companion is available, swiping a MotionLab badge will create a booking for that member at that resource starting immediately using a configurable default duration. 
- Update bookings 
  - If the user has already booked a resource online ahead of time, swiping their MotionLab badge at the associated Booking Companion after the start time of their booking will update the start time of the reservation online to match when the user swiped (with a configurable grace period).
  - If the user created a booking on-site with the Booking Companion, or has already checked in to the booking they made online, swiping their MotionLab badge will either delete the booking (if done immediately after creation, to undo a mistaken booking) or update the end time of the booking to match when the user swiped.
- First boot configuration
  - On first boot, the Booking Companion will ask for the necessary information to generate a narrowly-scoped OAuth token to accomplish its booking tasks. This means admin credentials, the Cobot client_id, and Cobot client_secret are never stored locally and cannot be discovered even if someone were to steal the Booking Companion.

## Hardware Requirements
- Raspberry Pi Pico W
- RC522 RFID reader
- 5v power over USB-Micro

## Credits
Developed by Nicholas Romeo, with thanks for additional code from:
- [micropython-mfrc522](https://github.com/danjperron/micropython-mfrc522 "MFRC522")
- [micropython-logging](https://github.com/erikdelange/MicroPython-Logging "micropython-logging")
- [dhylands](https://forum.micropython.org/viewtopic.php?t=8112#p68368)
