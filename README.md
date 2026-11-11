# AZkernel

Skill do [Claude Code](https://claude.com/claude-code) para analisar, portar, compilar, depurar e empacotar **kernels e ROMs modificadas para Android**.

Nasceu do porte do LineageOS 14.1 (Android 7.1.2) para o Galaxy Tab 3 7.0 SM-T210, feito a partir do port de um aparelho irmão (SM-T110). O método, os bugs encontrados e os scripts foram generalizados para servir a qualquer aparelho.

## O que ela faz

- Levanta o hardware, as partições, a cmdline do bootloader e as bases disponíveis, e ajuda a escolher a estratégia (kernel só, adaptar a ROM de um irmão, build completo ou GSI).
- Guia o ambiente de build (WSL, chroot da versão certa, toolchain).
- Porta arquivos de placa e drivers, configura e compila o kernel e testa em degraus.
- Monta system.img e ramdisk mantendo os rótulos SELinux, corrige fstab, init e ueventd.
- Depura com uma tabela de sintomas tirados de casos reais (tela preta, panics, IRQ errada, loopback desligado, áudio, câmera, Bluetooth, teclas...).
- Gera um zip de TWRP que confere modelo, partições e hashes antes de gravar e relê tudo depois.
- Sempre pergunta antes de gravar partições, exige backup conferido e nunca ajuda a burlar FRP, bloqueios ou IMEI.

## Instalação

```
git clone https://github.com/shivanayron-lab/azkernel ~/.claude/skills/azkernel
```
No Windows: `git clone https://github.com/shivanayron-lab/azkernel %USERPROFILE%\.claude\skills\azkernel`

Depois, no Claude Code, peça algo como "quero portar uma ROM para o meu tablet" ou use `/azkernel`.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `SKILL.md` | Princípios e fluxo de trabalho |
| `references/01-analise.md` … `07-depuracao.md` | Uma referência por etapa |
| `references/06-sintomas.md` | Sintoma → causa → correção |
| `references/caso-t210.md` | O porte completo do SM-T210 como exemplo |
| `scripts/recon.sh` | Levantamento do aparelho por adb, somente leitura |
| `scripts/bootimg.py` | info / unpack / repack de boot.img (cabeçalho v0 a v2) |
| `scripts/sysimg.sh`, `scripts/labelchk.py` | Edição de system.img mantendo rótulos SELinux |
| `scripts/mkzip.py`, `scripts/update-binary.tmpl` | Zip de TWRP genérico a partir de um config.json |
| `scripts/flash_verify.sh` | Backup, gravação e conferência de uma partição |

## Aviso

Gravar partições pode inutilizar o aparelho. Use por sua conta e risco, sempre com backup.

## Licença

MIT. Veja [LICENSE](LICENSE).
