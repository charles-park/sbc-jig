# If you have registered the label printer as a generic driver in the past, please re-register with the following instructions.

## Get the registered printer
lpstat -v

## Remove the printer
sudo lpadmin -x zebra

## Get the urls of usb
sudo lpinfo -v

## Register printer with the following command after removing the serial number of the string.
sudo lpadmin -p zebra -E -v usb://Zebra%20Technologies/ZTC%20GC420d%20\(EPL\)
