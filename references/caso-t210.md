# Caso de estudo: LineageOS 14.1 no Galaxy Tab 3 7.0 SM-T210

Resultado: ROM t210-r2 instalável pelo TWRP, com tela, toque, Wi-Fi, BT, áudio (alto-falante, fone e mic), duas câmeras, acelerômetro, tecla Home e apps que usam 127.0.0.1 (AZtube) funcionando. Pendentes: GPS e bússola BMM050.

## Ponto de partida

- Aparelho: SM-T210 (lt02wifi), Marvell PXA986, GPU GC1000, 1 GB RAM, 2 núcleos até 1205 MHz. Stock 4.4.2 (bootloader T210XXBPJ2).
- Não existia LineageOS acima do 4.4 para o T210.
- Irmão: SM-T110 (goyawifi), mesmo SoC, com port LineageOS 14.1 do jakaco (github.com/jakaco/lineageos-14.1-goyawifi). O instalador dele recusava o T210, e com razão: as partições são outras.
- Fonte Samsung T210: android_kernel_samsung_pxa986, branch sm-t210_eur_kk_opensource, defconfig `pxa986_lt02_defconfig`.

## Diferenças T110 → T210 (o que deu trabalho)

| Peça | T110 | T210 |
|---|---|---|
| Placa/PMIC | MACH_GOYA, 88PM822 | MACH_LT02, 88PM800 + 88PM805 (codec) |
| Partições | system p15, data p16, efs p4 | system p14 (1507852288 B), data p17, cache p15, efs p6, kernel p9 de 12 MiB |
| Tela | outra | CPT_LTL070NL01 por ponte tc35876x/VX5B3D |
| Touch | bt532 (firmware T110) | Zinitix bt532 com firmware do T210 |
| Wi-Fi/BT | SD8777 | SD8787 (sem BLE) |
| Câmeras | — | SR352 (traseira), SR130PC10 (frontal) |
| Sensores | — | BMC150 (bma2x2 + bmm050), gp2a |
| Home | keycode 102 | KEY_HOMEPAGE 172 |

## Ambiente

WSL Ubuntu, `.wslconfig` com 12 GB e 16 GB de swap, chroot xenial (OpenJDK 8, gcc 5.4, python 2.7, repo) com `inchroot.sh`, toolchain GCC 4.7 do AOSP 4.4.4. O build do kernel fora do chroot dava "make: not found" e o zImage ficava igual.

## Estratégia

O `assemble.py` do port do irmão dependia de uma pasta privada do autor (HALs, webview, ramdisk modelo) → não dava para reproduzir pelas fontes. Solução: partir do **release r7** dele (system.ext4 + ramdisk) e adaptar:
- kernel 3.4.113 do port + arquivos de placa e drivers da Samsung T210;
- system.ext4 com resize para a partição do T210, módulos novos, firmware do SD8787, HALs corrigidos e build.prop;
- ramdisk com fstab e init remapeados (p15→p14, p16→p17, p4→p6) e nome lt02wifi.

## Linha do tempo dos bugs (na ordem em que apareceram)

1. **Panic no initramfs**: o SBL passa `initrd=...,1m`. → override do tamanho do initrd (5 MiB, como no kernel Samsung) + `CONFIG_CMDLINE=""`.
2. **Panic no touch**: o driver bt532 do T110 chamava `pdata->tsp_power` NULL e traria o firmware de touch errado. → driver e firmware do T210.
3. **Panic na câmera frontal** (power do sr130pc10): hook de mclk no i2c-pxa. → ajustado.
4. **Panic no fb**: um `#ifndef LT02` deixava o fb0 sem memória. → corrigido.
5. **/data não montava, adb unauthorized**: fstab do stock KK com o kernel novo. → fstab certo na ROM.
6. **BUG em timer.c**: o `sec_battery_probe` falhava por IRQ errada e liberava memória com work pendente. Achado com `DEBUG_OBJECTS_TIMERS`. Raiz: a base de IRQ dos GPIOs era 160 no kernel e 128 na placa. → base fixa em 160 para LT02, `cancel_delayed_work_sync` no erro, IRQ do gp2a certa.
7. **Tela preta no 1º boot da ROM**: `regulator_init_complete` desligava LDO14/16/17 da ponte, porque o caminho `skip_pw_on` nunca pegava os reguladores; e o fb tinha só 2 buffers. → `late_initcall` pega os reguladores, 3 buffers, tabela de brilho da Samsung.
8. **Ainda sem imagem**: o clock "LCDCLK" não existe no kernel base (a câmera desligava o clock compartilhado), e o ramo genérico do `lcd_func_clk_init` ligava o pós-divisor e quebrava o DSI do SBL. → `"mmp_disp"` e o ramo GOYA (só reparent do pll1_624, igual Samsung). Depurado lendo registradores com um binário estático e comparando com o TWRP (kernel Samsung).
9. **Sem som**: as rotas usavam o class-D do PM822. → registradores do class-D do PM800 (0x48=0xE0, 0x4A=0xD0, 0x4B=0x07).
10. **Câmera traseira**: o sr352 do port nunca fazia probe; o HAL só abria video0; o driver recusava 24 fps (-EINVAL → "capture error -22"). → driver Samsung, video0 para o sr352, 24 fps aceito; depois, HAL novo compilado com NDK r13b com duas câmeras.
11. **Bluetooth**: o HAL abortava em asserts de BLE (o SD8787 não tem LE). → asserts viraram NOP; calibração `cal_cfg` no insmod como no stock.
12. **Sensores**: as regras de permissão apontavam para `input4` (no T210 é o de proximidade). → curinga `input*` no ueventd.
13. **Home**: `key 172 HOME` no `gpio-keys.kl`.
14. **Mic do fone mudo**: no T210 o mic do fone entra por AMIC1 (reg 0x11 MICPGA1_IN_SEL=0), e não pela entrada "externa". Achado gravando enquanto alternava as entradas pelo debugfs do codec.
15. **Serviço sem ler o arquivo em enforcing**: `sed -i` dentro do system.ext4 criou inode sem rótulo. → rotular depois de cada edição + `labelchk.py`.
16. **AZtube não tocava vídeo**: o init do port não fazia `ifup lo`, então o loopback ficava DOWN e o proxy TLS local falhava ("Cannot assign requested address"). → `on boot` com `ifup lo` no init.framework.rc. Saiu na release r2.

## Decisões com a pessoa

- YouTube: NewPipe como app de sistema (sem GApps; o app oficial pedia Android 8+).
- Overclock `CONFIG_CORE_1248` recusado (trocava o PLL da tela e reduzia a tensão). Em vez disso, um ajuste seguro do governor interactive no `boot_completed`.
- Backup das partições únicas (EFS, NVM, MRD, PARAM, MEP, KERNEL, RECOVERY) com MD5SUMS antes do primeiro flash.

## Scripts originais (base dos genéricos desta skill)

`mkrom.sh` (system + ramdisk), `mkromk.py` (boot.img de 12 MiB, variante debug), `labelchk.py`, `twrp/mkzip.py` + `update-binary` (confere modelo, partições, tamanhos e sha256; grava e relê).
