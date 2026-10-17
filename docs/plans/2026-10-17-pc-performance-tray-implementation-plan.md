# Plano de Implementação: PC Performance Tray Hub (Full Night Mode)

**Data:** 17 de Outubro de 2026  
**Status:** Pronto para Execução  
**Referência de Design:** `docs/specs/2026-10-13-pc-performance-tray-design.md`  
**Target:** Windows 10/11 x64 | Executável Ultra-Leve (< 25 MB RAM, ~0.0% CPU Idle)

---

## 1. Visão Geral da Arquitetura do Sistema

O projeto é estruturado em duas camadas desacopladas:
1. **Core Engine (Backend de Otimizações & Hardware):** Módulos Python puros que interagem diretamente com a Win32 API (`ctypes`), WMI e comandos do sistema para executar otimizações em threads separadas, sem nunca bloquear a interface.
2. **Stealth Tray UI (Frontend Full Night Mode):** Janela flutuante moderna sem bordas (Frameless Acrylic) ancorada acima do relógio da bandeja do sistema, desenhada com ícones vetoriais SVG, tipografia monoespaçada/tabular e estrita paleta escura True Night Mode (`#04060A`, `#080C14`, `#161E2E`, `#38BDF8`).

---

## 2. Fases de Implementação Passo a Passo

### Fase 1: Módulos de Baixo Nível e Otimização (Core Engine)
- [ ] **1.1 `power_manager.py`:**
  - Gerencia os esquemas de energia do Windows via `powrprof.dll` e `powercfg.exe`.
  - Suporta troca instantânea entre:
    - **Turbo Max:** Desempenho Máximo (`261561f2-df2e-4c08-be8e-41f4c8eaefb6`) com CPU a 100%.
    - **Equilibrado:** Esquema padrão (`381b4222-f694-41f0-9685-ff5bb260df2e`).
    - **Silencioso:** Modo de economia de energia e redução térmica (`a1841308-3541-4fab-bc81-f71556f20b4a`).
- [ ] **1.2 `memory_manager.py`:**
  - Limpeza profunda de memória via chamadas de kernel Win32:
    - `psapi.dll:EmptyWorkingSet` em processos abertos para recolher páginas desnecessárias.
    - Esvaziamento de Standby List via `ntdll.dll:NtSetSystemInformation` com privilégio de processo.
    - Retorna a quantidade exata de Megabytes liberados para feedback visual.
- [ ] **1.3 `process_suspender.py`:**
  - Detecção inteligente de launchers e ferramentas de segundo plano (Steam, Epic Games, Discord, Docker, EA Desktop, Overwolf).
  - Execução de suspensão via `ntdll.dll:NtSuspendProcess` e retomada via `ntdll.dll:NtResumeProcess`.
  - Zera 100% o uso de CPU desses programas sem fechá-los, preservando logins e downloads.
- [ ] **1.4 `network_optimizer.py`:**
  - Esvaziamento rápido do cache DNS (`ipconfig /flushdns` e chamadas `dnsapi.dll`).
  - Limpeza de tabelas ARP órfãs de rede de forma não-destrutiva e sem reiniciar a máquina.
- [ ] **1.5 `health_checker.py`:**
  - Leitura SMART dos discos (SSD Walram 128GB e HDD Western Digital 1TB) via WMI (`MSStorageDriver_FailurePredictStatus`).
  - Consulta rápida aos últimos eventos de desligamento não esperado (`Kernel-Power Event 41`) e cálculo de uma pontuação de integridade do sistema.
- [ ] **1.6 `hardware_monitor.py`:**
  - Monitoramento de frequência de clock da CPU (GHz), uso percentual e temperatura do processador.
  - Integração com `LibreHardwareMonitorLib` para leitura do diodo térmico da CPU e comando de velocidade de ventoinha em RPM.

---

### Fase 2: Interface Visual Full Night Mode & Ícones SVG
- [ ] **2.1 `assets/icons.py`:**
  - Dicionário de ícones vetoriais SVG minimalistas desenhados em traço linear fino (1.5px/2px), padronizados em `#38BDF8`, `#94A3B8` e `#10B981`.
  - Zero emojis.
- [ ] **2.2 `tray_flyout.py`:**
  - Criação da janela flutuante estilo Fluent Acrylic / True Dark Mode (`#04060A`, `#080C14`, `#161E2E`).
  - Janela sem bordas (`Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool`) com animação suave de fade e slide-up ao abrir.
  - Posicionamento automático inteligente no canto inferior direito, adaptado à posição e altura da barra de tarefas do Windows.
- [ ] **2.3 Componentes dos 7 Gadgets Modulares:**
  - `PowerWidget`: Segmented switch moderno com acento em Azul Safira/Azure.
  - `TelemetryWidget`: Cards de GHz e Temperatura com numerais tabulares fixos.
  - `FanControlWidget`: Slider com visual noturno e botão de trava rápida em 100%.
  - `MemoryWidget`: Medidor e botão de limpeza instantânea com animação de confirmação.
  - `LauncherWidget`: Toggle de pausar/retomar launchers com contagem de processos suspensos.
  - `HealthWidget`: Status SMART do SSD/HD e estabilidade geral.
  - `NetworkWidget`: Botão de Flush DNS com resposta em milissegundos.

---

### Fase 3: Integração com a System Tray & Atalhos Globais
- [ ] **3.1 `tray_icon.py`:**
  - Ícone dinâmico desenhado em tempo real para a bandeja ao lado do relógio do Windows.
  - Renderiza o glifo de raio e o texto com a temperatura atual da CPU (ex: `54°C`).
  - Suporte a clique esquerdo para abrir o flyout e clique direito para menu de contexto rápido.
- [ ] **3.2 `hotkey_manager.py`:**
  - Registro de atalhos globais de teclado usando `user32.dll:RegisterHotKey` em thread de baixa latência.
  - Atalho padrão: `Ctrl + Shift + F12` (Limpar RAM instantaneamente mesmo dentro de jogos).
  - Atalho padrão: `Ctrl + Shift + F11` (Ativar Turbo Max).

---

### Fase 4: Autoinstalação Silenciosa e Empacotamento Portátil (.exe)
- [ ] **4.1 `installer.py` / `register_task.py`:**
  - Script que registra o executável no Agendador de Tarefas do Windows (`schtasks`) para iniciar automaticamente no logon do usuário com privilégios elevados (`HighestAvailable`), eliminando qualquer aviso de UAC.
- [ ] **4.2 Build de Executável Único:**
  - Compilação via PyInstaller gerando um único executável portátil (`PCTrayHub.exe`) sem instaladores chatos ou dependências externas.

---

### Fase 5: Testes de Validação e Verificação em Tempo Real
- [ ] **5.1 Teste de Pegada de Memória:** Validar que o executável em segundo plano consome menos de 25 MB de RAM e 0.0% de CPU em repouso.
- [ ] **5.2 Teste de Efetividade da Limpeza:** Verificar se o botão de RAM reduz o Working Set e a Standby List no Gerenciador de Tarefas do Windows.
- [ ] **5.3 Teste de Resposta Térmica e Clock:** Validar se a alternância de perfis reflete no clock do Core i7-7700 e no plano do Windows.
- [ ] **5.4 Teste de Atalho Global em Jogo/Full-Screen:** Garantir que o `Ctrl+Shift+F12` funcione com foco em outra janela.
