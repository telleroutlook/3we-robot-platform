# Payload connection and power state
std_msgs/Header header
string payload_id               # EEPROM-read identifier
string name                     # Human-readable name from EEPROM
bool connected                  # Physical connection detected
bool power_5v_active            # 5V rail enabled
bool power_12v_active           # 12V rail enabled
bool power_vbat_active          # VBAT rail enabled
float32 current_5v              # Current draw on 5V rail (A)
float32 current_12v             # Current draw on 12V rail (A)
float32 power_consumption_watts # Total power consumption (W)
uint8 status                    # 0=idle, 1=active, 2=error, 3=updating

uint8 STATUS_IDLE=0
uint8 STATUS_ACTIVE=1
uint8 STATUS_ERROR=2
uint8 STATUS_UPDATING=3
