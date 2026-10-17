# PC Performance Tray Hub

Otimizador de desktop ultraleve (consumo inferior a 20 MB de RAM e 0.0% de CPU em idle) com interface Full Night Mode (True Dark) e iconografia vetorial SVG nativa, desenvolvido especificamente para Windows 10 e Windows 11.

---

## Metodos de Instalacao

### Metodo 1: Instalador Automatico (Para Terceiros e Usuarios Finais)

Este metodo nao requer instalacao de Python, abertura de terminal ou comandos manuais.

1. Baixe o executavel `PCTrayHub_Setup.exe` disponibilizado na aba de Releases do repositorio ou na pasta `dist/`.
2. Execute o arquivo `PCTrayHub_Setup.exe` com um clique duplo.
3. Na janela do instalador com interface Dark:
   - Selecione ou mantenha o diretorio de instalacao padrao (`%LOCALAPPDATA%\Programs\PCPerformanceTrayHub`).
   - Mantenha marcadas as opcoes de criar atalhos na Area de Trabalho, Menu Iniciar e inicializacao automatica com o Windows (sem prompt de UAC).
   - Clique em **INSTALAR AGORA**.
4. O aplicativo sera copiado, configurado no Agendador de Tarefas do Windows e iniciado imediatamente na bandeja do sistema (proximo ao relogio).

#### Desinstalacao do Metodo 1
- O aplicativo pode ser desinstalado diretamente pelo **Painel de Controle -> Programas e Recursos** ou em **Configuracoes -> Aplicativos Instalados** do Windows, selecionando `PC Performance Tray Hub`.
- Alternativamente, execute o arquivo `uninstall.bat` localizado na pasta de instalacao.

---

### Metodo 2: Instalacao Manual a Partir do Codigo-Fonte (Para Desenvolvedores)

Para desenvolvedores que desejam inspecionar o codigo, executar diretamente via interpretador Python ou compilar suas proprias versoes.

#### Pre-requisitos
* Sistema Operacional: Windows 10 ou Windows 11 (64-bit).
* Python 3.10, 3.11 ou 3.12 instalado (com a opcao "Add Python to PATH" marcada durante a instalacao).
* Git para Windows instalado.

#### Passo a Passo

1. **Clonar o Repositorio:**
   Abra o PowerShell ou Prompt de Comando e execute:
   ```powershell
   git clone https://github.com/derbitr/pc-performance-tray-hub.git
   cd pc-performance-tray-hub
   ```

2. **Criar e Ativar o Ambiente Virtual (venv):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Instalar as Dependencias:**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Executar o Aplicativo:**
   ```powershell
   python main.py
   ```
   O aplicativo sera inicializado em segundo plano e fixado na bandeja do sistema (System Tray).

5. **Compilar os Executaveis Binarios (Opcional):**
   Para gerar o executavel standalone unico sem console:
   ```powershell
   python -m PyInstaller --noconsole --onefile --name "PCTrayHub" --icon="app_icon.ico" --add-data "src;src" main.py
   ```
   Para compilar o instalador grafico com o executavel embutido:
   ```powershell
   python -m PyInstaller --noconsole --onefile --name "PCTrayHub_Setup" --icon="app_icon.ico" --add-data "dist/PCTrayHub.exe;." --add-data "app_icon.ico;." installer.py
   ```
   Os arquivos compilados ficarao disponiveis na pasta `dist/`.

---

## Recursos e Funcionalidades

* **Graficos Vetoriais em Tempo Real (Customizaveis):**
  * Tracado continuo renderizado via `QPainter` com seletores tipo pilula.
  * Escolha de exibicao flexivel: exiba os graficos na primeira janela (Hub) ou na gaveta lateral expansivel (`Local: [ Hub ] [ Lateral ]`).
  * Grafico de CPU e Temperatura: monitoramento de processamento e termica em tempo real.
  * Grafico de Memoria RAM: percentual de uso fisico e memoria livre disponivel.
  * Grafico de Placa de Video (GPU): carga percentual de processamento e alocacao de VRAM.

* **Gaveta Lateral Expansivel:**
  * O painel se expande lateralmente com animacao fluida baseada em curvas cubicas (`OutCubic`), revelando gadgets complementares e processos com maior consumo de memoria.
  * Detecao inteligente das bordas da tela: quando acoplado no canto direito, expande-se suavemente para a esquerda em direcao ao centro da tela sem ultrapassar os limites do monitor.

* **Monitoramento e Otimizacao de Jogos (Anti-Cheat Seguro):**
  * Deteccao automatica do processo de jogo em tela cheia via Win32 API.
  * Elevacao automatica de prioridade para `HIGH_PRIORITY_CLASS` sem injecao de DLLs (totalmente compativel e seguro contra bloqueios de Riot Vanguard, EAC, BattlEye e VAC).
  * Leitura de taxa de quadros (FPS) via memoria compartilhada nativa do RivaTuner Statistics Server (RTSS), caso esteja presente no sistema.

* **Controle de Energia e Latencia de Sistema:**
  * Perfis de energia: Turbo Max (Desempenho Maximo), Equilibrado e Silencioso (Economia de Energia).
  * Redutor de latencia de timer: altera a granularidade do temporizador do kernel de 15.6ms para 0.5ms via `winmm.dll:timeBeginPeriod`, reduzindo o input lag em jogos competitivos.

* **Limpeza de Memoria RAM e Armazenamento:**
  * Esvaziamento de Working Set e purga de Standby List da memoria sem fechar programas ou causar perda de dados.
  * Limpeza rapida de arquivos temporarios de `%TEMP%` preservando sessoes ativas e arquivos criados nos ultimos 20 minutos.
  * Otimizacao de rede com descarga instantanea do cache de resolucao DNS (`ipconfig /flushdns` e `dnsapi.dll`).

* **Congelamento Seguro de Aplicativos em Segundo Plano:**
  * Pausa launchers pesados (Steam, Epic Games, Discord, EA App, Spotify, Docker) atraves de `NtSuspendProcess` durante sessoes de jogo, liberando CPU e RAM sem fechar as sessoes ativas.

* **Diagnostico de Sistema em 1 Clique:**
  * Botao no rodape que gera e copia instantaneamente para a area de transferencia um relatorio completo das especificacoes do sistema (modelo de processador, frequencia, uso de threads, placa de video, memoria VRAM, integridade S.M.A.R.T. de discos e latencia de timer).

* **Atalho Global:**
  * `Ctrl + Shift + F12`: Executa a limpeza imediata de memoria RAM em segundo plano a partir de qualquer aplicativo ou jogo.
  * `Ctrl + Shift + F11`: Alterna instantaneamente o perfil de energia para o modo Turbo Max.

---

## Estrutura do Codigo-Fonte

```
pc-performance-tray-hub/
├── main.py                     # Ponto de entrada com mutex de instancia unica de sessao
├── installer.py                # Instalador grafico standalone para distribuicao
├── app_icon.ico                # Icone do aplicativo
├── requirements.txt            # Dependencias do projeto (PyQt6, psutil, pyinstaller)
├── src/
│   ├── assets/
│   │   └── icons.py            # Icones vetoriais SVG desenhados sob medida
│   ├── core/
│   │   ├── autostart.py        # Registro no Agendador de Tarefas do Windows
│   │   ├── disk_cleaner.py     # Limpeza segura de arquivos temporarios
│   │   ├── fps_sync.py         # Sincronizacao de jogos e telemetria RTSS
│   │   ├── game_focus.py       # Gerenciamento de prioridade de processos em foco
│   │   ├── gpu_monitor.py      # Deteccao de placas de video e VRAM no Registro
│   │   ├── hardware_monitor.py # Metricas de CPU, frequencia e temperatura
│   │   ├── health_checker.py   # Deteccao de integridade S.M.A.R.T. de discos
│   │   ├── memory_manager.py   # Otimizador de Working Set e Standby List
│   │   ├── network_optimizer.py# Limpeza de cache DNS e medicoes de latencia
│   │   ├── power_manager.py    # Gerenciamento de esquemas de energia Win32
│   │   ├── process_suspender.py# Suspensao e retomada de launchers
│   │   └── timer_resolution.py # Reducao de input lag via temporizadores de alta precisao
│   └── ui/
│       ├── flyout_window.py    # Interface principal True Dark com expansao lateral
│       ├── hotkey_worker.py    # Captura global de combinacoes de teclas do teclado
│       ├── sparkline_widget.py # Renderizacao continua de graficos em tempo real
│       └── tray_app.py         # Icone dinamico e menu de contexto na System Tray
```
