/*
 *
 *  Wireless daemon for Linux
 *
 *  Copyright (C) 2023  Cruise, LLC. All rights reserved.
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

struct pmksa {
	uint64_t expiration;
	uint8_t spa[6];
	uint8_t aa[6];
	uint8_t ssid[32];
	size_t ssid_len;
	uint32_t akm;
	uint8_t pmkid[16];
	uint8_t pmk[64];
	size_t pmk_len;
};

typedef void (*pmksa_cache_add_func_t)(const struct pmksa *pmksa);
typedef void (*pmksa_cache_remove_func_t)(const struct pmksa *pmksa);
typedef void (*pmksa_cache_flush_func_t)(void);

struct pmksa **__pmksa_cache_get_all(uint32_t *out_n_entries);

struct pmksa *pmksa_cache_get(const uint8_t spa[static 6],
				const uint8_t aa[static 6],
				const uint8_t *ssid, size_t ssid_len,
				uint32_t akm);
int pmksa_cache_put(struct pmksa *pmksa);
int pmksa_cache_expire(uint64_t cutoff);
int pmksa_cache_flush(void);
int pmksa_cache_free(struct pmksa *pmksa);

uint64_t pmksa_lifetime(void);
void __pmksa_set_config(const struct l_settings *config);

void __pmksa_set_driver_callbacks(pmksa_cache_add_func_t add,
					pmksa_cache_remove_func_t remove,
					pmksa_cache_flush_func_t flush);
