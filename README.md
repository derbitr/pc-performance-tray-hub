# PC Performance Tray Hub

Um otimizador de desktop ultraleve (< 20MB de RAM, 0.0% CPU em idle) com interface **Full Night Mode (True Dark)** e ícones vetoriais SVG, desenhado especificamente para o Windows 10/11.

---

## Recursos Principais

* **Modo HUD Livre / Arrastável:** Pode ser fixado em qualquer canto da tela (Modo Alfinete) com controle de opacidade (60% a 100%) ou recolhido discretamente na System Tray ao lado do relógio.
* **Perfis de Energia Nativos:** Alternância rápida entre *Turbo Max* (Desempenho Máximo nativo do processador), *Equilibrado* e *Silencioso*.
* **Telemetria Tabular em Tempo Real:** Monitora clock em GHz, uso percentual de CPU e temperatura do processador.
* **Gráfico Sparkline Vetorial (30s):** Traçado contínuo em tempo real de carga da CPU (Ciano `#38BDF8`) e temperatura (Esmeralda `#10B981`) sem bibliotecas externas pesadas.
* **Redutor de Latência do Windows (Timer 0.5ms):** Reduz o timer de eventos do kernel de 15.6ms para 0.5ms/1.0ms via `winmm.dll:timeBeginPeriod`, diminuindo o input lag do mouse e microstutters.
* **Modo Game Focus:** Detecta o jogo ativo em tela cheia e eleva sua prioridade para `HIGH_PRIORITY_CLASS`, aplicando `EcoQoS` em processos secundários de fundo.
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
│   │   └── icons.py            # Ícones vetoriais SVG (Zero emojis)
│   ├── core/
│   │   ├── autostart.py        # Registro no Agendador de Tarefas do Windows
│   │   ├── disk_cleaner.py     # Limpeza não-destrutiva de arquivos temporários
│   │   ├── game_focus.py       # Prioridade de CPU e EcoQoS para jogos
│   │   ├── hardware_monitor.py # Leitura de clock, temperatura e Super I/O
│   │   ├── health_checker.py   # Diagnóstico S.M.A.R.T. de discos
│   │   ├── memory_manager.py   # Otimizador de Working Set e Standby List
│   │   ├── network_optimizer.py# Flush DNS e latência
│   │   ├── power_manager.py    # Gerenciamento de planos de energia Win32
│   │   ├── process_suspender.py# Congelamento seguro de launchers
│   │   └── timer_resolution.py # Redução de input lag via winmm.dll
│   └── ui/
│       ├── flyout_window.py    # Interface gráfica True Dark arrastável
│       ├── hotkey_worker.py    # Captura global de atalhos do teclado
│       ├── sparkline_widget.py # Gráfico dinâmico em QPainter
│       └── tray_app.py         # Ícone dinâmico e menu de contexto da bandeja
```

---

## Compilação Standalone

Para gerar o executável nativo único (`.exe` sem console):

```powershell
python -m PyInstaller --noconsole --onefile --name "PCTrayHub" --icon="app_icon.ico" --add-data "src;src" main.py
```
O binário será gerado na pasta `dist/PCTrayHub.exe`.
