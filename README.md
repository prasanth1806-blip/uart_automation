# UART Automation Tool 

This project automates hardware testing via UART.

#Setup & Run
You don't need to manually install Python libraries. The included script handles everything.

### Step 1: Permissions (Linux Only)
If you are using real hardware, your user needs permission to access Serial ports. Run this and **restart your PC**:
```bash
sudo usermod -a -G dialout $USER
