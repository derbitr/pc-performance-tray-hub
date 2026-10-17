# PC Performance Tray Hub

Um otimizador de desktop ultraleve (< 20MB de RAM, 0.0% CPU em idle) com interface **Full Night Mode (True Dark)** e ícones vetoriais SVG, desenhado especificamente para o Windows 10/11.

---

## Recursos Principais

* **Gráficos Visuais Customizáveis (Na 1ª Janela ou na Lateral):** Traçado contínuo vetorial em tempo real via `QPainter` com seletores tipo pílula para ativar ou ocultar cada gráfico individualmente:
  * **Exibição Flexível:** Os gráficos podem aparecer diretamente na **Primeira Janela (Hub)** ou ser movidos para a **Gaveta Lateral** com um único clique (`Local: [ Hub ] [ Lateral ]`).
  * **CPU & Temperatura:** Carga de processamento (Ciano `#38BDF8`) e temperatura em graus Celsius (Esmeralda `#10B981`).
  * **Memória RAM:** Uso da memória física em porcentagem (Roxo `#A855F7`) e memória livre em gigabytes (Ciano `#38BDF8`).
  * **Placa de Vídeo & VRAM:** Carga de computação gráfica (Âmbar `#F59E0B`) e uso de memória de vídeo (Rosa `#F43F5E`).
* **Gaveta Lateral Expansível Estilo Jogos IDLE:** Em vez de abrir janelas modais sobrepostas, o hub se expande horizontalmente para a lateral exibindo a telemetria estendida de hardware e jogos. Possui detecção adaptativa das bordas da tela: quando acoplado no canto direito perto do relógio, expande-se suavemente para a esquerda em direção ao centro da tela.
* **Detecção Automática de Placa de Vídeo (GPU):** Identifica adaptadores dedicados (NVIDIA, AMD) e gráficos integrados (Intel HD Graphics) via Registro do Windows com custo zero de CPU, monitorando carga percentual, temperatura e alocação de memória de vídeo (VRAM).
* **Sincronização de Jogos e FPS (Anti-Cheat Seguro):**
  * Detecta dinamicamente o jogo em tela cheia via Win32 API.
  * Eleva a prioridade do jogo para `HIGH_PRIORITY_CLASS` e aplica `EcoQoS` em processos secundários.
  * **Arquitetura Anti-Cheat Safe:** Não realiza injeção intrusiva de DLLs nos jogos para evitar risco de banimentos em jogos competitivos (Valorant Vanguard, Easy Anti-Cheat, BattlEye, VAC).
  * Suporta leitura de FPS instantânea via Memória Compartilhada do RTSS (RivaTuner Statistics Server) com 0% de sobrecarga quando instalado.
* **Modo HUD Livre / Arrastável:** Pode ser fixado em qualquer canto da tela (Modo Alfinete) com controle de opacidade (60% a 100%) ou recolhido discretamente na System Tray ao lado do relógio.
* **Perfis de Energia Nativos:** Alternância rápida entre *Turbo Max* (Desempenho Máximo nativo do processador), *Equilibrado* e *Silencioso*.
* **Redutor de Latência do Windows (Timer 0.5ms):** Reduz o timer de eventos do kernel de 15.6ms para 0.5ms via `winmm.dll:timeBeginPeriod`, diminuindo o input lag do mouse e microstutters.
* **Limpeza Inteligente de RAM e SSD:**
  * Purga o *Working Set* e a *Standby List* da memória sem fechar nenhum app.
  * Remove resíduos temporários de `%TEMP%` preservando sessões e senhas do navegador.
* **Pausar / Retomar Launchers:** Congela processos pesados (Steam, Epic, Discord) via `NtSuspendProcess` sem perder o estado das aplicações.
* **Atalho Global:** <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>F12</kbd> (Limpa a memória RAM instantaneamente em segundo plano).

---

## Estrutura do Projeto

```
pc-performance-tray-hub/
├── main.py                     # Entry point com mutex de instância única
├── app_icon.ico                # Ícone do aplicativo
├── src/
│   ├── assets/
│   │   └── icons.py            # Ícones vetoriais SVG 
│   ├── core/
│   │   ├── autostart.py        # Registro no Agendador de Tarefas do Windows
│   │   ├── disk_cleaner.py     # Limpeza não-destrutiva de arquivos temporários
│   │   ├── fps_sync.py         # Sincronização segura de jogos e leitura RTSS
│   │   ├── game_focus.py       # Prioridade de CPU e EcoQoS para jogos
│   │   ├── gpu_monitor.py      # Detecção e telemetria de GPUs dedicadas/integradas
│   │   ├── hardware_monitor.py # Leitura de clock, temperatura e Super I/O
│   │   ├── health_checker.py   # Diagnóstico S.M.A.R.T. de discos
│   │   ├── memory_manager.py   # Otimizador de Working Set e Standby List
│   │   ├── network_optimizer.py# Flush DNS e latência
│   │   ├── power_manager.py    # Gerenciamento de planos de energia Win32
│   │   ├── process_suspender.py# Congelamento seguro de launchers
│   │   └── timer_resolution.py # Redução de input lag via winmm.dll
│   └── ui/
│       ├── flyout_window.py    # Interface True Dark com expansão lateral IDLE
│       ├── hotkey_worker.py    # Captura global de atalhos do teclado
│       ├── sparkline_widget.py # Múltiplos gráficos dinâmicos em QPainter
│       └── tray_app.py         # Ícone dinâmico e menu de contexto da bandeja
```

---

## Compilação Standalone

Para gerar o executável nativo único (`.exe` sem console):

```powershell
python -m PyInstaller --noconsole --onefile --name "PCTrayHub" --icon="app_icon.ico" --add-data "src;src" main.py
```
O binário será gerado na pasta `dist/PCTrayHub.exe`.
