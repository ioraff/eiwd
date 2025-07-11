/*
 *
 *  Wireless daemon for Linux
 *
 *  Copyright (C) 2019  Intel Corporation. All rights reserved.
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

enum blacklist_reason {
	/*
	 * When a BSS is blacklisted using this reason IWD will refuse to
	 * connect to it via autoconnect
	 */
	BLACKLIST_REASON_CONNECT_FAILED,
	/*
	 * This type of blacklist is added when an AP indicates that its unable
	 * to handle more connections. This is done via BSS-TM requests or
	 * denied authentications/associations with certain status codes.
	 *
	 * Once this type of blacklist is applied to a BSS IWD will attempt to
	 * avoid roaming to it for a configured period of time.
	 */
	BLACKLIST_REASON_AP_BUSY,
};

void blacklist_add_bss(const uint8_t *addr, enum blacklist_reason reason);
bool blacklist_contains_bss(const uint8_t *addr, enum blacklist_reason reason);
void blacklist_remove_bss(const uint8_t *addr, enum blacklist_reason reason);
