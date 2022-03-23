# Add group and permissions for fusing UUID
cp 99-efuse.rules /etc/udev/rules.d/

sudo udevadm control --reload-rules
udevad trigger /dev/efuse
