# Payload connection and power state
std_msgs/Header header
string payload_id           # EEPROM-read identifier
bool connected              # Physical connection detected
bool powered                # Power rails active
float32 current_5v          # Current draw on 5V rail (A)
float32 current_12v         # Current draw on 12V rail (A)
uint8 status                # 0=idle, 1=active, 2=error, 3=updating

uint8 STATUS_IDLE=0
uint8 STATUS_ACTIVE=1
uint8 STATUS_ERROR=2
uint8 STATUS_UPDATING=3
