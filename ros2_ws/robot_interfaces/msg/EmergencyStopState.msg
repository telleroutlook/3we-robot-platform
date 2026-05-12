# Emergency stop state topic
std_msgs/Header header
bool stopped                    # Whether E-stop is currently active
uint8 state                     # 0=normal, 1=estopped, 2=recovery_pending, 3=relay_fault
string reason                   # Human-readable reason for last E-stop

uint8 STATE_NORMAL=0
uint8 STATE_ESTOPPED=1
uint8 STATE_RECOVERY=2
uint8 STATE_RELAY_FAULT=3
