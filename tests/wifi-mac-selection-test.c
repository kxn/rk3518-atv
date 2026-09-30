// SPDX-License-Identifier: Apache-2.0
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <errno.h>
#define CONFIG_USE_CUSTOMER_MAC
#define ETH_ALEN 6
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
struct mm_get_mac_addr_cfm { uint8_t mac_addr[6]; };
static unsigned long system_serial_high,system_serial_low;
static uint8_t factory[6],otp[6];static int factory_rc,otp_rc,otp_calls;
static int rwnx_get_custom_mac_addr(uint8_t* p){memcpy(p,factory,6);return factory_rc;}
static int rwnx_send_get_macaddr_req(void* h,struct mm_get_mac_addr_cfm* p){(void)h;otp_calls++;memcpy(p->mac_addr,otp,6);return otp_rc;}
static int is_valid_ether_addr(const uint8_t* p){static const uint8_t zero[6]={0};return !(p[0]&1)&&memcmp(p,zero,6);}
static int select_mac(uint8_t* result){
 int ret;uint8_t mac_addr_efuse[6]={0};uint8_t dflt_mac[6]={0x88,0,0x33,0x77,0x10,0x99};
 struct {uint8_t mac_addr[6];} init_conf;void* rwnx_hw=0;
#ifdef CONFIG_USE_CUSTOMER_MAC
    ret = rwnx_get_custom_mac_addr(mac_addr_efuse);
    if (ret || !is_valid_ether_addr(mac_addr_efuse)) {
        /* Some boards leave vendor storage blank but program the AIC OTP. */
        memset(mac_addr_efuse, 0, ETH_ALEN);
        ret = rwnx_send_get_macaddr_req(rwnx_hw,
                    (struct mm_get_mac_addr_cfm *)mac_addr_efuse);
        if (ret)
            memset(mac_addr_efuse, 0, ETH_ALEN);
    }
#else
    ret = rwnx_send_get_macaddr_req(rwnx_hw,
                (struct mm_get_mac_addr_cfm *)mac_addr_efuse);
    if (ret)
        memset(mac_addr_efuse, 0, ETH_ALEN);
#endif
    if (is_valid_ether_addr(mac_addr_efuse)) {
        memcpy(init_conf.mac_addr, mac_addr_efuse, ETH_ALEN);
    } else {
        /* Only require a SoC identity when both factory sources are blank.
         * A valid factory address must not depend on the fallback source. */
        if (!(system_serial_high | system_serial_low)) {
            pr_err("aic8800: no factory MAC or stable SoC identity\n");
            ret = -ENODATA;
            goto err_lmac_reqs;
        }
        dflt_mac[0] = 0x02;
        dflt_mac[1] = (system_serial_high >> 8) & 0xff;
        dflt_mac[2] = system_serial_high & 0xff;
        dflt_mac[3] = (system_serial_low >> 16) & 0xff;
        dflt_mac[4] = (system_serial_low >> 8) & 0xff;
        dflt_mac[5] = system_serial_low & 0xff;
        memcpy(init_conf.mac_addr, dflt_mac, ETH_ALEN);
        pr_info("aic8800: blank factory MAC, using stable SoC MAC %pM\n",
                init_conf.mac_addr);
    }
    pr_info("aic8800: selected Wi-Fi MAC %pM\n", init_conf.mac_addr);

 memcpy(result,init_conf.mac_addr,6);return 0;
err_lmac_reqs:return ret;
}
int main(){
 uint8_t out[6],again[6];system_serial_high=system_serial_low=0;
 uint8_t good[6]={0x10,2,3,4,5,6};memcpy(factory,good,6);assert(select_mac(out)==0&&!memcmp(out,good,6)&&otp_calls==0);
 memset(factory,0,6);memcpy(otp,good,6);assert(select_mac(out)==0&&!memcmp(out,good,6)&&otp_calls==1);
 memset(otp,0,6);assert(select_mac(out)==-ENODATA);
 system_serial_high=0x7c3a;system_serial_low=0xd130bc;assert(select_mac(out)==0);uint8_t expected[6]={2,0x7c,0x3a,0xd1,0x30,0xbc};assert(!memcmp(out,expected,6));assert(select_mac(again)==0&&!memcmp(out,again,6));
 memset(factory,255,6);otp_rc=-EIO;assert(select_mac(out)==0&&!memcmp(out,expected,6));
 memcpy(factory,good,6);assert(select_mac(out)==0&&!memcmp(out,good,6));
 puts("PASS: factory without SoC ID, OTP fallback, absent identity error, deterministic fallback, invalid factory/OTP, factory precedence");
}
