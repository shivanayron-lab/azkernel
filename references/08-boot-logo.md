# 8. Animação e logo de boot

O boot mostra duas imagens diferentes, que se trocam de formas diferentes:

| O quê | Quando aparece | Onde mora | Risco de trocar |
|---|---|---|---|
| **Logo fixo** | Logo ao ligar, antes do Android | Partição do bootloader ("logo", "aml_logo", "param", "splash", "up_param"...) | Alto: partição de boot. Só com backup conferido |
| **Animação de boot** | Depois do kernel, até a tela inicial | `bootanimation.zip` em `/system/media` (ou `/product/media`, `/oem/media`) | Baixo: é um arquivo |

## 8.1 Animação de boot sem root (Android 4.x)

No AOSP antigo, o `/system/bin/bootanimation` procura **primeiro** `/data/local/bootanimation.zip` e só depois o `/system/media/bootanimation.zip`. A pasta `/data/local` (ou `/data/local/tmp`) é gravável pelo usuário `shell` do adb, então dá para trocar a animação **sem root e sem mexer no sistema**:

```
adb -s <serial> push bootanimation.zip /data/local/bootanimation.zip
adb -s <serial> reboot
# voltar ao original:
adb -s <serial> shell rm /data/local/bootanimation.zip
```

Confirmado num tablet com Android 4.0.4 (Amlogic). Versões mais novas do AOSP removeram esse caminho: confira com `strings /system/bin/bootanimation | grep -i zip` antes de prometer. Sem ele, é preciso root ou ROM e gravar no `/system/media`, mantendo o rótulo SELinux (`sysimg.sh`).

Formato do `bootanimation.zip`:
- **Sem compressão** (`zip -0r`, ou `ZIP_STORED` no Python). Comprimido, a animação não aparece e o sistema mostra a padrão.
- `desc.txt` na raiz: `<largura> <altura> <fps>` e uma linha por parte: `p <repetições> <pausa> <pasta>` (`p 1 0 part0` toca a entrada uma vez; `p 0 0 part1` repete até o sistema abrir).
- Pastas `part0/`, `part1/`... com quadros PNG ou JPG numerados (`00000.png`...), todos do tamanho do `desc.txt`.
- Use a resolução **na orientação em que o aparelho liga** (tablet que liga em pé: 600x1024, não 1024x600). Pegue de `wm size` ou do `desc.txt` original.
- Guarde o original (`adb pull /system/media/bootanimation.zip`) antes.

Para capturar a tela durante o boot, salve o `screencap` em `/data/local/tmp`: o `/sdcard` ainda não está montado.

## 8.2 Logo fixo (partição do bootloader)

Varia por fabricante. Passos gerais:
1. Ache a partição: `/proc/partitions`, `by-name`, `/proc/inand` (Amlogic antigo) e a cmdline (`logo=...`).
2. **Copie a partição inteira** com `dd`, traga para o PC e confira o hash. Se houver duas cópias (Amlogic: `logo` e `aml_logo`, idênticas), copie as duas.
3. Descubra o formato abrindo a cópia. No Amlogic meson3 era um **BMP 24 bits** de 1024x600 (linhas de baixo para cima), com o conteúdo **girado 90°** porque o painel é retrato e liga em pé, seguido de zeros até completar a partição (5 MiB). Reaproveite o cabeçalho original (54 bytes) e mantenha o tamanho exato.
4. Gere a imagem nova com o mesmo tamanho total, grave com `scripts/flash_verify.sh` (relê e compara o hash) e grave as duas cópias.

Precisa de root. Samsung guarda o logo em `param`/`up_param` (tar com JPGs), e Qualcomm costuma usar a partição `splash`. Em todos os casos vale a mesma regra: backup conferido primeiro e o mesmo tamanho e formato do original.

## 8.3 Root temporário em Android 4.0/4.1 antigo (aparelho da pessoa)

Alguns aparelhos 4.0/4.1 sem root aceitam um truque antigo, público desde 2012, que dá **adb como root** até ser desfeito. O `init` muda o dono de `/data/local/tmp` no boot e segue um link simbólico. Com isso, `/data` passa a ser do `shell`, e um `/data/local.prop` com `ro.kernel.qemu=1` faz o Android achar que é um emulador, então o adbd sobe como root.

Só no aparelho da própria pessoa, para algo concreto (ex.: backup e troca do logo, remover apps do sistema), e **desfazendo na mesma sessão**:
```
# tablet NA TOMADA. Preparar:
mv /data/local/tmp /data/local/tmp.bak; ln -s /data /data/local/tmp; reboot
echo ro.kernel.qemu=1 > /data/local.prop; reboot        # adb shell id -> uid=0
# ... trabalho como root ...
# Desfazer SEMPRE:
rm /data/local.prop; rm /data/local/tmp; mv /data/local/tmp.bak /data/local/tmp
chown system.system /data; chmod 0771 /data
chown shell.shell /data/local; chmod 0751 /data/local
chown shell.shell /data/local/tmp; chmod 0771 /data/local/tmp; reboot
```
O que assusta: com `qemu=1` **a interface não abre** (tela preta, gasta bateria, o PC pode mostrar "dispositivo USB desconhecido" por um tempo). Não é brick. Espere o adb voltar e desfaça; em último caso, um wipe de dados pelo recovery desfaz tudo. Se o sistema já foi corrigido (Android 4.2+ na maioria), o truque simplesmente não funciona: não insista e não procure outro exploit (ver Princípios no SKILL.md).
