# 1. Análise do aparelho e escolha da base

## 1.1 Levantamento pelo adb

Rode `scripts/recon.sh <serial> relatorio.txt`. Sem root ele já pega quase tudo. Com root (`su`) ou no TWRP ele pega também a tabela de partições completa e os blocos. Confira principalmente:

- **Identidade:** `ro.product.model`, `ro.product.device`, `ro.product.board`, `ro.hardware`, `ro.board.platform`, versão do bootloader (`ro.boot.bootloader` ou `ro.bootloader`), Android e patch.
- **SoC e CPU:** `/proc/cpuinfo` (Hardware, núcleos, arquitetura arm/arm64), frequências em `/sys/devices/system/cpu/cpu0/cpufreq/`, governor.
- **Kernel atual:** `uname -a` (`/proc/version`), `/proc/cmdline` (o que o bootloader passa, como tamanho do initrd, board_id e reservas de memória), `/proc/config.gz` se existir (defconfig real!).
- **Partições:** `/proc/partitions` + `ls -l /dev/block/platform/*/by-name` (ou `/dev/block/by-name`). Anote número **e tamanho** de cada uma. Atenção: pode haver mais de uma pasta em `platform/*` (ex.: dois controladores sdhci); use o nó real (`mmcblkXpN`).
- **Esquema moderno?** `ro.boot.slot_suffix` (A/B), `ro.boot.dynamic_partitions` (super.img), `ro.boot.vbmeta.*` (AVB), `ro.treble.enabled` (Treble → GSI possível), header do boot (v3/v4 → vendor_boot, GKI).
- **Hardware:** `/sys/bus/i2c/devices/*/name` (touch, sensores, PMIC, câmera, codec), `/proc/bus/input/devices` (touch, teclas, sensores), `lsmod` e `/system/lib/modules`, `/vendor/firmware` ou `/system/etc/firmware` (Wi-Fi/BT), `dmesg` dos primeiros segundos (nomes de drivers e painel de tela), `/proc/asound/cards` e mixer (codec de áudio).
- **SELinux:** `getenforce`. **Root:** `su -c id`. Cuidado com `su` falso: confira versão e origem do binário (no T210 o APK SuperSU era um stub).

## 1.2 Firmware original

Baixe o firmware stock da mesma região/versão do bootloader. Ele dá: kernel e ramdisk originais, blobs (HALs, firmware), fstab, init*.rc, `build.prop`, e muitas vezes a defconfig. Formatos comuns:

- Samsung: `.tar.md5` com `boot.img`, `system.img` (sparse → `simg2img`), às vezes `.lz4` (`lz4 -d`).
- Fastboot (Xiaomi, Motorola, Pixel...): `.img` sparse ou `super.img` (`lpunpack`), `payload.bin` (`payload-dumper-go`).
- MediaTek: scatter + imagens soltas.

Se não houver firmware, faça backup pelo TWRP ou `dd` (com root) das partições boot, recovery e system e trabalhe a partir dele.

## 1.3 Procurar bases

Pesquise (XDA, GitHub, GitLab, postmarketOS wiki) por:

1. ROM/kernel já existente para o **modelo exato**. Desconfie de tópicos que são só pedido ("LineageOS for X?" sem download).
2. **Aparelho irmão**: mesmo SoC, mesma família, outra variante (Wi-Fi/3G/LTE, 7"/8"/10", outra região). Ex.: SM-T110 (goyawifi) e SM-T210 (lt02wifi) têm o mesmo PXA986.
3. **Fonte de kernel do fabricante**: Samsung opensource.samsung.com (ou os espelhos no GitHub, como Samsung-OSS-Kernels), Motorola/Sony/LG/Xiaomi no GitHub oficial, Qualcomm CodeLinaro/CAF, MediaTek (só fonte do fabricante do aparelho).
4. Projetos mainline/pmOS do SoC.

Compare o irmão com o seu aparelho peça por peça: partições, painel de tela, touch, Wi-Fi/BT, PMIC, codec, câmeras, sensores, teclas. **O que difere é o seu trabalho.** Faça uma tabela "igual / diferente / desconhecido".

## 1.4 Escolher a estratégia

| Situação | Estratégia | Esforço |
|---|---|---|
| Quer só um recurso no kernel (overclock seguro, driver, módulo) | Kernel da fonte do fabricante + ramdisk original | baixo |
| Aparelho Treble (Android 8+) | GSI + kernel/vendor stock (ou ajustes no vendor) | baixo a médio |
| Irmão já tem ROM pronta e reproduzível | Adaptar a ROM pronta: kernel do seu aparelho + imagem do irmão ajustada (o caminho do T210) | médio |
| ROM do irmão depende de arquivos privados do autor | Mesmo caminho: partir do **release** dele (system.img) em vez de recompilar | médio |
| Nada pronto, mas fonte de kernel e device tree de irmão existem | Build completo de fontes (repo sync + device tree) | alto |
| Sem fonte de kernel em lugar nenhum | Só ROM baseada no kernel stock (mesma versão de Android do kernel) ou desistir | — |

Regra prática: a versão de Android depende muito do kernel. Android 7 roda com kernel 3.4 com patches. Android 9+ costuma exigir 3.18/4.4 ou mais, e recursos como binder novo, namespaces de montagem e eBPF.

## 1.5 O que registrar antes de seguir

- Serial adb de cada modo (ROM, recovery, debug).
- Tabela de partições com tamanhos.
- cmdline e cabeçalho do boot.img original (endereços, página, tamanho máximo).
- Lista de diferenças com o irmão.
- Onde estão os backups e os hashes deles.
