/*
 *
 *  Wireless daemon for Linux
 *
 *  Copyright (C) 2023  Cruise LLC. All rights reserved.
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

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <ell/ell.h>

#include "src/module.h"
#include "src/util.h"
#include "src/pmksa.h"

static bool verbose = false;
static struct l_settings *config;
extern struct iwd_module_desc __start___iwd_module[];
extern struct iwd_module_desc __stop___iwd_module[];
/* There's a single module compiled in, so it will be the pmksa one */
static struct iwd_module_desc *pmksa = __start___iwd_module;

static void print_cache()
{
	uint32_t used;
	struct pmksa **entries = __pmksa_cache_get_all(&used);
	uint32_t i;

	for (i = 0; i < used; i++) {
		struct pmksa *pmksa = entries[i];

		fprintf(stderr, "%02u aa "MAC" spa "MAC" expiration: %"
				PRIu64"\n", i,
				MAC_STR(pmksa->aa), MAC_STR(pmksa->spa),
				pmksa->expiration);
	}
}

static struct pmksa *make_pmksa()
{
	static uint32_t counter = 0xabcdef00;
	struct pmksa *pmksa = l_new(struct pmksa, 1);

	memcpy(pmksa->aa, &counter, sizeof(counter));
	counter += 1;
	memcpy(pmksa->spa, &counter, sizeof(counter));
	counter += 1;

	pmksa->ssid_len = 6;
	pmksa->ssid[0] = 'F';
	pmksa->ssid[1] = 'o';
	pmksa->ssid[2] = 'o';
	pmksa->ssid[3] = 'b';
	pmksa->ssid[4] = 'a';
	pmksa->ssid[5] = 'r';

	pmksa->akm = 0x4;

	return pmksa;
}

static void test_pmksa(const void *data)
{
	struct pmksa *p;
	struct pmksa **entries;
	uint32_t used;

	config = l_settings_new();
	l_settings_set_uint(config, "PMKSA", "Capacity", 7);
	__pmksa_set_config(config);
	pmksa->init();

	p = make_pmksa();
	p->expiration = 20;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 15;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 32;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 48;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 102;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 55;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 41;
	assert(!pmksa_cache_put(p));

	p = make_pmksa();
	p->expiration = 66;
	assert(!pmksa_cache_put(p));

	if (verbose)
		print_cache();

	entries = __pmksa_cache_get_all(&used);
	assert(used == 7);
	assert(entries[0]->expiration == 20);

	/* Reverse spa and aa */
	p = pmksa_cache_get(entries[0]->aa, entries[0]->spa,
				entries[0]->ssid, entries[0]->ssid_len,
				0xff);
	assert(!p);

	p = pmksa_cache_get(entries[0]->spa, entries[0]->aa,
				entries[0]->ssid, entries[0]->ssid_len,
				0xff);
	assert(p);
	l_free(p);

	entries = __pmksa_cache_get_all(&used);
	assert(used == 6);
	assert(entries[0]->expiration == 32);

	assert(pmksa_cache_expire(48) == 3);
	entries = __pmksa_cache_get_all(&used);
	assert(used == 3);
	assert(entries[0]->expiration == 55);

	pmksa->exit();
	l_settings_free(config);
}

int main(int argc, char *argv[])
{
	l_test_init(&argc, &argv);

	l_test_add("PMKSA/basics", test_pmksa, NULL);

	return l_test_run();
}
