# 3. Kernel: portar, configurar, compilar

## 3.1 Escolha da fonte

- **Fonte do fabricante para o seu modelo** é a referência de hardware: arquivos de placa (`arch/arm/mach-*/board-*.c`) ou device tree (`arch/*/boot/dts/...`), drivers dos chips do seu aparelho, defconfig (`arch/*/configs/*_defconfig`).
- **Kernel do port do irmão** (quando existe) é a referência de **compatibilidade com a ROM nova**: patches de binder, SELinux, drivers da GPU que casam com os blobs, correções de Android novo.
- Estratégia que funcionou: partir do kernel do irmão (já roda a ROM) e **trazer do fabricante** os arquivos de placa e os drivers do seu aparelho, um por um. Registre cada troca num commit.

## 3.2 Configuração

1. Pegue a defconfig real do aparelho: `/proc/config.gz` do stock ou a defconfig da fonte do fabricante.
2. Compare com a defconfig do irmão (`scripts/diffconfig` ou `diff` de `make savedefconfig`). Monte a sua a partir da do irmão **trocando máquina/placa, PMIC e drivers** pelos do seu aparelho e mantendo o que o Android novo precisa (binder, ashmem, SELinux, cgroups, `ANDROID_*`).
3. Opções que existem no Kconfig do fabricante mas não no kernel base indicam drivers que você terá de portar (Kconfig + Makefile + pasta do driver).
4. Guarde a config gerada num script (ex.: `mkcfg.sh`) para refazer do zero.

## 3.3 O que costuma mudar entre aparelhos irmãos

- **Máquina/placa:** `MACH_*` e arquivo de placa, ou DTB diferente. Se a placa nova não compila no kernel base, falta campo de struct ou função: traga o header do fabricante ou adapte o mínimo.
- **PMIC e reguladores:** nomes de LDO/BUCK, tensões, ordem de ligar. Reguladores sem consumidor registrado são **desligados pelo `regulator_init_complete`** uns 30 s depois do boot. Isso pode apagar a tela ou o touch se o driver usa um caminho que "pula" a inicialização porque o bootloader já ligou (ex.: `skip_power_on`). Garanta que o driver pegue (`regulator_get` + `enable`) os reguladores também nesse caminho.
- **Tela:** painel, ponte (DSI→LVDS/RGB), clocks. Use o nome de clock que o kernel base conhece. Não religue nem reprograme o que o bootloader já configurou se o driver não sabe fazer igual (no T210, ligar um pós-divisor quebrava o DSI configurado pelo SBL).
- **Touch:** controlador e **firmware embutido**. Driver de outro aparelho pode gravar o firmware de touch errado no seu controlador. Traga driver e header de firmware do seu modelo.
- **Wi-Fi/BT:** chip e firmware (`/system/etc/firmware/...`, `/vendor/firmware`). Módulo `.ko` precisa ter o `vermagic` do kernel novo.
- **Áudio:** codec e rotas. Às vezes muda só o amplificador (class-D) e o resto do codec é igual.
- **Câmeras e sensores:** sensores I2C, barramento, endereço e GPIO de interrupção, orientação (`position`).
- **IRQs de GPIO:** confira se a base de IRQ dos GPIOs que a placa usa (macro tipo `GPIO_TO_IRQ`) é a mesma que o driver de GPIO aloca. No T210 a placa contava com 128 e o kernel alocava 160 dinamicamente. Resultado: IRQ errada, probe falhando e um BUG de timer bem longe da causa.

## 3.4 Bootloader: limites invisíveis

- Leia `/proc/cmdline` do stock. Exemplos que importam: `initrd=<end>,<tamanho>` (o T210 passava 1 MiB e cortava um ramdisk maior → panic. Correção: aceitar override do tamanho no kernel, como fazia o kernel Samsung), `mem=`, reservas (`reserve_gpu`, `ioncarv`), `board_id`, `androidboot.*`.
- `CONFIG_CMDLINE` / `CMDLINE_EXTEND` / `CMDLINE_FORCE`: decida conscientemente se o kernel usa, completa ou ignora a cmdline do bootloader.
- Endereços de carga e tamanho de página: copie do cabeçalho do boot.img original (`scripts/bootimg.py info`).
- **Tamanho da partição de kernel/boot:** a imagem final não pode passar disso. Compare com o que o port do irmão gera (o T110 gerava 16 MiB e a partição do T210 tem 12 MiB).
- Samsung: o bootloader pode avisar ou bloquear sem o trailer `SEANDROIDENFORCE`. Mantenha-o se o original tinha.

## 3.5 Compilar

```
make O=out ARCH=arm CROSS_COMPILE=<prefixo> <sua>_defconfig
make O=out ARCH=arm CROSS_COMPILE=<prefixo> -j$(nproc) zImage modules
# arm64: Image.gz(-dtb); DT: make dtbs
```
- Confira hash e data de `out/arch/*/boot/zImage` a cada build.
- Módulos: copie os `.ko` necessários para `/system/lib/modules` (ou `/vendor/lib/modules`) e confira o `vermagic` (`strings x.ko | grep vermagic`).
- Kernel de depuração: uma variante com `SECURITY_SELINUX` permissivo forçado, `DEBUG_OBJECTS_TIMERS`, `DEBUG_ATOMIC_SLEEP`, `PANIC_TIMEOUT`, `DYNAMIC_DEBUG`, debugfs. Gere com um script separado para nunca ir para a release.

## 3.6 Primeiro boot do kernel novo

Teste em degraus, **um de cada vez**:
1. Kernel novo + **ramdisk do stock** (sistema stock). Só prova que o kernel inicia o hardware básico.
2. Imagem de teste com adb aberto e sem autenticação (`ro.adb.secure=0`, `ro.secure=0`, `setenforce 0`, `dmesg_restrict 0`) para ver o `dmesg` ao vivo. **Só para testes.**
3. Kernel novo + ramdisk da ROM nova.

Em cada panic, leia o log anterior (`/proc/last_kmsg`, `/sys/fs/pstore/console-ramoops*`) pelo recovery logo depois. Veja `07-depuracao.md`. Cada panic costuma apontar um driver: corrija, faça novo build e teste de novo.

## 3.7 Overclock e desempenho

- Prefira ajustar o governor (`interactive`/`schedutil`: `hispeed_freq`, `go_hispeed_load`, `target_loads`, `min_sample_time`) num `on property:sys.boot_completed=1` do init. É seguro e reversível.
- Frequência acima da de fábrica exige tabela de tensão e de clocks coerente. Se a opção de overclock muda o clock de outro bloco (tela, memória) ou usa uma tensão menor que a de fábrica, **recuse** e explique o motivo. No T210, `CONFIG_CORE_1248` trocava o PLL da tela e nunca foi usado pela Samsung.
