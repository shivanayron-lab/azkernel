# 5. Empacotar, instalar e lançar

## 5.1 Backup antes do primeiro flash

Com TWRP ou root, copie por `dd` as partições únicas do aparelho. Os nomes variam: EFS, efs, modemst1/2, fsg, nvdata, nvram, persist, PARAM, sec_efs, MRD, protect_f/s. Copie também boot/KERNEL e recovery. Gere um `MD5SUMS.txt`, traga para o PC e confira. Sistema e dados: backup do TWRP ou `tar` de /data se a pessoa quiser voltar.

Muitos recoveries não têm `md5sum`: use `busybox md5sum`/`sha256sum`.

## 5.2 Gravar uma partição com conferência

`scripts/flash_verify.sh <serial> <bloco> <imagem>`: faz backup do conteúdo atual, envia, grava com `dd`, relê só os bytes da imagem e compara o hash. Use para kernel, recovery e testes rápidos.

Atalho para testes de kernel sem precisar entrar no recovery toda vez: com um kernel de depuração (adb root), grave a partição de kernel direto do Android pelo mesmo script e reinicie.

## 5.3 Zip de TWRP

`scripts/mkzip.py config.json` gera um zip que:
- recusa modelos errados e avisa nos parecidos (ex.: variante com modem);
- confere se cada partição está no nó **e tem o tamanho** esperados, antes de gravar qualquer coisa (é a trava de verdade);
- confere o sha256 de cada imagem dentro do zip (download corrompido);
- grava, relê e compara o hash. Se a conferência do sistema falhar, grava de novo uma vez;
- deixa recovery e dados intocados e lembra o Wipe > Data quando a pessoa vem de outra ROM.

Exemplo de `config.json`:
```json
{
  "rom_name": "LineageOS 14.1 (Android 7.1.2)",
  "device_title": "Galaxy Tab 3 7.0 Wi-Fi (SM-T210)",
  "release": "t210-r2",
  "zip_name": "lineage-14.1-{date}-{release}-SM-T210.zip",
  "accept_hint": "SM-T210",
  "refuse": [{"match": "*SM-T11*|*goya*", "msg": "Este zip e do SM-T210. Para o SM-T110 use a ROM goyawifi"}],
  "warn":   [{"match": "*SM-T211*|*lt023g*", "msg": "modelo com modem, nao testado"}],
  "partitions": [
    {"name": "SYSTEM", "by_name": "SYSTEM", "dev": "/dev/block/mmcblk0p14", "size": 1507852288,
     "image": "/caminho/system.ext4", "entry": "system.ext4.gz", "gzip": true},
    {"name": "KERNEL", "by_name": "KERNEL", "dev": "/dev/block/mmcblk0p9", "size": 12582912,
     "image": "/caminho/kernel.img", "entry": "kernel-partition.img", "gzip": false}
  ],
  "after_notes": ["Vindo de outra ROM: faca Wipe > Data antes de reiniciar."],
  "readme": "/caminho/README.md",
  "out_dir": "/caminho/release"
}
```
Teste o zip com `twrp install /sdcard/<zip>` pelo adb, ou pela tela do TWRP, e depois boote.

## 5.4 Release

- Nome com data e número (`r1`, `r2`...). A cada correção, uma release nova. Não sobrescreva a anterior até a nova ser testada; depois, apague a antiga para ninguém postar a errada.
- Publique o sha256 junto com o zip, e um README com: o que funciona, o que não funciona, como instalar, como voltar ao stock e o histórico de mudanças.
- Registre na memória do projeto: sha256, md5 do kernel, o que mudou e onde está o arquivo.
