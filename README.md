# Xiaomi Gaming Mouse Lite

## Specifications  
Chip: Holtek HT32F5XXXX  
Flash: 32 KB `0x00000000 - 0x00007FFF`  
SRAM: 4 KB `0x20000000 - 0x20000FFF`  
Boot ROM: 4 KB `0x1FF00000`  
Sensor: PixArt PAW3327

## Toolkit  
Download: https://github.com/thebadinteger/xiaomi-gaming-mouse-lite/blob/main/toolkit.py
Setup: `pip install hidapi`  
Start: `python toolkit.py`  
(Requires hidapi package and root privileges on Linux)  

#### Echo Loopback  
Sends command 7 (`0x07, val`) via interface 2 (`MI_02`)  
If `val = 2, 3, 4, 5` - the mouse resets the DPI, backlight settings and restarts.  
For any other values of `val` - the mouse returns the sent value in the second byte of the response.  

#### Bootloader Mode  
Sends command 17 (`0x11`) via interface 2 (`MI_02`)  
Upon receiving command 17, the Holtek chip initiates a software switch to the bootloader.  
The mouse is disconnected as a device and reconnected with its factory identifiers.  
In this mode, the backlight stops flashing, the buttons and sensor are disabled, and the device waits for firmware commands.  
[Recommended Software for Bootloader Mode](https://github.com/hansemro/ht32-dfu-tool)  

#### Factory Test  
Sends command 87 (`0x57, 1`) via interface 2 (`MI_02`)  
The mouse enters Factory Test mode. Parameter 1 instructs the processor to run a function subtest.  
The firmware takes control of the ARGB LEDs, applies maximum current to all three channels (Red + Green + Blue = White light), and temporarily disables the transmission of scroll wheel interrupts via USB.  
In this mode, the FN button cycles through static colors (red, blue, green, yellow), and the DPI button cycles through the sensor’s internal settings. To exit this mode, simply reconnect the mouse.  

#### Version Check  
Sends command 160 (`0xA0`) via interface 2 (`MI_02`)  
The mouse returns a packet with the following approximate structure: `[160, 22, 1, 0, 0...]`.  
`160` - command echo.  
`22` - possibly the firmware version.  
`1` - possibly indicates that the mouse is currently operating in Active Profile 1.  

#### DPI Sniffer  
The sniffer operates passively via non-blocking calls `h.read(64)`.  
When you physically press the DPI button, the chip reconfigures the sensor and sends a notification packet in the following format to the USB port via the `MI_02 (0xff01)` channel: `[4, Level, Value, 0, 0...]`.  
The sniffer intercepts the incoming packet (Input Report) and instantly displays it.  

## Shenanigans  
_Hereinafter, "we" refers to Gemini and me_  
Standard and [custom](https://github.com/JUGGERNAUT13/XIAOMI_MI_GAMING_MOUSE_APP) software for the older Xiaomi Gaming Mouse (PID `5009`) failed to recognize the Lite model (PID `5031`). We enumerated the USB   interfaces and found that the mouse registers a custom vendor-specific interface `MI_02` with Usage Page `0xFF01`. This is a standard debug page for Holtek microcontrollers, serving as our primary entry point.  

To find active commands on `MI_02`, we wrote a custom Python fuzzer. Commands 7, 17, 87, 160 were found.  

**Official** specifications claimed the mouse utilized an `NXP LPC11U35` processor. However, during fuzzing, CMD `17` caused the mouse to reconnect with a new USB ID: `VID 1A81` / `PID 2237` (MG670U Bootloader).  
`0x1A81` is officially registered to **Holtek Semiconductor, Inc.**, proving that the greedy Chinese are at it again, and the hardware had been silently redesigned to use a `Holtek HT32FXXX` (ARM Cortex-M0+) chip with its factory ROM bootloader.  

We compiled [ht32-dfu-tool](https://github.com/hansemro/ht32-dfu-tool) (Unofficial Holtek HT32 ISP DFU Tool in Rust) to dump the firmware. However, on startup, the tool detected `Flash security: true` (hardware readout protection) and panicked, refusing to read.  
We modified the Rust source code (`src/main.rs`), commenting out the safety assertions, and forced raw read requests on `0x00000000` (Main Flash) and `0x20000000` (SRAM). The MCU responded with dummy packets, demonstrating that the hardware-level Flash Memory Controller (FMC) blocks memory reads in secure mode by replacing data with structured zeros.  
I think the only way around this is through physical modification and voltage manipulation.  

After we changed the driver to `WinUSB`, we fuzzed the bootloader's verification command (`CMD 1, SUB 0`). While direct reading was blocked by the hardware, we attempted a "Direct Comparison Oracle" attack (brute-forcing 1 byte at a time and reading the hardware verify response). However, we discovered that the bootloader requires aligned 52-byte chunks and blocks all verification commands when `Flash Security` is active, preventing side-channel leaks.  

#### Conclusion  
- The Xiaomi Gaming Mouse Lite (YXSB01YM) has no over-USB color configuration handlers compiled into its AP firmware. 
- The ROM bootloader is completely secured against USB readout attacks, making the original firmware safe from extraction. 
- Custom color is exclusively handled by local hardware interrupts (FN button combos). This can only be fixed by rewriting the firmware from scratch and mass-erasing the factory one.

### Materials Used
- https://github.com/hansemro/ht32-dfu-tool
- https://www.holtek.com/webapi/116745/an0602en.pdf
- https://mcu.holtek.com.tw/ht32/resource/HT32_M0p_V20260408.zip
- https://mcu.holtek.com.tw/ht32/app.fw/IAP_HID/HT32_APPFW_5xxxx_IAP_HID_V1.22.1_9417.zip
