# 4. ROM: imagem de sistema e ramdisk

## 4.1 Script único de montagem

Escreva **um script** (modelo: `mkrom.sh` do caso T210) que, a partir de entradas fixas (release do irmão ou build, kernel compilado, pasta `overlay/` com arquivos do seu aparelho), refaz system.img e ramdisk do zero. Cada correção entra no script, e cada release sai dele. Nunca corrija só "na mão" dentro do aparelho sem levar a correção para o script.

## 4.2 system.img

1. Converta se for sparse: `simg2img system.img system.ext4`. Se for `super.img`: `lpunpack`.
2. Ajuste o tamanho à **sua** partição:
   ```
   e2fsck -fy system.ext4
   resize2fs system.ext4 <blocos>            # tamanho_da_partição / tamanho_do_bloco (normalmente 4096)
   truncate -s <tamanho_da_partição> system.ext4
   ```
   Se o conteúdo não cabe, remova apps antes (não o sistema base).
3. Monte em loop e edite usando `scripts/sysimg.sh` (`put` mantém inode e rótulo; `add` cria arquivo e copia o rótulo de um vizinho).
4. O que costuma entrar:
   - **Módulos do kernel novo** (`lib/modules/*.ko`, vermagic conferido).
   - **Firmware** do Wi-Fi/BT/touch do seu aparelho (tirado do stock).
   - **HALs** que dependem do hardware: áudio (rotas/mixer), câmera, sensores, luzes, Bluetooth. Se o HAL do irmão quase serve, corrija o mínimo (ex.: transformar asserts de BLE em NOP para um chip sem LE). Se não serve, recompile a partir da fonte com o NDK.
   - **Configurações:** `audio_policy`, `mixer_paths`/rotas, `media_profiles.xml` (câmeras e resoluções), `keylayout/*.kl` (teclas que o seu kernel manda), `init.*.sh` de Wi-Fi/BT (parâmetros do módulo, calibração).
   - **build.prop:** `ro.product.model`, `ro.product.device`, `ro.build.product` (e `ro.product.name` se for preciso) do seu aparelho. O `default.prop` do ramdisk **sobrepõe** o build.prop, então ajuste os dois.
   - Remova o que não funciona com o seu kernel e só trava (ex.: MtpDocumentsProvider sem appfuse num kernel 3.4).
   - Apps de sistema extras: pasta em `app/<Nome>/` com `.apk` + `lib/<abi>/*.so`, dono 0:0, 755/644, rotulados.
5. Antes de desmontar: `python3 -I scripts/labelchk.py <mount>` precisa dar `unlabeled: 0`.
6. `sync; umount; e2fsck -fn` para conferir.

## 4.3 Rótulos SELinux (o erro mais traiçoeiro)

- Arquivo sem rótulo ou com rótulo errado: em enforcing o serviço não lê, e o log mostra `avc: denied`. Em permissive "funciona", e o problema passa despercebido.
- `sed -i`, `cp`, `mv`, `install` e editores criam inode novo. Rotule depois ou use `cat novo > destino`.
- Rótulo padrão de `/system`: `u:object_r:system_file:s0`. Mas há exceções (`/system/bin/*` específicos, `vendor_file`, `same_process_hal_file`...). Por isso o mais seguro é copiar o rótulo do arquivo vizinho ou consultar `file_contexts` (`plat_file_contexts`) da ROM.
- Teste final **sempre em enforcing** e procure `avc: denied` no `dmesg`/`logcat`.

## 4.4 Ramdisk

Descompacte com `scripts/bootimg.py unpack` e depois `cpio -id < ramdisk.cpio` (descompacte gzip/lz4 antes). Ajustes típicos:

- **fstab** (`fstab.<hardware>`): número das partições system, data, cache, efs e das demais. Use os do **seu** aparelho. Erro aqui → /data não monta, a ROM pede senha ou fica em bootloop.
- **init*.rc:**
  - Garanta `ifup lo` no `on boot`. Sem loopback, apps que servem em 127.0.0.1 (proxies locais, players, alguns apps de vídeo como o AZtube) falham com "Cannot assign requested address".
  - Nós USB (`iProduct`, `iSerial`), propriedades do aparelho.
  - Ajustes de governor e criação de pastas que apps esperam, no `on property:sys.boot_completed=1`.
  - Regras de permissão de sysfs que apontavam para `inputN` fixo: o número muda entre aparelhos. Use curinga.
- **ueventd.rc:** permissões de `/dev/videoN`, `/dev/i2c-*`, nós de sensores (`enable`, `poll_delay`) para o usuário certo.
- **default.prop:** identidade, `ro.secure`/`ro.adb.secure`/`ro.debuggable` (abertos **só** na imagem de depuração).

Reempacote com:
```
cd rd && find . | sort | cpio -o -H newc -R 0:0 --quiet | gzip -9 > ../ramdisk.cpio.gz
```
(mantenha a compressão que o bootloader aceita, normalmente a mesma do original.)

## 4.5 boot.img

```
python3 -I scripts/bootimg.py info boot-stock.img
python3 -I scripts/bootimg.py repack --orig boot-stock.img --kernel zImage --ramdisk ramdisk.cpio.gz \
        --name <device> --pad <tamanho_partição> --out boot.img
```
Mantém endereços, página, cmdline, dt/dtb e o trailer Samsung do original. Para cabeçalho v3/v4 (Android 11+ com vendor_boot), use `magiskboot`.

Faça duas saídas pelo mesmo script: `boot.img` (release) e `boot-debug.img` (adb root sem autenticação + permissivo), com nomes que não se confundam.
