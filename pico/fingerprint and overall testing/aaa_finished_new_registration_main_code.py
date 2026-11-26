import time
import board
import busio
import adafruit_fingerprint


# ============================================================
# CONFIGURATION
# ============================================================

UART_BAUDRATE = 57600

MIN_ID = 1
MAX_ID = 127


# ============================================================
# FINGERPRINT SENSOR
# ============================================================

uart = busio.UART(
    board.GP0,
    board.GP1,
    baudrate=UART_BAUDRATE
)

try:
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

    print()
    print("==============================")
    print(" AS608 FINGERPRINT MANAGER")
    print("==============================")
    print("Sensor connected")
    print()

except RuntimeError:
    print("Fingerprint sensor not found.")
    print("Check:")
    print("TX -> GP1")
    print("RX -> GP0")
    print("VCC -> 3V3")
    print("GND -> GND")
    raise


# ============================================================
# SHOW SENSOR INFORMATION
# ============================================================

def sensor_info():

    print()
    print("------------------------------")
    print(" SENSOR INFORMATION")
    print("------------------------------")

    print("Status:", finger.verify_password())

    print("Capacity:", finger.capacity)

    print("Security level:", finger.security_level)

    print("Device address:", finger.device_address)

    print("Packet length:", finger.packet_len)

    print("Baud rate:", finger.baudrate)

    print("------------------------------")


# ============================================================
# GET STORED IDS
# ============================================================

def get_ids():

    if finger.read_templates() != adafruit_fingerprint.OK:

        print("Could not read fingerprint templates.")

        return []

    return finger.templates


# ============================================================
# SHOW ALL IDS
# ============================================================

def show_ids():

    print()
    print("==============================")
    print(" REGISTERED FINGERPRINTS")
    print("==============================")

    ids = get_ids()

    if not ids:

        print("No fingerprints registered.")

        return

    print()
    print("Total fingerprints:", len(ids))
    print()

    for fingerprint_id in ids:

        print(
            "ID:",
            fingerprint_id
        )

    print()
    print("------------------------------")


# ============================================================
# FIND NEXT AVAILABLE ID
# ============================================================

def find_available_id():

    ids = get_ids()

    for fingerprint_id in range(
        MIN_ID,
        MAX_ID + 1
    ):

        if fingerprint_id not in ids:

            return fingerprint_id

    return None


# ============================================================
# INPUT ID
# ============================================================

def get_id():

    while True:

        try:

            fingerprint_id = int(
                input(
                    "Enter fingerprint ID (1-127): "
                )
            )

            if MIN_ID <= fingerprint_id <= MAX_ID:

                return fingerprint_id

            print("ID must be between 1 and 127.")

        except ValueError:

            print("Enter a valid number.")


# ============================================================
# WAIT FOR FINGER
# ============================================================

def wait_for_finger():

    print("Place finger on sensor...")

    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.OK:

            return True

        if result == adafruit_fingerprint.NOFINGER:

            continue

        print(
            "Fingerprint sensor error:",
            result
        )

        return False


# ============================================================
# WAIT FOR FINGER REMOVAL
# ============================================================

def wait_for_finger_removal():

    print("Remove finger...")

    while True:

        result = finger.get_image()

        if result == adafruit_fingerprint.NOFINGER:

            print("Finger removed.")

            return True

        time.sleep(0.1)


# ============================================================
# ENROLL FINGERPRINT
# ============================================================

def enroll_fingerprint(fingerprint_id):

    print()
    print("==============================")
    print(" ENROLL FINGERPRINT")
    print("==============================")

    print("ID:", fingerprint_id)

    # Check whether ID already exists

    ids = get_ids()

    if fingerprint_id in ids:

        print()
        print(
            "ID",
            fingerprint_id,
            "is already registered."
        )

        print(
            "Delete it first if you want to replace it."
        )

        return False


    # --------------------------------------------------------
    # FIRST SCAN
    # --------------------------------------------------------

    print()
    print("Scan 1 of 2")

    if not wait_for_finger():

        return False

    if finger.image_2_tz(1) != adafruit_fingerprint.OK:

        print("Could not process first scan.")

        return False

    print("First scan successful.")

    wait_for_finger_removal()

    time.sleep(0.5)


    # --------------------------------------------------------
    # SECOND SCAN
    # --------------------------------------------------------

    print()
    print("Scan 2 of 2")

    if not wait_for_finger():

        return False

    if finger.image_2_tz(2) != adafruit_fingerprint.OK:

        print("Could not process second scan.")

        return False


    print("Second scan successful.")


    # --------------------------------------------------------
    # CREATE MODEL
    # --------------------------------------------------------

    print()
    print("Creating fingerprint model...")

    if finger.create_model() != adafruit_fingerprint.OK:

        print()
        print("ERROR:")
        print("The two scans did not match.")

        return False


    # --------------------------------------------------------
    # STORE MODEL
    # --------------------------------------------------------

    print(
        "Saving fingerprint to ID",
        fingerprint_id
    )

    if finger.store_model(
        fingerprint_id
    ) != adafruit_fingerprint.OK:

        print("Could not store fingerprint.")

        return False


    print()
    print("==============================")
    print(" ENROLLMENT SUCCESSFUL")
    print("==============================")
    print(
        "Fingerprint ID:",
        fingerprint_id
    )
    print("==============================")

    return True


# ============================================================
# DELETE FINGERPRINT
# ============================================================

def delete_fingerprint(fingerprint_id):

    print()
    print("==============================")
    print(" DELETE FINGERPRINT")
    print("==============================")

    ids = get_ids()

    if fingerprint_id not in ids:

        print(
            "ID",
            fingerprint_id,
            "does not exist."
        )

        return False


    confirm = input(
        "Delete ID "
        + str(fingerprint_id)
        + "? (yes/no): "
    ).strip().lower()


    if confirm != "yes":

        print("Delete cancelled.")

        return False


    if finger.delete_model(
        fingerprint_id
    ) == adafruit_fingerprint.OK:

        print()
        print(
            "Fingerprint ID",
            fingerprint_id,
            "deleted."
        )

        return True

    else:

        print(
            "Could not delete ID",
            fingerprint_id
        )

        return False


# ============================================================
# VERIFY FINGERPRINT
# ============================================================

def verify_fingerprint():

    print()
    print("==============================")
    print(" VERIFY FINGERPRINT")
    print("==============================")

    if not wait_for_finger():

        return


    if finger.image_2_tz(
        1
    ) != adafruit_fingerprint.OK:

        print("Could not process fingerprint.")

        return


    if finger.finger_fast_search(
    ) != adafruit_fingerprint.OK:

        print()
        print("NO MATCH FOUND")

        return


    print()
    print("==============================")
    print(" MATCH FOUND")
    print("==============================")

    print(
        "Fingerprint ID:",
        finger.finger_id
    )

    print(
        "Confidence:",
        finger.confidence
    )

    print("==============================")


# ============================================================
# ENROLL AUTOMATIC ID
# ============================================================

def enroll_automatic():

    fingerprint_id = find_available_id()

    if fingerprint_id is None:

        print()
        print("Fingerprint database is full.")

        return


    print()
    print(
        "Next available ID:",
        fingerprint_id
    )

    confirm = input(
        "Use ID "
        + str(fingerprint_id)
        + "? (yes/no): "
    ).strip().lower()


    if confirm == "yes":

        enroll_fingerprint(
            fingerprint_id
        )

    else:

        print("Enrollment cancelled.")


# ============================================================
# REPLACE FINGERPRINT
# ============================================================

def replace_fingerprint():

    print()
    print("==============================")
    print(" REPLACE FINGERPRINT")
    print("==============================")

    fingerprint_id = get_id()

    ids = get_ids()

    if fingerprint_id not in ids:

        print(
            "ID",
            fingerprint_id,
            "does not exist."
        )

        return


    print()
    print(
        "Current fingerprint ID:",
        fingerprint_id
    )

    confirm = input(
        "Replace this fingerprint? (yes/no): "
    ).strip().lower()


    if confirm != "yes":

        print("Cancelled.")

        return


    # Delete old fingerprint

    if finger.delete_model(
        fingerprint_id
    ) != adafruit_fingerprint.OK:

        print("Could not delete old fingerprint.")

        return


    print("Old fingerprint deleted.")

    time.sleep(0.5)


    # Enroll new fingerprint

    enroll_fingerprint(
        fingerprint_id
    )


# ============================================================
# DATABASE SUMMARY
# ============================================================

def database_summary():

    ids = get_ids()

    print()
    print("==============================")
    print(" DATABASE SUMMARY")
    print("==============================")

    print(
        "Used:",
        len(ids)
    )

    print(
        "Free:",
        127 - len(ids)
    )

    print(
        "Capacity:",
        finger.capacity
    )

    if ids:

        print()
        print(
            "First ID:",
            min(ids)
        )

        print(
            "Last ID:",
            max(ids)
        )

    print("==============================")


# ============================================================
# MENU
# ============================================================

def menu():

    while True:

        print()
        print()
        print("================================")
        print("      AS608 FINGERPRINT")
        print("          MANAGEMENT")
        print("================================")

        print()
        print("1. Show all IDs")
        print("2. Register new fingerprint")
        print("3. Register using automatic ID")
        print("4. Delete fingerprint")
        print("5. Replace fingerprint")
        print("6. Verify fingerprint")
        print("7. Database summary")
        print("8. Sensor information")
        print("9. Refresh")
        print("0. Exit")

        print()

        choice = input(
            "Select option: "
        ).strip()


        # ----------------------------------------------------
        # SHOW IDS
        # ----------------------------------------------------

        if choice == "1":

            show_ids()


        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        elif choice == "2":

            fingerprint_id = get_id()

            enroll_fingerprint(
                fingerprint_id
            )


        # ----------------------------------------------------
        # AUTOMATIC REGISTER
        # ----------------------------------------------------

        elif choice == "3":

            enroll_automatic()


        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        elif choice == "4":

            fingerprint_id = get_id()

            delete_fingerprint(
                fingerprint_id
            )


        # ----------------------------------------------------
        # REPLACE
        # ----------------------------------------------------

        elif choice == "5":

            replace_fingerprint()


        # ----------------------------------------------------
        # VERIFY
        # ----------------------------------------------------

        elif choice == "6":

            verify_fingerprint()


        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        elif choice == "7":

            database_summary()


        # ----------------------------------------------------
        # SENSOR INFO
        # ----------------------------------------------------

        elif choice == "8":

            sensor_info()


        # ----------------------------------------------------
        # REFRESH
        # ----------------------------------------------------

        elif choice == "9":

            print("Refreshing...")

            time.sleep(0.5)


        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        elif choice == "0":

            print()
            print("Exiting fingerprint manager.")

            break


        else:

            print()
            print("Invalid option.")


# ============================================================
# START
# ============================================================

menu()
