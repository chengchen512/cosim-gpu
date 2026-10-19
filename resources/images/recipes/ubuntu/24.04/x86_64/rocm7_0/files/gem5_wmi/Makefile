# SPDX-License-Identifier: BSD-3-Clause

obj-m += gem5_wmi.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD)

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
