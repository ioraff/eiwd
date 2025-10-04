/*
 *
 *  Wireless daemon for Linux
 *
 *  Copyright (C) 2025  Locus Robotics Corporation. All rights reserved.
 *
 *  This library is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Lesser General Public
 *  License as published by the Free Software Foundation; either
 *  version 2.1 of the License, or (at your option) any later version.
 *
 *  This library is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  Lesser General Public License for more details.
 *
 *  You should have received a copy of the GNU Lesser General Public
 *  License along with this library; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */

#ifndef __IWD_VENDOR_QUIRKS_H
#define __IWD_VENDOR_QUIRKS_H


#include <stdint.h>

struct vendor_quirk {
	bool ignore_bss_tm_candidates : 1;
	bool replay_counter_mismatch : 1;
};

void vendor_quirks_append_for_oui(const uint8_t *oui,
					struct vendor_quirk *quirks);

const char *vendor_quirks_to_string(struct vendor_quirk quirks);

#endif /* __IWD_VENDOR_QUIRKS_H */
