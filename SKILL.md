---
name: azkernel
description: Especialista em analisar, portar, compilar, depurar e empacotar kernels e ROMs modificadas (custom ROM, LineageOS, port de ROM de um aparelho irmão, kernel mod, ramdisk, boot.img, system.img, zip de TWRP) para qualquer Android. Use sempre que a pessoa quiser criar ou portar uma ROM, compilar ou modificar um kernel, mexer em boot.img/ramdisk/fstab/init.rc, consertar algo que não funciona numa ROM custom (tela preta, bootloop, kernel panic, Wi-Fi, áudio, câmera, sensores, tecla, app que não toca vídeo), extrair ou reempacotar imagens de firmware, ou montar um zip instalável pelo TWRP, mesmo sem dizer "kernel". Também para "port ROM", "build kernel", "custom kernel", "bootloop after flashing", "unpack boot.img". Para só otimizar, debloat ou instalar uma ROM pronta, prefira a skill android-optimizer.
---

# AZkernel: kernels e ROMs mod para Android

Esta skill guarda o método que deu certo no porte do LineageOS 14.1 para o Galaxy Tab 3 SM-T210, partindo do port de um aparelho irmão (SM-T110). O caso completo está em `references/caso-t210.md` e serve de exemplo real para cada etapa. Responda no idioma da pessoa (pt-BR por padrão) e explique cada termo técnico em uma frase.

## Princípios

- **O aparelho é da pessoa, e o risco é dela.** Explique o efeito antes de gravar qualquer partição, desbloquear o bootloader ou apagar dados, e peça uma confirmação específica para cada passo desse tipo. "Pode fazer tudo" vale para compilar e montar imagens, não para gravar.
- **Backup antes de gravar, conferido por hash.** Antes do primeiro flash, copie as partições únicas do aparelho (EFS/IMEI, NV, modem calibração, PARAM, boot, recovery) e confira md5/sha256 de cada cópia. Sem backup conferido, não grave.
- **Grave sempre com conferência.** Depois de cada `dd`/`fastboot flash`, leia de volta e compare o hash. Use `scripts/flash_verify.sh`.
- **Use `-s <serial>` em todo comando adb/fastboot.** O serial muda entre ROM, recovery e modo debug: confira com `adb devices -l` antes.
- **Só afirme o que verificou.** Diferencie "compilou" de "bootou" de "a função funciona no aparelho". Peça para a pessoa testar o que depende de olho ou ouvido (tela, som, câmera, toque) e registre o resultado.
- **Uma mudança por teste.** Kernel novo e ramdisk novo ao mesmo tempo escondem a causa. Troque uma peça, teste, anote.
- **Não force instaladores que recusam o aparelho.** Se um zip de outro modelo recusa o seu, a recusa costuma estar certa (partições diferentes). Porte de verdade em vez de editar a checagem.
- **Nunca ajude a contornar proteção de aparelho alheio** (FRP, bloqueio de tela, MDM, operadora, IMEI). Mudar IMEI ou número de série de rádio está fora do escopo, sempre.

## Fluxo de trabalho

Siga as fases em ordem. Leia a referência de cada fase quando chegar nela.

1. **Entrevista e objetivo** (sem tocar no aparelho): modelo exato, o que a pessoa quer (Android mais novo, kernel com recurso X, consertar uma ROM existente, só um app funcionar), se aceita perder dados, se tem PC com espaço (build de ROM pede 70 a 300 GB) e quanto tempo topa investir. Diga com franqueza se o caminho é longo.
2. **Análise do aparelho e das bases** → `references/01-analise.md` e `scripts/recon.sh`. Mapeie SoC, partições, bootloader, hardware e root. Procure ROMs/kernels existentes e o **aparelho irmão** mais próximo (mesmo SoC e família). Decida a estratégia: kernel só, adaptar ROM pronta de irmão, ou build completo de fontes.
3. **Ambiente de build** → `references/02-ambiente.md` (WSL/Linux, chroot da versão certa, toolchain, armadilhas).
4. **Kernel** → `references/03-kernel.md`: fonte, defconfig, porte de arquivos de placa/DT e drivers, cmdline do bootloader, compilação e o primeiro boot.
5. **ROM** → `references/04-rom.md`: imagem de sistema (resize, firmware, HALs, build.prop, rótulos SELinux), ramdisk (fstab, init.rc, ueventd), montagem do boot.img com `scripts/bootimg.py`.
6. **Teste e depuração** → `references/07-depuracao.md`, sempre consultando a tabela de sintomas em `references/06-sintomas.md` antes de investigar do zero.
7. **Empacotar e instalar** → `references/05-empacotar-instalar.md` e `scripts/mkzip.py` (zip de TWRP que confere modelo, partições e hashes).
8. **Release e registro**: gere o zip, anote sha256, versão e o que mudou. Mantenha um script único que refaz a ROM do zero (como o `mkrom.sh` do T210), para cada correção virar uma release nova e reproduzível. Grave na memória do projeto os achados novos e, se forem gerais, acrescente-os em `references/06-sintomas.md`.

## Regras que evitaram horas de retrabalho

- Toda edição dentro de um system.img montado precisa manter o rótulo SELinux. `sed -i`, `cp` e `mv` criam inode novo **sem rótulo**, e em modo enforcing o serviço deixa de ler o arquivo. Prefira `cat novo > destino` (mantém o inode) e, ao criar arquivo, rotule copiando o rótulo de um vizinho. Confira com `scripts/labelchk.py` antes de desmontar. Os helpers estão em `scripts/sysimg.sh`.
- O bootloader pode impor limites que a fonte não mostra: tamanho do initrd na cmdline, tamanho da partição de kernel, endereço de carga. Leia `/proc/cmdline` da ROM original e o cabeçalho do boot.img original e reuse os mesmos endereços e tamanho de página.
- Partições de aparelhos irmãos quase nunca batem. Compare número e tamanho de cada partição (`/proc/partitions` e `by-name`) e corrija fstab, init e instalador.
- Compile sempre dentro do ambiente certo (chroot/container). Fora dele o build pode "terminar" sem gerar nada novo. Confira sempre o hash e a data do zImage gerado.
- Guarde o kernel e o boot.img originais conferidos. Eles são a referência de registradores, endereços e comportamento quando algo não funciona.

## Scripts

Todos rodam no Linux/WSL, salvo indicação. Leia o cabeçalho de cada um antes de usar.

| Script | Para quê |
|---|---|
| `scripts/recon.sh <serial> [saída]` | Levanta tudo do aparelho por adb (props, SoC, partições, cmdline, drivers, I2C, input, firmware, SELinux, root) num relatório |
| `scripts/bootimg.py` | `info`, `unpack` e `repack` de boot.img/recovery.img (cabeçalho v0 a v2, mantém dt/dtb/dtbo e assinatura Samsung), troca kernel/ramdisk e recalcula o id |
| `scripts/sysimg.sh` | Funções para preparar, montar e editar system.img mantendo rótulos SELinux (`prep`, `put`, `add`, `label_like`, `finish`) |
| `scripts/labelchk.py <mount>` | Lista arquivos sem rótulo SELinux numa imagem montada |
| `scripts/mkzip.py <config.json>` | Gera zip de TWRP genérico a partir de uma configuração (modelos aceitos e recusados, partições, tamanhos, imagens), usando o modelo `scripts/update-binary.tmpl` |
| `scripts/flash_verify.sh` | Faz backup, grava e confere uma partição pelo adb (recovery ou root) |

## Quando parar e perguntar

- O aparelho não tem fonte de kernel publicada nem irmão com fonte: explique que o caminho vira engenharia reversa e confirme se a pessoa quer seguir.
- O bootloader é travado e não desbloqueia oficialmente: não procure exploit para burlar. Explique os limites.
- Uma etapa exige apagar dados ou gravar bootloader/modem: confirme antes, sempre.
