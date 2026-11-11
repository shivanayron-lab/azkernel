# 2. Ambiente de build

## 2.1 Windows: WSL2

- `wsl --install -d Ubuntu --no-launch` (terminal com admin). Precisa **reiniciar o Windows** depois de ativar os recursos. Depois, crie o usuário no Ubuntu.
- `%USERPROFILE%\.wslconfig`: limite memória e dê swap, senão o build mata o Windows. Ex. com 16 GB: `memory=12GB`, `swap=16GB`.
- Build fica **dentro do disco do WSL** (`/mnt/algo` ou `~`), nunca em `/mnt/c` (lento e com problema de maiúsculas, links e permissões). Copie só os resultados para o Windows.
- Para comandos de root: `wsl -d Ubuntu -u root -- bash script.sh`.
- **PowerShell estraga aspas e `$`** em comandos longos passados ao WSL. Escreva o comando num `.sh` e rode o arquivo. Do Git Bash, caminhos como `/mnt/...` viram caminhos do Windows: passe pelo PowerShell ou use `wsl ... bash -c` dentro de um script.

## 2.2 Versão do sistema de build

ROMs antigas exigem ferramentas antigas. Use um **chroot** (debootstrap) ou container com a versão certa:

| Base | Sistema | Java | Observações |
|---|---|---|---|
| Android 4.4 / CM11 | Ubuntu 12.04/14.04 | OpenJDK 6/7 | make 3.81 |
| Android 6–7 / CM13–14.1 | Ubuntu 16.04 (xenial) | OpenJDK 8 | python 2.7 |
| Android 8–9 / Lineage 15–16 | Ubuntu 18.04 | OpenJDK 8 (já vem no prebuilt em 9) | |
| Android 10+ / Lineage 17+ | Ubuntu 20.04/22.04 | prebuilt | ≥ 16 GB RAM, swap |

Chroot xenial, por exemplo:
```
debootstrap --variant=buildd xenial /srv/xenial http://archive.ubuntu.com/ubuntu
# entrar: bind de /proc /sys /dev /dev/pts e da pasta de build, depois chroot + sudo -u <usuario>
```
Faça um script `inchroot.sh` que monta os binds e roda um comando como o usuário normal. **Todo build de kernel e ROM passa por ele.** Fora do chroot o `make` pode não existir ou ser outra versão, e o build "termina" sem gerar zImage novo: confira sempre o hash e a data do resultado.

## 2.3 Toolchain do kernel

- Kernel 3.x ARM 32: GCC 4.6–4.9 (`arm-eabi-` ou `arm-linux-androideabi-` do AOSP prebuilts da mesma época). GCC novo quebra kernel antigo com dezenas de erros e warnings tratados como erro.
- Kernel 3.18/4.x arm64: GCC 4.9 `aarch64-linux-android-` ou Clang do AOSP indicado no `build.config` do fabricante.
- GKI (5.x+): seguir o `build/build.sh` ou o Kleaf do Android Common Kernel com o Clang daquela versão.
- Variáveis: `ARCH`, `SUBARCH`, `CROSS_COMPILE`, `O=<pasta de saída>` (mantém a fonte limpa), `-j<threads>`.

## 2.4 Ferramentas úteis

- Imagens: `simg2img`/`img2simg` (android-sdk-libsparse-utils), `e2fsprogs` (e2fsck, resize2fs, debugfs), `lpunpack`/`lpmake` (super.img), `magiskboot` (boot v3/v4, vendor_boot e compressões exóticas), `extract-dtb`, `dtc`, `mkdtimg`.
- Ramdisk: `cpio` (formato newc), `gzip`/`lz4`/`xz`.
- Python 3 para os scripts desta skill (rodar com `python3 -I`).
- Para binários estáticos de teste no aparelho (ler registradores, por exemplo): `arm-linux-gnueabi-gcc -static` ou o NDK.
- NDK antigo (r13b, por exemplo) dentro do chroot para recompilar HALs pequenos sem montar a árvore inteira.

## 2.5 Espaço e tempo

- Só kernel: 2 a 5 GB, 5 a 20 min.
- Adaptar ROM pronta: 10 a 20 GB.
- Árvore completa: Lineage 14.1 ~70 GB, Lineage 18+ 200 a 300 GB, horas de build na primeira vez. Use `ccache`.
