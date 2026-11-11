# 6. Sintoma → causa provável → correção

Consulte esta tabela antes de investigar do zero. Os itens marcados (T210) aconteceram de verdade no caso de estudo.

## Boot

| Sintoma | Causa provável | Onde olhar / correção |
|---|---|---|
| Panic logo no início, "junk in compressed archive" ou initramfs truncado | Bootloader passa um tamanho de initrd menor que o ramdisk (T210: `initrd=...,1m`) | `/proc/cmdline` do stock; override do tamanho do initrd no kernel ou ramdisk menor |
| Volta ao bootloader/download mode sem log | Imagem maior que a partição, endereço de carga errado, página errada, compressão não suportada | `bootimg.py info` do original × novo; tamanho da partição |
| Panic num `probe` de driver | Driver de outro aparelho, `pdata` com callback NULL, chip diferente (T210: touch bt532 chamando `tsp_power` NULL) | last_kmsg: o driver aparece no backtrace. Trazer driver e dados de placa do fabricante |
| BUG/panic em timer, workqueue ou lista, longe de qualquer driver | Algo foi liberado com timer ou work pendente, quase sempre um probe que falhou (T210: sec_battery com IRQ errada) | Kernel com `DEBUG_OBJECTS_TIMERS`/`DEBUG_OBJECTS_WORK`, que aponta o dono. Corrigir a causa da falha e cancelar o work no caminho de erro |
| IRQ de GPIO errada, "irq N: nobody cared" ou probe com -EINVAL | Base de IRQ dos GPIOs diferente entre a placa e o driver de GPIO (T210: 128 × 160) | Macro `*_GPIO_TO_IRQ`, `irq_base` do gpio; fixar a base |
| Boota mas /data não monta, adb "unauthorized", pede senha | fstab com partições do irmão; EFS em outro número | fstab e init*.rc com `mmcblk` do seu aparelho |
| Bootloop no logo animado | system não monta, SELinux bloqueia serviço essencial, HAL crítico crashando | `adb logcat` (imagem de depuração), `dmesg \| grep avc`, tombstones |

## Tela e toque

| Sintoma | Causa provável | Correção |
|---|---|---|
| Tela preta, mas o sistema roda (adb ok) | Clock do display errado ou desligado por outro driver que compartilha o clock (T210: câmera desligando o clock "LCDCLK" inexistente) | Usar o nome de clock que o kernel conhece e que segura AXI/AHB/DSI; ler registradores do display e comparar com o recovery stock |
| Imagem some uns 30 s depois do boot | `regulator_init_complete` desligou reguladores sem consumidor (ponte/painel) | Driver pega os reguladores também quando o bootloader já ligou a tela |
| Tela quebra ao iniciar o driver | Driver reprograma o que o bootloader configurou (T210: pós-divisor do clock do LCD quebrava o DSI) | Seguir exatamente o caminho do kernel do fabricante para essa placa |
| UI travando ou rasgando | Framebuffer com poucos buffers (gralloc do N quer 3) | Aumentar a memória do fb para 3 buffers |
| Brilho fraco ou sem controle | Tabela de brilho de outro painel | Copiar a tabela do fabricante |
| Toque não responde ou fica invertido | Driver ou firmware de touch errado, eixos e resolução | Driver e firmware do modelo; `idc`, `swap_xy`/`invert` |

## Rede, áudio, mídia

| Sintoma | Causa provável | Correção |
|---|---|---|
| App não toca vídeo, proxy ou servidor local falha com "Cannot assign requested address" | Loopback `lo` DOWN: init.rc sem `ifup lo` (T210, AZtube) | `on boot` com `ifup lo`, `hostname localhost`, `domainname localdomain` |
| Wi-Fi não liga | Firmware ausente ou com nome errado, módulo com vermagic antigo, script de setup com parâmetros do chip do irmão | `dmesg` do módulo; firmware do stock; `insmod` com os parâmetros do stock |
| Bluetooth derruba o serviço | HAL espera recurso que o chip não tem (T210: SD8787 sem BLE, asserts abortando) | Corrigir o HAL (NOP nos asserts) e carregar a calibração (`cal_cfg`) como o stock |
| Sem som no alto-falante | Rotas do irmão ligam o amplificador de outro PMIC/codec | Rotas com os registradores do seu codec/amplificador (do stock ou da fonte) |
| Microfone do fone mudo | Entrada do codec errada (T210: o mic do fone chega por AMIC1, e não pela entrada "externa") | Ler/escrever registradores do codec por debugfs gravando ao mesmo tempo; testar cada entrada |
| Câmera "capture error -22" | Driver recusa um parâmetro que o HAL pede (T210: fps 24) | Aceitar o valor no driver ou corrigir o HAL |
| Só uma câmera aparece | HAL só abre `/dev/video0`, ou falta regra do `video1` no ueventd | HAL com duas câmeras; regra no ueventd |
| App gravador fecha na 1ª gravação | Pasta esperada não existe | `mkdir` no `boot_completed` |
| MTP Documents crasha | Falta appfuse (kernel antigo) | Remover MtpDocumentsProvider (o MTP com o PC continua) |

## Sistema e segurança

| Sintoma | Causa provável | Correção |
|---|---|---|
| Serviço funciona em permissive e falha em enforcing | Arquivo editado sem rótulo SELinux | Rotular (`sysimg.sh label_like`); `labelchk.py` |
| Tecla Home ou Voltar não funciona | Kernel manda keycode diferente do `.kl` (T210: KEY_HOMEPAGE 172) | `key 172 HOME` no `gpio-keys.kl` (ou no .kl do driver) |
| Sensores mortos para os apps | Permissões de sysfs com `inputN` fixo do irmão | Regras com curinga no ueventd |
| Modelo errado na loja ou no PC | `default.prop` sobrepondo o `build.prop`; `iProduct` USB do irmão | Ajustar os dois e o init.rc |
| `adb reboot recovery` cai no Android | Bootloader ignora o pedido às vezes | Esperar ~15 s e repetir, ou combinação de teclas |
| Relógio pulando atrapalha testes | NTP ajustando no meio | Laços por contador, não por `date` |
