import sys
import time

import hid

TARGET_VID = None
TARGET_PID = None
USAGE_PAGE = 0xFF01


KNOWN_BOOTLOADERS = [
    (0x1A81, 0x2237),  # Holtek / Xiaomi Lite
    (0x04D9, 0x8010),  # Standard Holtek ISP
    (0x1A81, 0x2238),  # Alternative Holtek
]


def find_secret_channel():
    global TARGET_VID, TARGET_PID
    for dev in hid.enumerate():
        if dev.get("usage_page") == 0xFF01 and dev.get("vendor_id") == 0x2717:
            TARGET_VID = dev.get("vendor_id")
            TARGET_PID = dev.get("product_id")
            return dev.get("path")
    return None


def get_all_interfaces():
    if TARGET_VID and TARGET_PID:
        return hid.enumerate(TARGET_VID, TARGET_PID)
    return []


def menu():
    menu_text = (
        "\nXiaomi Gaming Mouse Lite > Toolkit\n"
        "[1] Echo Loopback {CMD 7}\n"
        "[2] Bootloader Mode {CMD 17}\n"
        "[3] Factory Test {CMD 87}\n"
        "[4] Version Check {CMD 160}\n"
        "[5] DPI Sniffer\n"
        "[0] Exit\n"
        "> "
    )
    return input(menu_text)


def echo_loopback():
    print("\nEcho Loopback")
    print("> 2-5 - Factory reset")
    print("> 256 To go back")
    while True:
        user_val = input("0-255 > ")
        try:
            val = int(user_val)
            if val == 256:
                break
            if not (0 <= val <= 255):
                raise ValueError
        except ValueError:
            print("[!] Error: Invalid input value. Enter 0-255 or 256 to exit.")
            continue

        path = find_secret_channel()
        if not path:
            print("[!] Error: Secret channel 0xff01 not found.")
            continue

        h = hid.device()
        try:
            h.open_path(path)
            h.set_nonblocking(True)

            packet = [0x04, 7, val] + [0x00] * 61
            h.write(packet)
            time.sleep(0.05)

            resp = h.read(64)
            if resp:
                print(f"Response > {list(resp[:16])}")
                print(f"Result > {resp[1]}")
            else:
                print("Response > None")
                print("Result > Timeout")
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            h.close()


def enable_bootloader():
    path = find_secret_channel()
    if not path:
        print("\n[!] Error: Secret channel 0xff01 not found.")
        return

    h = hid.device()
    try:
        h.open_path(path)
        h.set_nonblocking(True)
        packet = [0x04, 17] + [0x00] * 62
        h.write(packet)
        print("\n[+] Bootloader Mode Enabled")
        print("> To disable - reconnect the mouse")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        h.close()


def factory_test():
    path = find_secret_channel()
    if not path:
        print("\n[!] Error: Secret channel 0xff01 not found.")
        return

    h = hid.device()
    try:
        h.open_path(path)
        h.set_nonblocking(True)
        packet = [0x04, 87, 1] + [0x00] * 61
        h.write(packet)
        print("\n[+] Factory Test Enabled")
        print("> FN To change color")
        print("> DPI To change DPI")
        print("> Wheel does nothing")
        print("> To disable - reconnect the mouse")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        h.close()


def version_check():
    path = find_secret_channel()
    if not path:
        print("\n[!] Error: Secret channel 0xff01 not found.")
        return

    h = hid.device()
    try:
        h.open_path(path)
        h.set_nonblocking(True)

        packet = [0x04, 160] + [0x00] * 62
        h.write(packet)
        time.sleep(0.05)

        resp = h.read(64)
        if resp:
            print("\nVersion Check")
            print(f"Response > {list(resp[:16])}")
            print(f"Decoded > Firmware Version v{resp[1]}")
        else:
            print("\n[!] Error: No response from mouse.")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        h.close()


def sniff_mode():
    print("\nSniffing...")
    print("> Change DPI to see packets")
    print("> Press Ctrl+C to go back")

    devices = get_all_interfaces()
    if not devices:
        for vid, pid in KNOWN_BOOTLOADERS:
            boot_devs = hid.enumerate(vid, pid)
            if boot_devs:
                devices = [boot_devs[0]]
                break

    handles = []
    last_data = {}

    for dev in devices:
        try:
            h = hid.device()
            h.open_path(dev["path"])
            h.set_nonblocking(True)
            handles.append((h, dev["interface_number"]))
            last_data[h] = None
        except:
            pass

    try:
        while True:
            for h, iface in handles:
                try:
                    data = h.read(64)
                    if data:
                        if data != last_data.get(h):
                            print(f"[{iface}] > {list(data[:16])}")
                            last_data[h] = data
                except:
                    pass
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[+] Sniffing stopped")
    finally:
        for h, _ in handles:
            h.close()


def main():
    find_secret_channel()

    try:
        while True:
            choice = menu()
            if choice == "1":
                echo_loopback()
            elif choice == "2":
                enable_bootloader()
            elif choice == "3":
                factory_test()
            elif choice == "4":
                version_check()
            elif choice == "5":
                sniff_mode()
            elif choice == "0":
                print("[*] Exiting...")
                sys.exit(0)
            else:
                print("[!] Error: Invalid selection")

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
