# 7. Depuração

## 7.1 Logs

- **Panic:** entre no recovery logo depois e leia `/proc/last_kmsg` ou `/sys/fs/pstore/console-ramoops*`. Atenção: alguns recoveries reiniciam uma vez no próprio boot e sobrescrevem o log. Ele só é confiável logo após um panic, então compare o horário.
- **Boot que trava sem panic:** imagem de depuração com adb aberto desde o início (`ro.adb.secure=0`, `ro.secure=0`, `service.adb.root=1`, `setenforce 0` e `dmesg_restrict 0` no `on early-init`). Depois: `adb wait-for-device; adb shell dmesg -w` e `adb logcat`.
- **SELinux:** `dmesg | grep avc` e `logcat | grep avc`. Teste sempre também em enforcing.
- **Crashes nativos:** `/data/tombstones/`, `logcat -b crash`.

## 7.2 Ciclo rápido de teste

Monte um script de ciclo que: grava o kernel de teste (com conferência de hash) → reinicia → espera o adb → captura dmesg/logcat com o nome do teste. Isso transforma cada tentativa em um comando. Um serviço de depuração no ramdisk de teste que grava a partição de kernel a partir de um arquivo enviado (com conferência de md5) evita entrar no recovery a cada teste.

## 7.3 Kernel de depuração

Opções úteis (só na variante de depuração): `DEBUG_OBJECTS` (+ `_TIMERS`, `_WORK`, `_FREE`), `DEBUG_ATOMIC_SLEEP`, `PROVE_LOCKING` (pesado), `DEBUG_KMEMLEAK`, `DYNAMIC_DEBUG`, `DEBUG_FS`, SELinux permissivo forçado. Quando um bug aparece "longe" do driver culpado (timer, lista, slab), essas opções costumam apontar o dono do objeto.

## 7.4 Ler registradores e hardware

- **debugfs** (`/sys/kernel/debug`): clocks (`clk_summary` ou equivalente), reguladores (`regulator/`), GPIO (`gpio`), pinctrl, codec ASoC (`asoc/<card>/<codec>/codec_reg`, com leitura e, em muitos codecs, escrita `reg valor`).
- **Registradores de SoC:** um binário estático pequeno que lê `/dev/mem` (mmap) ajuda a comparar o estado do display, clocks e pinos entre o seu kernel e o **recovery stock** (que roda o kernel do fabricante e serve de "gabarito").
- **I2C:** `i2cdetect`/`i2cget` (busybox ou estático) para ver se o chip responde no endereço esperado.
- **Áudio:** grave enquanto alterna as entradas do codec por script e meça o nível do WAV para achar qual entrada tem sinal.

## 7.5 Método

1. Reproduza e capture o log.
2. Consulte `06-sintomas.md`.
3. Compare com o stock: o mesmo nó, registrador, propriedade ou arquivo no firmware original.
4. Mude **uma** coisa, refaça pelo script e teste.
5. Registre causa e correção (memória do projeto e, se for geral, esta skill).
